# ForgeBase 正式外部測試安全與觀測封板報告

日期：2026-08-16\
正式環境：`https://pcbrm.tw`\
結論：**程式與部署層封板已完成並上線；正式外部測試閘門仍為 BLOCKED，不應視為已取得未知公開流量的放行。**

## 1. 目前狀態

ForgeBase 核心服務目前正常，`/health/ready` 回傳 HTTP 200；另外新增的 `/health/external-test` 採 fail-closed 設計，只要正式外測所需控制仍有缺口就回傳 HTTP 503。

目前已通過 4 項：

1. RFQ 生產環境強制使用有時效、租戶綁定的簽章 challenge。
2. 對訪客／leads 的外寄總開關保持關閉。
3. Resend webhook 已建立，且簽章驗證與退信／客訴抑制機制已啟用。
4. 合成測試資料可辨識、隔離，預設不進一般 RFQ、漏斗、歸因與成效統計。

目前仍有 6 項外部資源缺口：

1. Cloudflare Turnstile 正式 site key 與 secret key。
2. 內部通知收件匣與收件 allowlist。
3. R2 正式素材物件儲存。
4. R2／S3 相容的加密 off-site 備份儲存。
5. Slack、Teams 或其他事故告警 webhook。
6. 真正從 Linode 之外執行的 uptime 監控服務。

## 2. 本輪完成項目

### 公開表單與濫用防護

- 生產 RFQ 強制驗證簽章 challenge；過期、錯誤或未帶 challenge 的完整表單會回傳 422，不會建立 RFQ。
- Turnstile 已完成前後端接線：後端呼叫官方 Siteverify，檢查成功狀態、hostname 與 action，並提供 idempotency key。
- Turnstile 未配置時不偽裝成已啟用，外測閘門會明確阻擋。
- 既有 honeypot、IP rate limit 與資料驗證保留。

### 郵件安全與 Resend 治理

- 新增平台級 `EMAIL_EXTERNAL_DELIVERY_ENABLED=false` kill switch，租戶設定無法繞過。
- 正式環境目前同時維持 `EMAIL_DRY_RUN=true`；對訪客、leads、nurture 與自動回信都不會實際寄出。
- 內部通知與測試郵件分開治理，只有 allowlist 內的精確地址或網域才可寄送。
- 建立 Resend 正式 webhook：`https://pcbrm.tw/api/v1/webhooks/resend`。
- webhook 使用原始 request body、Svix headers、HMAC-SHA256、時間容忍與事件 ID 去重；無有效簽章回傳 401。
- 永久退信、spam complaint、Resend suppression 會加入本機 suppression list；暫時性 delivery delay 不會誤封鎖地址。
- 郵件事件保存遮罩地址與 keyed identifier，避免把完整 email 不必要地複製到觀測資料。

### 測試資料隔離

- RFQ、visitor、session、event 新增 `is_test_data` 與 `test_run_id`。
- 只有帶正確秘密測試 token 的請求才可標記為合成測試。
- 合成 RFQ 跳過訪客回信、HubSpot、AgentOS、一般 webhook 與其他對外副作用。
- RFQ 清單、CSV、統計、訪客意圖、分群、漏斗、歸因、outcome 與平台摘要預設排除測試資料。
- 正式環境已建立一筆 `external-hardening-20260816` 端到端測試 RFQ，資料庫確認為 `is_test_data=true`。

### 健康檢查與觀測

- 保留 `/health/ready` 作為容器核心健康檢查，避免外部資源缺口造成服務重啟循環。
- 新增 `/health/external-test` 作為正式外測放行閘門，僅在所有條件通過時回傳 200。
- 平台健康頁分開呈現「系統可運作」與「可正式外測」，避免綠色健康狀態掩蓋外部測試缺口。
- 新增 `deploy/monitor-external.sh`，檢查首頁、API、後台登入、NorthForge、AxisForm 與兩站素材健康端點。
- 本輪八個站點／端點探針全數通過。

### 備份、還原與部署安全

- 部署前會先產生 PostgreSQL 本機備份；本輪備份：`/opt/forgebase/backups/database-20260815T212755Z.sql.gz`，70,950 bytes。
- 新增加密 off-site 備份工具，使用 AES-256-GCM，支援 S3 相容儲存的串流上傳、下載與明文雜湊驗證。
- 新增 disposable database 還原演練腳本，完成後會刪除演練資料庫，不覆寫正式資料庫。
- 因尚未提供 R2／S3 bucket 與憑證，本輪只能驗證加密 round-trip 與腳本，尚未完成真正的站外上傳及下載還原。
- Linode 規格不適合同時編譯多個 Next.js 映像。本輪並行建置曾造成主機短暫資源飽和；已修正 `safe-deploy.sh`，往後逐一建置映像，全部成功後才做資料庫遷移與容器切換。

## 3. 正式環境驗證結果

