#!/usr/bin/env bash
set -u
echo "=== api.env 的 AI 設定（遮蔽金鑰）==="
grep -E '^(OPENAI_API_KEY|AI_MODEL_NAME)' /opt/forgebase/deploy/api.env | sed -E 's/(=sk-.{6}).*/\1***/'

echo
echo "=== 容器內生效值 ==="
docker exec forgebase-api-1 python3 -c 'from app.core.config import settings; print("AI_MODEL_NAME =", settings.AI_MODEL_NAME); print("OPENAI_API_KEY set =", bool(settings.OPENAI_API_KEY))'

echo
echo "=== 中文提問測試 ==="
VISITOR=$(cat /proc/sys/kernel/random/uuid)
S=$(curl -s -X POST http://localhost/api/v1/chat/sessions -H 'Content-Type: application/json' -d "{\"visitor_id\":\"$VISITOR\",\"context_page\":\"/zh-TW\",\"context_entity_type\":\"home\",\"locale\":\"zh-TW\"}")
SID=$(echo "$S" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["chat_session_id"])')
curl -s -X POST http://localhost/api/v1/chat/sessions/$SID/messages -H 'Content-Type: application/json' -d "{\"visitor_id\":\"$VISITOR\",\"content\":\"你們的扭力扳手有沒有通過絕緣認證？最低訂購量是多少？\",\"locale\":\"zh-TW\"}" | python3 -c 'import sys,json; d=json.load(sys.stdin)["data"]; print("reply:", d["reply"][:300])'
