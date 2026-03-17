# ForgeBase 部署與維運注意事項

更新日期：2026-03-16

本文件整理 ForgeBase 目前正式可用的部署方式，以及這次已確認的高風險維運陷阱。重點不是重講一般部署步驟，而是避免再次踩到 Next.js standalone 與靜態資產路徑的坑。

## 1. 目前正式部署結構

- API：`forgebase-api`
  - 工作目錄：`/opt/forgebase/app/api`
  - 啟動方式：systemd + uvicorn
- 前台：`forgebase-web`
  - 工作目錄：`/opt/forgebase/app/web/.next/standalone`
  - 啟動方式：systemd + `node server.js`
- 後台：`forgebase-admin`
  - 工作目錄：`/opt/forgebase/app/admin/.next/standalone`
  - 啟動方式：systemd + `node server.js`

關鍵前提：前後台正式執行時都不是從專案根目錄啟動，而是從 `.next/standalone` 啟動。

## 2. 這次已確認的圖片故障根因

症狀：

- 站上圖片一度正常，但只要重新 build 或重新部署，又會再次失效
- 檔案其實仍存在於 `web/public` 或 `admin/public`
- 但對外 URL 變成 404

根因：

- 執行中的 Next.js standalone 程序看的是 `.next/standalone`
- rebuild 後若 `.next/standalone/public` 不存在，執行中的程式就看不到真正的 `public`
- 同理，若 `.next/standalone/.next/static` 沒正確連回 `.next/static`，靜態資源也會異常

因此這不是圖片檔本身遺失，而是 standalone 執行目錄缺少正確的資產連結。

## 3. 正確修補方式

已正式採用的修補點：

- 腳本：`scripts/prepare-next-standalone.sh`
- 前台：`web/package.json` 的 `postbuild`
- 後台：`admin/package.json` 的 `postbuild`
- CI：`.github/workflows/deploy.yml`

### `prepare-next-standalone.sh` 的責任

每次 build 後自動重建以下連結：

```sh
.next/standalone/public -> <app>/public
.next/standalone/.next/static -> <app>/.next/static
```

這是目前唯一應保留的正式做法。

## 4. 明確禁止的舊做法

以下做法不要再用：

```sh
cp -r .next/static .next/standalone/.next/static
cp -r public .next/standalone/public
```

原因：

- 這種 copy 流程容易在重建後留下不一致內容
- 若目錄結構、權限或 copy 時機不對，會造成資產再度失效
- 問題看起來像偶發，但本質上是流程不穩定

結論：一律依賴 `npm run build` 之後的 `postbuild` 自動修補，不要再手動 copy。

## 5. 正式部署流程

### GitHub Actions

`.github/workflows/deploy.yml` 目前流程是：

1. 伺服器 `git pull origin main`
2. API 安裝依賴並套用 migration
3. 重啟 `forgebase-api`
4. 進入 `web` 執行 `npm ci` 與 `npm run build`
5. 進入 `admin` 執行 `npm ci` 與 `npm run build`
6. 重啟 `forgebase-web` 與 `forgebase-admin`

注意：前後台的 `npm run build` 已經會自動觸發 `postbuild`，不需要額外補 copy 指令。

### 手動部署

如需手動部署，請用下面流程：

```sh
cd /opt/forgebase/app/web
npm ci --prefer-offline
npm run build
systemctl restart forgebase-web

cd /opt/forgebase/app/admin
npm ci --prefer-offline
npm run build
systemctl restart forgebase-admin
```

## 6. 每次部署後必做檢查

前台檢查：

```sh
cd /opt/forgebase/app/web
readlink -f .next/standalone/public
readlink -f .next/standalone/.next/static
systemctl is-active forgebase-web
curl -I https://mitselect.com/demo/handtool-company/assets/generated/homepage-hero-northforge-manufacturer.png
```

後台檢查：

```sh
cd /opt/forgebase/app/admin
readlink -f .next/standalone/public
readlink -f .next/standalone/.next/static
systemctl is-active forgebase-admin
```

預期結果：

- `readlink -f .next/standalone/public` 需指向各自 app 的 `public`
- `readlink -f .next/standalone/.next/static` 需指向各自 app 的 `.next/static`
- systemd service 必須為 `active`
- 重要圖片 URL 應回 `HTTP/1.1 200 OK`

## 7. 出問題時先看哪裡

### 圖片 404，但 `public` 檔案明明存在

優先檢查：

1. `forgebase-web` 或 `forgebase-admin` 的工作目錄是否仍為 `.next/standalone`
2. `.next/standalone/public` 是否存在且是正確 symlink
3. `.next/standalone/.next/static` 是否存在且是正確 symlink
4. 最新一次 build 是否真的跑到了 `postbuild`

### rebuild 後前台可開，但部分 CSS 或 JS 異常

優先檢查：

1. `.next/standalone/.next/static` 是否缺失
2. `npm run build` 是否中斷但 service 仍被重啟
3. nginx 是否仍指向正確 upstream

### `/backend` 出現路由異常

優先檢查：

1. nginx `location /backend {` 是否沒有多餘 trailing slash
2. `proxy_pass http://127.0.0.1:3001` 是否也沒有 trailing slash

## 8. 維運紅線

- 不要手動改 `.next/standalone` 內部檔案當作永久修復
- 不要再用手動 copy `public` / `.next/static` 取代 `postbuild`
- 不要只看 `web/public` 內有檔案就判定圖片一定沒問題
- 前後台有相同 standalone 結構，修 web 的經驗要同步套用到 admin

## 9. 這次事件的結論

這次反覆失效不是內容問題，也不是圖片檔被刪掉，而是部署流程沒有把 standalone 需要的資產路徑固定下來。現在已改為：

- build 後自動重建 symlink
- CI 不再依賴手動 copy
- 前後台都使用同一套修補邏輯

後續只要維持這套流程，圖片與 standalone 靜態資產不應再因 rebuild 而重複故障。