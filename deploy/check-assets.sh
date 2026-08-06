#!/usr/bin/env bash
#
# 前台素材健檢：列出每個頁面引用的 demo 素材，並區分「實體檔案」與「即時產生的佔位圖」。
# 佔位圖代表該素材在容器裡找不到實體檔（多半是 demo/ 目錄沒掛進 web 容器）。
#
# 用法：bash deploy/check-assets.sh [base_url]     預設 http://localhost
set -u
BASE="${1:-http://localhost}"
PAGES="${PAGES:-/en /zh-TW /en/products /en/applications /en/certifications /en/about /zh-TW/products}"

FAIL=0
for PAGE in $PAGES; do
  TOTAL=0; PLACEHOLDER=0; MISSING=0
  for URL in $(curl -s "$BASE$PAGE" | grep -oE '(src="|url\()/demo[^")]*' | sed 's/^src="//; s/^url(//' | sort -u); do
    TOTAL=$((TOTAL + 1))
    HEAD=$(curl -sI "$BASE$URL")
    KIND=$(echo "$HEAD" | grep -i '^x-demo-asset:' | tr -d '\r' | awk '{print $2}')
    CODE=$(echo "$HEAD" | head -1 | awk '{print $2}')
    case "$KIND" in
      placeholder) PLACEHOLDER=$((PLACEHOLDER + 1)) ;;
      file) ;;
      *) MISSING=$((MISSING + 1)); echo "    ! $URL -> HTTP $CODE" ;;
    esac
  done
  printf '  %-38s 素材 %2d ｜ 實體 %2d ｜ 佔位 %2d ｜ 異常 %d\n' \
    "$PAGE" "$TOTAL" "$((TOTAL - PLACEHOLDER - MISSING))" "$PLACEHOLDER" "$MISSING"
  [ "$MISSING" -gt 0 ] && FAIL=1
done

echo
if [ "$FAIL" -eq 0 ]; then
  echo "OK：沒有異常素材。"
  echo "（cert-*-badge 一類本來就沒有實體檔，會顯示為佔位圖，屬正常設計）"
else
  echo "有素材回應異常，請檢查 web 容器是否掛載了 demo/ 目錄。"
fi
exit "$FAIL"
