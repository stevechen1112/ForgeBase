# ForgeBase — Linode 生產部署指南

單台 Linode、Docker Compose 一條龍部署三個應用：

| 服務 | 說明 | 對外路徑 |
|---|---|---|
| `caddy` | 反向代理＋自動 Let's Encrypt HTTPS | 80 / 443 |
| `marketing` | ForgeBase 產品官網 | `https://pcbrm.tw/` |
| `web` | NorthForge 參考站 | `https://pcbrm.tw/northforge-tools/` |
| `templates` | 產業範本展示站 | `https://pcbrm.tw/templates/` |
| `admin` | Next.js 後台（basePath=/backend） | `https://pcbrm.tw/backend` |
| `api` | FastAPI（單 worker，避免內建排程重複執行） | `https://pcbrm.tw/api/v1`、`/uploads`、`/health` |
| `db` | PostgreSQL 16（僅容器內網，不對外開 port） | — |
| `migrate` | 一次性 alembic upgrade head（api 啟動前自動跑） | — |

> 正式網域為 `https://pcbrm.tw`；`deploy/Caddyfile` 由 Caddy 自動申請及更新憑證。公開 HTTP 會永久導向 HTTPS，僅保留主機內部的 HTTP 健康檢查入口。

---

## 0. 前置作業

1. **Linode 開機**：Ubuntu 24.04 LTS，建議 **Shared CPU 4 GB（或以上）**——Next.js build 很吃記憶體，2 GB 可能在 `next build` 時 OOM。
2. **防火牆**：對外開 22 / 80 / 443；80 用於 ACME 驗證與健康檢查，443 提供正式 HTTPS。

## 1. 安裝 Docker

```bash
ssh root@<linode-ip>
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
# compose plugin 已內含：docker compose version
```

## 2. 取得程式碼

```bash
git clone https://github.com/stevechen1112/ForgeBase.git
cd ForgeBase
```

## 3. 設定環境變數（兩個檔案）

```bash
cp deploy/compose.env.example .env
cp deploy/api.env.example deploy/api.env
```

### 3.1 根目錄 `.env`

```bash
nano .env
```

| 變數 | 填法 |
|---|---|
| `PROTOCOL` | `https` |
| `DOMAIN` | `pcbrm.tw` |
| `APEX_DOMAIN` | `pcbrm.tw` |
| `POSTGRES_PASSWORD` | 強密碼 |
| `REVALIDATE_SECRET` | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `NEXT_PUBLIC_TENANT_SLUG` | **預設留空**，見下方說明 |
| `NEXT_PUBLIC_SITE_NAME` | 依站台調整 |

> **`NEXT_PUBLIC_TENANT_SLUG` 必須與內容的歸屬一致。** 有值時前台每次呼叫 API 都會帶 `X-Tenant-ID`，
> API 只回該租戶的資料；seed 與匯入腳本建立的內容 `tenant_id` 是 NULL，此時必須留空，
> 否則前台會查到 0 筆內容 —— 表現出來就是頁面沒有商品、圖片全變成佔位圖。

### 3.2 `deploy/api.env`

| 變數 | 填法 |
|---|---|
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `OPENAI_API_KEY` | OpenAI API key |
| `PUBLIC_TENANT_SLUG` | 公開網站使用的租戶 slug（啟用 AI 客服時必填，例如 `default-tenant`） |
| `ENCRYPTION_MASTER_KEY` | 同上方式產生（production 必填，沒設 API 會拒絕啟動） |
| `WEB_REVALIDATE_SECRET` | **必須與 .env 的 `REVALIDATE_SECRET` 完全相同** |

> `DATABASE_URL`、`FRONTEND_URL`、`ALLOWED_ORIGINS` 等由 compose 依 `DOMAIN`、`POSTGRES_*` 自動組裝，不用手填。

## 4. 建置與啟動

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

- 首次啟動順序：db 健康檢查 → migrate（alembic upgrade head）→ api → admin/web → caddy。
- Caddy 首次向 Let's Encrypt 申請憑證約 10–30 秒，可用 `docker compose -f docker-compose.prod.yml logs -f caddy` 觀察。

## 5. 建立管理員帳號

```bash
docker compose -f docker-compose.prod.yml run --rm --no-deps \
  -e PYTHONPATH=/app \
  -e ADMIN_EMAIL='admin@example.com' \
  -e ADMIN_PASSWORD='<至少 16 字元的隨機密碼>' \
  -e ADMIN_IS_SUPERUSER=true \
  api python scripts/seed_admin_bcrypt.py
```

