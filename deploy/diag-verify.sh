#!/usr/bin/env bash
set -u
BASE=http://localhost

for PAGE in /en /en/products /en/products/torque-and-socket-tools /en/applications; do
  echo "=== $PAGE ==="
  HTML=$(curl -s "$BASE$PAGE")
  echo -n "  空狀態訊息數: "; echo "$HTML" | grep -c 'No published' || true
  echo -n "  分類名稱出現: "; echo "$HTML" | grep -c 'Torque and Socket Tools' || true
  echo "  圖片 URL:"
  echo "$HTML" | grep -oE '(src="|url\()/demo[^")]*' | sed 's/^src="//; s/^url(//' | sort -u | head -8 | sed 's/^/    /'
done

echo
echo "=== 每個圖片 URL 的真實回應 ==="
curl -s "$BASE/en/products" | grep -oE '(src="|url\()/demo[^")]*' | sed 's/^src="//; s/^url(//' | sort -u | while read -r U; do
  printf '  %-90s ' "$U"
  curl -s -o /dev/null -w '%{http_code} %{content_type} %{size_download}B\n' "$BASE$U"
done