| 驗證項目 | 結果 |
|---|---|
| Core readiness | HTTP 200；database、migration、storage、scheduler 均為 ok |
| 外部測試安全閘門 | HTTP 503；正確列出 6 個未完成外部依賴 |
| 資料庫 migration | 已升級至 `0070_external_test_hardening` |
| API、DB、NorthForge、AxisForm 容器 | 正常運行；有 healthcheck 的容器均 healthy |
| 無簽章 Resend webhook | HTTP 401 |
| 缺少 RFQ challenge 的完整請求 | HTTP 422，不建立資料 |
| 合成 RFQ | HTTP 201；資料庫標記為測試資料 |
| 訪客／lead 外寄 | `EMAIL_DRY_RUN=true` 且 external delivery=false |
| 外部端點監控腳本 | 8/8 通過 |
| 瀏覽器檢查 | ForgeBase 首頁、後台登入、平台登入導向、NorthForge Contact/RFQ 均可操作且無 console error |
| API 自動測試 | 完整套件 111 passed、64 skipped；最終安全與健康指定測試 8 passed |
| 前端品質 | Admin 與 Web lint、type-check、production build 通過；Linode production images 建置成功 |

平台健康頁未登入時會導向 `/backend/platform/login`，確認平台級觀測資訊不會公開給一般訪客。

## 4. 尚未放行的資源清單

### A. Cloudflare Turnstile

需要提供或在 Cloudflare 建立：

- 適用於 `pcbrm.tw` 與 `axisform.172-233-64-5.sslip.io` 的 site key。
- 對應 secret key。
- hostname allowlist 保持精確，action 使用 `rfq_submit`。

啟用後必須在兩個租戶各完成：正常通過、缺 token、錯誤 hostname／action、重複 token 與逾時測試。

### B. 內部通知收件匣

需要一個真實的內部收件地址，例如 `sales@公司網域` 或專用測試 inbox。該地址同時寫入 `SALES_NOTIFY_EMAIL` 與 `EMAIL_INTERNAL_RECIPIENT_ALLOWLIST`；不可使用廣泛、未受控的外部網域 allowlist。

### C. R2 素材與 off-site 備份

建議分成兩個 bucket：

- assets bucket：網站圖片與文件，依租戶 prefix 隔離。
- backups bucket：私人、禁止公開存取，只供加密資料庫備份與還原。

需要 account ID、endpoint、access key、secret、bucket name；assets 另需 public/custom domain URL。憑證只放正式環境 secret，不寫入版本庫。

### D. 事故告警

需要 Slack／Teams／自有 webhook URL。至少告警：core readiness 失敗、排程器不健康、背景工作持續失敗、備份失敗、Resend complaint／異常退信率。

### E. 外部 uptime 監控

需要 Better Stack、UptimeRobot、Pingdom、Grafana Cloud 或等效服務，且探針必須從 Linode 外部執行。單純在同一台 Linode 跑 cron 不能證明 DNS、TLS、網路路徑與主機本身可用。

## 5. 放行標準

正式外測前必須同時滿足：

1. `/health/ready` 為 200。
2. `/health/external-test` 由目前 503 轉為 200，且沒有 blocker。
3. Turnstile 真實瀏覽器測試通過，並觀察一段時間的誤判率。
4. 內部通知成功送達；訪客自動回信與 nurture 仍維持關閉。
5. Resend 測試事件可驗簽入庫；退信與 complaint 能進 suppression。
6. R2 素材存取與加密 off-site backup／restore drill 通過。
7. 外部 uptime 與事故告警各完成一次實際觸發及恢復通知。
8. 對外測試期間使用 synthetic token 的內部測試不污染正式成效數字。

在上述條件全部完成前，可以繼續內部與受控測試，但**不應宣稱已完成未知公開流量的正式外測封板**。

## 6. 已知技術風險

- Alembic 實際 upgrade chain 可正常升級至 0070；但 `alembic check` 仍會偵測到專案先前累積的 model／schema metadata 漂移。這不是本輪 migration 失敗，但應另開資料庫 schema reconciliation 工作，不應宣稱 autogenerate drift 已清零。
- R2 尚未啟用前，現有素材仍依賴 Linode volume；主機或 volume 故障仍是單點風險。
- 現在的監控 shell script 已驗證可用，但在外部監控供應商設定完成前，不具備真正站外觀測能力。
- Turnstile 尚未取得正式金鑰，因此目前 `/rfq/challenge` 會顯示 `turnstile_required=false`；簽章 challenge 仍有啟用，但不等同完整 bot 防護。

## 7. 參考規格

- [Cloudflare Turnstile server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)
- [Resend webhook request verification](https://resend.com/docs/webhooks/verify-webhooks-requests)
- [Resend webhook event types](https://resend.com/docs/webhooks/event-types)
- [Resend email suppressions](https://resend.com/docs/dashboard/emails/email-suppressions)
- [Cloudflare R2 S3 compatibility](https://developers.cloudflare.com/r2/api/s3/api/)