管理員帳號、密碼與是否為平台超級管理員都必須透過環境變數明確提供；腳本不含預設密碼，也不會把密碼寫入 Git。
公開註冊預設關閉（`REGISTRATION_KEY` 留空）。

## 6.（選填）匯入 demo 內容

`demo/handtool-company/seed/import_demo_content.py` 預設連到本機 API，但不再內含管理員密碼。執行前必須透過環境變數提供密碼；若要連到其他環境，再一併覆寫 API URL 與帳號：

```bash
FORGEBASE_API_BASE='http://localhost:8000/api/v1' \
FORGEBASE_DEMO_IMPORT_EMAIL='admin@forgebase.com' \
FORGEBASE_DEMO_IMPORT_PASSWORD='<至少 16 字元的密碼>' \
python demo/handtool-company/seed/import_demo_content.py
```

## 7. 驗證清單

- [ ] `https://pcbrm.tw/health/ready` → `{"status":"ready"}` 且憑證可信任
- [ ] `https://pcbrm.tw/` ForgeBase 產品官網正常
- [ ] `https://pcbrm.tw/northforge-tools/` NorthForge 參考站正常
- [ ] `https://pcbrm.tw/templates/` 範本入口正常
- [ ] `https://pcbrm.tw/backend/login` 後台登入頁正常，能登入
- [ ] 後台商品／分類列表有資料（或為空但無錯誤）
- [ ] 發布一篇內容 → 60 秒內前台更新（revalidate 生效）
- [ ] AI 起草可用（OpenAI key 生效）
- [ ] `bash deploy/check-assets.sh` 無異常素材

### 圖片顯示異常時

前台的 demo 素材由 web 容器直接讀 `demo/<company>/assets/` 下的實體檔；compose 已把 `./demo` 唯讀掛進容器。
若素材找不到，程式會即時產生一張佔位 SVG（回應帶 `X-Demo-Asset: placeholder` 且 `Cache-Control: no-store`），
所以素材補齊後重新整理就會恢復，不會被瀏覽器快取鎖住。

**先看自檢端點，它會直接說出原因：**

```bash
curl -s http://<你的網域>/api/health/assets | python3 -m json.tool
```

| 欄位 | 意義 |
|---|---|
| `assetsMounted: false` | `demo/` 沒掛進 web 容器，所有圖會退化成佔位圖 |
| `publishedCategories: 0` | 前台查不到內容，多半是 `NEXT_PUBLIC_TENANT_SLUG` 與內容歸屬不符（見 3.1） |
| `missingAssets` | 執行期間實際找不到實體檔的素材（同時會寫進 web 的 log） |
| `productsWithoutImage` | 已發布但沒有對應圖片的產品型號 |

web 容器的 healthcheck 就是打這個端點，所以上述前兩種故障會讓 `docker compose ps` 顯示 `unhealthy`，
不需要等人看到破圖才發現。逐頁盤點素材用：

```bash
bash deploy/check-assets.sh                      # 伺服器本機
bash deploy/check-assets.sh http://<你的網域>    # 從外部檢查
```

改動素材或租戶相關設定後，可用 `bash deploy/verify-selfcheck.sh` 重新確認自檢本身仍能攔截故障
（它會另外起兩個刻意壞掉的容器，驗證端點確實回 503，跑完自動清掉）。

**新增產品沒有圖是預期行為，需要補內容。** 產品圖目前的來源順序是 CMS 的 `image_url` →
`web/src/lib/siteConfig.ts` 的 `assetManifest.productByKey`（以型號對照）。新型號兩邊都沒有時就會沒有圖，
自檢會把型號列在 `productsWithoutImage` 提醒你，但不會讓容器變 unhealthy。

## 8. 日常維運

```bash
# 更新程式碼並重建
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 看 log
docker compose -f docker-compose.prod.yml logs -f api

# 手動跑 migration（正常部署會自動跑，這裡是除錯用）
docker compose -f docker-compose.prod.yml run --rm migrate

# 備份資料庫
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U forgebase forgebase | gzip > backup-$(date +%F).sql.gz
```

### 建議的安全部署流程

正式更新改用下列腳本。它會先備份 PostgreSQL 與目前映像，再自動找出 `api`、`admin`、`web`、所有 `web_*` 租戶前台、`marketing` 與 `templates`，建置、執行 migration、啟動並逐一確認容器狀態，最後檢查 `/health/ready`：

```bash
bash deploy/safe-deploy.sh
```

