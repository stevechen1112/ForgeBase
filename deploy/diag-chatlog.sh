#!/usr/bin/env bash
set -u
echo "=== api 容器最近 20 分鐘的 chat 請求與錯誤 ==="
docker logs forgebase-api-1 --since 25m 2>&1 | grep -iE 'chat|error|exception|timeout' | tail -n 40

echo
echo "=== chat reply generation 相關錯誤 ==="
docker logs forgebase-api-1 --since 25m 2>&1 | grep -iE 'generation failed|openai|rate' | tail -n 20

echo
echo "=== DB 中最近的 chat session 與訊息計數 ==="
docker exec forgebase-db-1 psql -U forgebase -d forgebase -c "SELECT id, context_entity_type, status, message_count, started_at, updated_at FROM chat_sessions ORDER BY started_at DESC LIMIT 6;"
docker exec forgebase-db-1 psql -U forgebase -d forgebase -c "SELECT role, left(content, 90) AS content, created_at FROM chat_messages ORDER BY created_at DESC LIMIT 8;"
