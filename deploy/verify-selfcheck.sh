#!/usr/bin/env bash
# 驗證自檢機制本身有效：故意製造故障，確認自檢會轉紅。
set -u
NET=$(docker inspect forgebase-web-1 -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')
echo "network: $NET"

probe() {
  docker exec forgebase-api-1 python3 -c "
import urllib.request, json, sys
try:
    r = urllib.request.urlopen('http://$1:3000/api/health/assets', timeout=20)
    code, body = r.status, r.read().decode()
except urllib.error.HTTPError as e:
    code, body = e.code, e.read().decode()
d = json.loads(body)
print(' HTTP', code, '| status =', d['status'])
print(' assetsMounted =', d['assetsMounted'], '| publishedCategories =', d['publishedCategories'])
for p in d['problems']:
    print('  problem:', p)
"
}

echo
echo "=== 對照組：正常運作的 web 容器 ==="
probe forgebase-web-1

echo
echo "=== 故障組 A：沒有掛 demo 素材目錄 ==="
docker run -d --rm --name web-nomount --network "$NET" \
  -e API_INTERNAL_URL=http://api:8000 \
  -e NEXT_PUBLIC_API_URL=http://172.233.64.5 \
  -e REVALIDATE_SECRET=dummy \
  forgebase-web >/dev/null
sleep 12
probe web-nomount
docker stop web-nomount >/dev/null

echo
echo "=== 故障組 B：租戶設定與內容不符（模擬 NEXT_PUBLIC_TENANT_SLUG=default-tenant）==="
docker run -d --rm --name web-badtenant --network "$NET" \
  -v /opt/forgebase/demo:/demo:ro \
  -e API_INTERNAL_URL=http://api:8000 \
  -e NEXT_PUBLIC_API_URL=http://172.233.64.5 \
  -e NEXT_PUBLIC_TENANT_ID=default-tenant \
  -e REVALIDATE_SECRET=dummy \
  forgebase-web >/dev/null
sleep 12
probe web-badtenant
docker stop web-badtenant >/dev/null
