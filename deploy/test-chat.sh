#!/usr/bin/env bash
# AI 客服端到端測試：建 session → 問問題（首頁/產品頁兩種情境）→ 檢查是否為 AI 生成
set -u
BASE=http://localhost/api/v1/chat
VISITOR=$(cat /proc/sys/kernel/random/uuid)
SESSION=$(cat /proc/sys/kernel/random/uuid)
FALLBACK_MARK="I don't have confirmed information"

echo "=== 0. 先抓一個真實產品 ID（模擬在產品頁打開客服）==="
PROD=$(curl -s "http://localhost/api/v1/content/products?status=published&locale=en&page_size=1" | python3 -c 'import sys,json; p=json.load(sys.stdin)["data"][0]; print(p["id"]); print(p["model_number"], file=sys.stderr)')
echo "product: $PROD"

echo
echo "=== 1. 建立 session（首頁情境）==="
S1=$(curl -s -X POST $BASE/sessions -H 'Content-Type: application/json' -d "{\"visitor_id\":\"$VISITOR\",\"session_id\":\"$SESSION\",\"context_page\":\"/en\",\"context_entity_type\":\"home\",\"locale\":\"en\"}")
echo "$S1" | python3 -m json.tool
SID=$(echo "$S1" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["chat_session_id"])')

echo
echo "=== 2. 提問：跨品類採購問題（需要 AI 歸納）==="
A1=$(curl -s -X POST $BASE/sessions/$SID/messages -H 'Content-Type: application/json' -d "{\"visitor_id\":\"$VISITOR\",\"content\":\"I run a hardware distribution business in Germany. Which of your product families would fit a private-label program for automotive workshops, and what certifications support that?\",\"locale\":\"en\"}")
echo "$A1" | python3 -m json.tool
echo "$A1" | grep -q "$FALLBACK_MARK" && echo ">>> 結果：AI 失敗（fallback 罐頭回覆）" || echo ">>> 結果：AI 有生成回覆"

echo
echo "=== 3. 提問：模糊需求（測試 clarifying question 機制）==="
A2=$(curl -s -X POST $BASE/sessions/$SID/messages -H 'Content-Type: application/json' -d "{\"visitor_id\":\"$VISITOR\",\"content\":\"I need some tools for my business\",\"locale\":\"en\"}")
echo "$A2" | python3 -m json.tool

echo
echo "=== 4. handoff（RFQ 預填）==="
H=$(curl -s -X POST $BASE/sessions/$SID/handoff -H 'Content-Type: application/json' -d "{\"visitor_id\":\"$VISITOR\",\"intent_reason\":\"chat_handoff_ready\",\"prefill\":{\"message\":\"private label torque wrench program\"}}")
echo "$H" | python3 -m json.tool

echo
echo "=== 5. 產品頁情境 session ==="
S2=$(curl -s -X POST $BASE/sessions -H 'Content-Type: application/json' -d "{\"visitor_id\":\"$VISITOR\",\"session_id\":\"$SESSION\",\"context_page\":\"/en/products/torque-and-socket-tools\",\"context_entity_type\":\"product\",\"context_entity_id\":\"$PROD\",\"locale\":\"en\"}")
SID2=$(echo "$S2" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["chat_session_id"])')
echo "greeting: $(echo "$S2" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["greeting"])')"
A3=$(curl -s -X POST $BASE/sessions/$SID2/messages -H 'Content-Type: application/json' -d "{\"visitor_id\":\"$VISITOR\",\"content\":\"What material and torque range does this have? Is it VDE certified?\",\"locale\":\"en\"}")
echo "$A3" | python3 -m json.tool
echo "$A3" | grep -q "$FALLBACK_MARK" && echo ">>> 結果：AI 失敗（fallback 罐頭回覆）" || echo ">>> 結果：AI 有生成回覆"
