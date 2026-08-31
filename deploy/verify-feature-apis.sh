#!/usr/bin/env bash
set -eu
test -n "${ADMIN_EMAIL:-}"
test -n "${ADMIN_PASSWORD:-}"
LOGIN=$(curl -s -X POST http://127.0.0.1/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")
TOKEN=$(echo "$LOGIN" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
TID=$(echo "$LOGIN" | python3 -c 'import sys,json; print(json.load(sys.stdin)["user"]["tenant_id"])')
AUTH="Authorization: Bearer $TOKEN"
echo "tenant_id=$TID"

echo
echo "=== 0. Reassign NULL-tenant ops data to admin tenant (so reads have something to show) ==="
docker compose -f /opt/forgebase/docker-compose.prod.yml exec -T db \
  psql -U forgebase -d forgebase -v ON_ERROR_STOP=1 -c "
UPDATE visitors SET tenant_id = '$TID'::uuid WHERE tenant_id IS NULL;
UPDATE tracking_events SET tenant_id = '$TID'::uuid WHERE tenant_id IS NULL;
UPDATE tracking_sessions SET tenant_id = '$TID'::uuid WHERE tenant_id IS NULL;
UPDATE chat_sessions SET tenant_id = '$TID'::uuid WHERE tenant_id IS NULL;
SELECT 'visitors' t, COUNT(*) FROM visitors WHERE tenant_id='$TID'::uuid
UNION ALL SELECT 'events', COUNT(*) FROM tracking_events WHERE tenant_id='$TID'::uuid
UNION ALL SELECT 'chats', COUNT(*) FROM chat_sessions WHERE tenant_id='$TID'::uuid;
"

code() { curl -s -o /tmp/out.json -w "%{http_code}" "$@"; }

echo
echo "=== READ: visitors ==="
C=$(code "http://127.0.0.1/api/v1/tracking/visitors?limit=5" -H "$AUTH"); echo "HTTP $C"
python3 - <<'PY'
import json
d=json.load(open('/tmp/out.json'))
rows=d if isinstance(d,list) else d.get('data',d)
print('count', len(rows) if isinstance(rows,list) else rows)
if isinstance(rows,list) and rows:
  print('sample', {k:rows[0].get(k) for k in ['visitor_id','total_visits','total_page_views','country'] if k in rows[0]})
PY

echo
echo "=== READ: analytics/pages ==="
C=$(code "http://127.0.0.1/api/v1/tracking/analytics/pages?days=30" -H "$AUTH"); echo "HTTP $C"
python3 - <<'PY'
import json
d=json.load(open('/tmp/out.json'))
print('summary', d.get('summary'))
print('pages', len(d.get('pages') or []))
if d.get('pages'):
  print('top', d['pages'][0])
PY

echo
echo "=== READ: chat admin sessions ==="
C=$(code "http://127.0.0.1/api/v1/chat/admin/sessions" -H "$AUTH"); echo "HTTP $C"
python3 - <<'PY'
import json
d=json.load(open('/tmp/out.json'))
items=d.get('items') or d.get('data') or []
print('items', len(items), 'total', d.get('total') or d.get('meta'))
if items:
  print('first', {k:items[0].get(k) for k in ['id','status','message_count','context_page']})
  open('/tmp/chat_id.txt','w').write(items[0]['id'])
PY

if [ -f /tmp/chat_id.txt ]; then
  CHAT_ID=$(cat /tmp/chat_id.txt)
  echo
  echo "=== READ: chat detail $CHAT_ID ==="
  C=$(code "http://127.0.0.1/api/v1/chat/admin/sessions/$CHAT_ID" -H "$AUTH"); echo "HTTP $C"
  python3 - <<'PY'
import json
d=json.load(open('/tmp/out.json'))
print('keys', list(d.keys())[:12])
msgs=d.get('messages') or []
print('messages', len(msgs))
if msgs:
  print('first_msg_role', msgs[0].get('role'), 'len', len(str(msgs[0].get('content',''))))
PY
  echo
  echo "=== WRITE: rate chat session ==="
  C=$(curl -s -o /tmp/rate.json -w "%{http_code}" -X PATCH "http://127.0.0.1/api/v1/chat/admin/sessions/$CHAT_ID" \
    -H "$AUTH" -H 'Content-Type: application/json' \
    -d '{"quality_rating":4,"admin_notes":"功能驗證評分"}')
  echo "HTTP $C"; cat /tmp/rate.json; echo
fi

echo
echo "=== WRITE: create segment ==="
C=$(curl -s -o /tmp/seg.json -w "%{http_code}" -X POST "http://127.0.0.1/api/v1/tracking/segments" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"功能驗證-台灣訪客","description":"e2e verify","combinator":"AND","conditions":[{"type":"country","op":"eq","value":"TW"}]}')
echo "HTTP $C"; cat /tmp/seg.json; echo
SEG_ID=$(python3 -c 'import json; print(json.load(open("/tmp/seg.json")).get("id",""))')
echo "SEG_ID=$SEG_ID"

if [ -n "$SEG_ID" ]; then
  echo
  echo "=== WRITE: evaluate segment ==="
  C=$(code -X POST "http://127.0.0.1/api/v1/tracking/segments/$SEG_ID/evaluate" -H "$AUTH")
  echo "HTTP $C"; cat /tmp/out.json; echo
fi

echo
echo "=== WRITE: create nurture sequence ==="
C=$(curl -s -o /tmp/nur.json -w "%{http_code}" -X POST "http://127.0.0.1/api/v1/tracking/nurture/sequences" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"功能驗證跟進","description":"e2e verify","trigger_type":"manual","is_active":false}')
echo "HTTP $C"; cat /tmp/nur.json; echo
SEQ_ID=$(python3 -c 'import json; print(json.load(open("/tmp/nur.json")).get("id",""))')
echo "SEQ_ID=$SEQ_ID"

if [ -n "$SEQ_ID" ]; then
  echo
  echo "=== WRITE: add nurture step ==="
  C=$(curl -s -o /tmp/step.json -w "%{http_code}" -X POST "http://127.0.0.1/api/v1/tracking/nurture/sequences/$SEQ_ID/steps" \
    -H "$AUTH" -H 'Content-Type: application/json' \
    -d '{"step_order":1,"delay_days":0,"subject":"Thanks for visiting","html_body":"<p>Hello from ForgeBase verify</p>"}')
  echo "HTTP $C"; cat /tmp/step.json; echo

  echo
  echo "=== WRITE: list nurture sequences ==="
  C=$(code "http://127.0.0.1/api/v1/tracking/nurture/sequences" -H "$AUTH"); echo "HTTP $C"; head -c 400 /tmp/out.json; echo
fi

echo
echo "=== WRITE: copilot message ==="
C=$(curl -s -o /tmp/cop.json -w "%{http_code}" --max-time 90 -X POST "http://127.0.0.1/api/v1/copilot/chat" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"message":"請用一句話告訴我目前有幾筆 RFQ？"}')
echo "HTTP $C"; head -c 1200 /tmp/cop.json; echo