推送到 `main` 後的 GitHub Actions production workflow 也必須呼叫同一支腳本；同步程式碼時會排除主機上的 `backups/`，避免 `rsync --delete` 刪除資料庫備份與映像 rollback manifest。

若健康檢查未通過，腳本會保留 rollback manifest。先查看 API 與 migration logs，並先做不變更 image／container 的完整 preflight：

```bash
bash deploy/rollback.sh --dry-run \
  --approve-api-schema-compatibility \
  /absolute/path/to/backups/images-TIMESTAMP.manifest

# 確認舊 API 可讀取目前 schema 後，才實際切換
bash deploy/rollback.sh \
  --approve-api-schema-compatibility \
  /absolute/path/to/backups/images-TIMESTAMP.manifest
```

rollback 會先驗證 manifest 服務、重複項、所有舊 image 是否存在，以及 target image 是否與 Compose 完全一致；任一項失敗時不會改 tag 或 container。只要 manifest 含 API，就必須明確提供 `--approve-api-schema-compatibility`，避免舊程式直接碰觸不相容的新 schema。

rollback 不會自動倒回資料庫，避免未經確認覆寫正式資料。每次 `backup.sh` 會以 restricted permission 產生壓縮 SQL、Compose snapshot 與 manifest；manifest 記錄 SHA-256、Alembic head、public table 數及核心資料表 row counts。可先在 disposable database 驗證本機 recovery point：

```bash
bash deploy/restore-drill.sh --local \
  /absolute/path/to/backups/database-TIMESTAMP.sql.gz
```

若已設定加密 off-site backup，則使用 object key；下載會同時驗證 AES-GCM 與 object metadata 內的 plaintext SHA-256：

```bash
bash deploy/restore-drill.sh --offsite \
  forgebase/database-TIMESTAMP.sql.gz.enc
```

Off-site upload／download utility 維持 API image 的非 root UID 10001：上傳只暫時授權並唯讀掛載單一 database backup，完成或中斷後還原原始 owner／mode；加密／下載中間檔只使用專屬 owner-only scratch mount 並保證清除；restore 只另掛載預建的單一下載目的檔。若未同步修改 API image UID，請勿覆寫 `FORGEBASE_API_RUNTIME_UID`／`FORGEBASE_API_RUNTIME_GID`。

Restore drill 會比對 checksum、Alembic head、table 數及核心 row counts，輸出 `restore-drills/*.json` 的 RTO／backup age evidence，並在結束時刪除唯一 `forgebase_restore_drill_*` 暫存資料庫。只有確認 migration 不向前相容時，才另行人工審核正式資料庫回復；drill 永遠不會覆寫 production database。

PR／release 使用 `bash deploy/restore-rollback-lab.sh` 在獨立 Compose project 自動演練 point-in-time backup／restore、API schema approval gate、non-mutating dry-run 與兩版 application image rollback，不使用 production 設定或資源。

背景工作可透過 `/api/v1/ops/operational-jobs/summary` 檢查，失敗工作可由租戶管理員或平台超級管理員使用 `/api/v1/ops/operational-jobs/{id}/retry` 重送。若設定 `OPS_ALERT_WEBHOOK_URL`，每五分鐘監控會在 failed/stale 工作超標時送出告警。

## 9. 注意事項

- **rate limit 是 in-memory**：`--workers 2` 時限制額度是 per-worker 計算，量級小的站沒差；要精確限流需再導入 Redis backend（程式碼已留註解）。
- **上傳素材**存於 `uploads_data` volume（`/uploads` 由 api 容器提供）；要長期營運建議改接 Cloudflare R2（`deploy/api.env` 的 `R2_*`）。
- **Let's Encrypt 有速率限制**：DOMAIN 沒指好前不要反覆 `up`，避免短時間大量申請失敗被暫鎖。
- **secrets 不要 commit**：`.env` 與 `deploy/api.env` 都在 `.gitignore` 範圍內，請確認沒被追蹤。

### 生產資料供應商金鑰

PDL 與 Hunter 金鑰由 GitHub Actions 的 `Sync Production Data Providers` 手動流程安裝。流程只接受
`PDL_API_KEY`、`HUNTER_API_KEY` 兩個白名單 Secret，透過 mode `0600` 的短效檔案傳送，並以同目錄
atomic replace 更新 `/opt/forgebase/deploy/api.env`；紀錄只輸出鍵名，不輸出值。完成後會重建 API
容器，並在容器內確認 `pdl_ip`、`hunter_domain`、`hunter` 三個 Provider 已註冊。此流程只讓
Provider 可供選擇，不會修改租戶政策，也不會開啟外聯寄送。
