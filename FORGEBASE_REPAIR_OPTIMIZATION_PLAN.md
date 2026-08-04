# ForgeBase 修復與優化計畫

確認日期：2026-06-19

## 相關文件（內部連結）

| 文件 | 說明 |
|------|------|
| [DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md](./DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md) | 主策略（Leads／Capture 方向） |
| [CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md) | CF 串接計畫（與本 P0 並行） |
| [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md) | CF↔FB 發佈契約 |

本文件整理 ForgeBase 專案目前最需要處理的修復與優化工作，目標是把現有功能密度高、產品方向明確的 SaaS monorepo，推進到更適合長期營運、多人協作與生產擴展的狀態。

## 1. 目標與原則

### 1.1 主要目標

1. 修復會影響部署、資料正確性、資安與多租戶隔離的高風險問題。
2. 讓 schema、CI、部署與文件維持一致，降低 release 時的不確定性。
3. 補強 RFQ、Tracking、Contact、Visitor 等高價值資料流的租戶邊界。
4. 建立可持續的測試與契約機制，避免 Web、Admin、API 型別與行為漂移。
5. 在不大幅重寫產品功能的前提下，提升可維護性、可觀測性與擴展能力。

### 1.2 執行原則

- 先修會造成資料錯誤、部署錯誤、憑證外洩與跨租戶讀寫的問題。
- 每個修復項都要有明確驗收標準，避免只做表面整理。
- 不在高風險修復中混入大型功能開發或 UI 重設計。
- 保留既有產品方向：Capture、Intent、Conversion 三層漏斗不變。
- 對已進版控的疑似 secrets 採取「視為已外洩」的保守處理方式。

## 2. 優先級總覽

| 優先級 | 主題 | 目的 | 建議處理窗口 |
|---|---|---|---|
| P0 | Alembic migration 單一路徑 | 確保 CI/deploy/schema 真相一致 | 立即 |
| P0 | Secrets 清理與輪替 | 降低憑證外洩與生產存取風險 | 立即 |
| P0 | 高價值資料流租戶隔離 | 避免 RFQ、Contact、Visitor、Tracking 跨租戶污染 | 立即 |
| P1 | Tracking 聚合修復 | 修正租戶統計外洩與資料不準 | 短期 |
| P1 | CI/production 一致性 | 降低部署與 build 行為漂移 | 短期 |
| P1 | Rate limit 分散式化 | 讓限流在 multi-worker/水平擴展下有效 | 短期 |
| P2 | Shared contract 接入 | 降低 Web/Admin/API 型別漂移 | 中期 |
| P2 | 前端關鍵流程測試 | 覆蓋 RFQ、chat、login、plan gate | 中期 |
| P2 | 文件與版本治理 | 讓 README、ARCHITECTURE、CI、Docker 維持一致 | 中期 |

## 3. P0 修復計畫

### 3.1 Alembic migration 單一路徑

#### 現況

`api/alembic.ini` 的 `script_location` 指向 `app/db/migrations`，但目前 `0042_add_rfq_agent_run_id.py`、`0043_add_rfq_agent_draft_fields.py`、`0044_add_page_brief_agent_fields.py` 位於 `api/alembic/versions`。因此 `alembic upgrade head` 只會看到 `api/app/db/migrations/versions` 內的 head，部署與 CI 不會執行 0042-0044。

`api/tests/conftest.py` 目前又在 fixture 中手動 `ALTER TABLE` 補欄位，這代表測試環境和正式 migration 已經分裂。

#### 修復步驟

1. 將 `api/alembic/versions/0042_*` 到 `0044_*` 移到 `api/app/db/migrations/versions/`。
2. 確認 `down_revision` 串接順序為 `0041 -> 0042 -> 0043 -> 0044`。
3. 執行 `alembic heads`，確認只有單一 head。
4. 在乾淨測試資料庫執行 `alembic upgrade head`。
5. 移除 `api/tests/conftest.py` 中手動新增 RFQ/PageBrief AgentOS 欄位的 schema 補丁。
6. 補一個 migration health check 文件或 CI step，避免未來再次出現雙目錄。

#### 驗收標準

- `cd api && alembic heads` 僅回傳一個 head。
- `cd api && alembic upgrade head` 可在空資料庫成功完成。
- `api/tests/conftest.py` 不再需要手動 `ALTER TABLE` 補正式欄位。
- CI 的 API migration step 與本地 migration step 使用同一套 migration 檔案。

#### 測試

- `cd api && alembic upgrade head`
- `cd api && pytest tests/ -q`
- 若有既有 staging DB，需先在 staging 做 migration rehearsal。

### 3.2 Secrets 清理與輪替

#### 現況

目前文件與 env 類檔案中出現疑似不應進版控的內容：

- `README.md` 含生產 DB 連線字串樣式內容。
- ~~`api/.env.kinga`~~（已自工作區徹底移除；King-A demo 套件亦已清除）。
- 部分 demo/env example 使用 placeholder 是合理的，但需要統一命名與清楚標示。

#### 修復步驟

1. 從 `README.md` 移除任何真實或疑似真實的帳密、host、password。
2. ~~將 `api/.env.kinga` 改為 example~~（已刪除，不再保留 King-A 專用 env）。
3. 確認 `.gitignore` 覆蓋 `.env`、`.env.*`，但允許 `.env.example`。
4. 若這些值曾經推到遠端，將相關 DB 密碼、JWT secret、admin password 視為已外洩並輪替。
5. 補 GitHub secret scanning 或 pre-commit secret scanning，例如 gitleaks。
6. 在 README 增加「不得將 secrets 寫入 repo」與本地設定方式。

#### 驗收標準

- `README.md` 不含任何真實連線字串、密碼或 token。
- repo 內只保留 example 類 env 檔，且內容均為 placeholder。
- 遠端 secrets 已完成輪替並記錄在維運紀錄。
- CI 可偵測新增的高風險 secret pattern。

#### 測試

- 執行 secret scanner。
- 搜尋 `postgresql://`、`SECRET_KEY=`、`PASSWORD=`、`API_KEY=`、`TOKEN=`、`CLIENT_SECRET`，確認只剩 placeholder 或程式設定名稱。

### 3.3 RFQ、Contact、Visitor、Tracking 租戶隔離

#### 現況

專案已有多租戶架構與測試，但高價值轉換資料流仍有全域設計痕跡：

- `contacts.email` 是全域 unique，不是 tenant scoped。
- `visitors.visitor_id` 是全域 primary key，client 端 ID 被重用時可能跨租戶合併。
- `tracking_sessions.session_id` 是全域 primary key。
- RFQ 提交時查詢 Contact 使用 `Contact.email == body.email`，未同時限制 `tenant_id`。
- RFQ number 使用日期流水號，若全域 unique，未來多租戶同日高併發可能衝突或造成不必要耦合。

#### 修復步驟

1. 調整 Contact dedupe 邏輯為 `(tenant_id, email)`。
2. 調整資料庫唯一鍵：移除全域 `contacts.email unique`，新增 tenant scoped unique index。
3. 評估 Visitor 與 TrackingSession 是否改為複合唯一或新增 surrogate primary key。
4. RFQ public submit 讀取 Visitor、Contact、ProductLink 時加入 tenant boundary。
5. RFQ number 改成 tenant scoped 流水號，或在號碼中加入 tenant prefix。
6. 補跨租戶 regression tests：
   - 兩個 tenant 使用同一 email 提交 RFQ，不應共用 Contact。
   - 兩個 tenant 重用同一 visitor_id，不應累積到同一 Visitor。
   - tenant A 的 RFQ product link 不應連到 tenant B 的 product。
   - tenant B admin 不應查到 tenant A RFQ、Contact、Visitor 事件。

#### 驗收標準

- Contact、Visitor、TrackingSession 的查詢與寫入都有明確 tenant boundary。
- 同 email、同 visitor_id、同 session_id 在不同 tenant 下不互相污染。
- RFQ list/detail/status/assign/follow-up/events 全部維持 tenant scoped。
- 新增測試在修復前會失敗，修復後通過。

#### 測試

- `cd api && pytest tests/test_multitenant.py -q`
- 新增 `tests/test_multitenant_rfq_tracking.py`
- 跑完整 API 測試：`cd api && pytest tests/ -q`

## 4. P1 修復與優化計畫

### 4.1 Tracking events summary tenant filter

#### 現況

`GET /api/v1/tracking/events/summary` 目前聚合 `TrackingEvent.event_name`，但沒有依 `current_user.tenant_id` 過濾。這會造成租戶統計資料交叉，屬於資料隔離與商業資訊外洩風險。

#### 修復步驟

1. 在 summary query 中加入 `if current_user.tenant_id: q = q.where(TrackingEvent.tenant_id == current_user.tenant_id)`。
2. 確認 superuser 或無 tenant user 的預期行為：若是平台管理應明確走 platform admin endpoint，不應混用 tenant admin endpoint。
3. 補測試：tenant A 與 tenant B 各自寫入 tracking events，summary 只能看到自己的事件數。

#### 驗收標準

- 一般 tenant admin 無法透過 summary 看到其他 tenant 的統計。
- 測試覆蓋 query events、summary、pages、entities、strategy-performance 的租戶隔離。

### 4.2 CI 與 production build 行為一致

#### 現況

Web 的 `package.json` 透過 `scripts/run-next-build.mjs` 設定 `FORGEBASE_STRICT_BUILD_API=1`。CI 雖然跑 `npm run build`，但建置時是否有可用 API、是否符合 production strict 行為，需要明確定義與驗證。

此外 README、ARCHITECTURE、CI、Docker 對 Python、PostgreSQL、AI model 的描述不一致。

#### 修復步驟

1. 決定 Web build 是否必須在 CI 中連到 mock/staging API。
2. 若 strict build 是正式策略，CI 應啟動 mock API 或 test API，讓 build 真的驗證 runtime site-profile 流程。
3. 若允許 fallback，則文件需明確標註哪些頁面允許 fallback、哪些頁面 fail-fast。
4. 統一版本文件：
   - Python 3.12 或 3.13。
   - PostgreSQL 16 或 17。
   - AI model 預設值。
   - Linode vs Vercel 註解。
5. 在 PR checklist 加入「是否更新 README/ARCHITECTURE/CI」。

#### 驗收標準

- README、ARCHITECTURE、CI、Dockerfile、docker-compose 對核心版本描述一致。
- CI build 與 production build 的環境變數策略一致。
- Web/Admin build 失敗時能清楚指出是 API unavailable、type error 或 runtime config 問題。

### 4.3 Rate limit 分散式化

#### 現況

`api/app/core/rate_limit.py` 是 in-process sliding window，檔案內已註明 multi-worker 會讓限制乘上 worker 數。`docker-compose.yml` 使用 `uvicorn --workers 2`，因此現有限流不適合多 worker 或水平擴展。

#### 修復步驟

1. 決定 Redis 是否納入基礎設施。
2. 導入 Redis-backed rate limiter，例如 slowapi + Redis 或自建簡單 token bucket。
3. 將 login、register、contact、rfq、tracking events 的規則移到設定檔或集中常數。
4. 加入 `X-Forwarded-For` 信任代理策略說明，避免 IP spoofing 或錯取 client IP。
5. 補測試或 smoke test 驗證限流規則。

#### 驗收標準

- 多 worker 下同一 IP 的限流計數一致。
- 429 response 包含穩定格式與 `Retry-After`。
- 限流設定可依環境調整。

### 4.4 部署安全與回滾能力

#### 現況

部署流程已有 SSH、migration、重啟服務與 health check，但仍可強化：

- `StrictHostKeyChecking no` 降低 SSH 安全性。
- deploy 直接在 production 工作樹 `git checkout -- .` 與 `git pull`，回滾策略不明確。
- migration 與 app deploy 綁在同一流程，遇到不可逆 migration 時風險較高。

#### 修復步驟

1. 改用已知 host key 或 GitHub Actions known_hosts。
2. 建立 release 目錄或至少記錄 deployed commit。
3. 在 deploy 前輸出 migration heads/current。
4. 對 destructive migration 加人工確認或 staging rehearsal。
5. 建立 rollback runbook：API/Web/Admin 如何回到前一 commit、DB 如何處理。

#### 驗收標準

- 每次部署可追蹤 commit SHA、migration head、服務版本。
- health check 失敗時有明確的停止與回報流程。
- 回滾流程文件化並至少演練一次。

## 5. P2 優化計畫

### 5.1 接入 shared contract

#### 現況

`shared/package.json` 定義了 `@forgebase/shared`，但目前 web/admin 未引用。API schema、Admin type、Web type 可能由人工同步，長期容易漂移。

#### 優化步驟

1. 盤點 Web/Admin 重複定義的 API response/request types。
2. 選擇策略：
   - 由 OpenAPI 產生 TypeScript client。
   - 或將穩定 domain types 放入 `shared/src`。
3. 先從低風險且高重複的 entities 開始：Tenant、SiteProfile、Plan、Product、RFQ。
4. 在 CI 加入 shared type-check。
5. 建立 breaking change 流程：API schema 改動需同步更新 consumer。

#### 驗收標準

- Web/Admin 至少引用 shared 中的 SiteProfile、Plan、RFQ types。
- API response 變更能在 CI 階段讓前端 type-check 失敗。

### 5.2 前端關鍵流程測試

#### 現況

API 有 pytest，但 Web/Admin 目前主要依賴 type-check、lint、build，缺少使用者流程測試。

#### 優化步驟

1. 導入 Playwright 或等價 E2E 工具。
2. 先覆蓋最小高價值流程：
   - Web RFQ form submit。
   - Chat session create/message/handoff。
   - Admin login token refresh。
   - Admin plan gate 顯示與後端 feature gate 一致。
   - SiteProfile runtime branding。
3. 為 E2E 提供固定 seed data。
4. 在 CI 中先以 smoke test 模式跑關鍵流程，避免過慢。

#### 驗收標準

- PR 會跑最小 E2E smoke suite。
- RFQ 與 chat handoff 破掉時 CI 可偵測。
- Admin login/refresh 破掉時 CI 可偵測。

### 5.3 文件與版本治理

#### 現況

README 與 ARCHITECTURE 很完整，但有版本與部署資訊漂移：

- Python 3.12/3.13。
- PostgreSQL 16/17。
- AI model 名稱。
- Web 註解提到 Vercel，但目前部署原則是 Linode。
- migration 數量與實際 head 不一致。

#### 優化步驟

1. 建立單一「支援版本矩陣」章節。
2. README 只保留開發者入口，長篇營運細節拆到專門文件。
3. ARCHITECTURE 保留原則與重要決策，不放容易過期的帳密或部署實例細節。
4. 在每次 release 前更新 migration head 與版本矩陣。

#### 驗收標準

- 新人只看 README 能正確啟動本地環境。
- 維運者只看部署文件能正確部署與回滾。
- 架構文件不含 secrets、不含過期部署平台描述。

### 5.4 可觀測性與背景任務治理

#### 現況

APScheduler 在 `api/app/main.py` 中集中啟動 daily score decay、Google Ads sync、scheduled publishing、daily digest。已透過 `FORGEBASE_SCHEDULER_ENABLED` 控制 worker，但仍需要更明確的任務治理。

#### 優化步驟

1. 為每個 job 記錄 start/end/error 與 duration。
2. 建立 job run log table，或接入既有 observability。
3. 明確定義 multi-worker production 下哪個 process 負責 scheduler。
4. 為 scheduled publishing、daily digest 加入 idempotency 檢查。
5. 補 health endpoint 或 admin view 顯示最近 job 狀態。

#### 驗收標準

- 任務失敗能追蹤到 tenant、job id、錯誤內容。
- 重啟 API 不會造成重複寄信、重複發布或重複通知。
- production worker 配置與 scheduler 配置有文件化。

## 6. 建議執行時程

### 第 1 週：P0 穩定化

- 完成 migration 單一路徑。
- 清理 secrets 並輪替高風險憑證。
- 補 RFQ/Contact/Visitor/Tracking 租戶隔離測試。
- 修正已確認的跨租戶查詢與 dedupe 問題。

### 第 2 週：P1 生產一致性

- 修正 events summary tenant filter。
- 對齊 CI、Docker、README、ARCHITECTURE 版本描述。
- 決定 strict build API 策略並落地到 CI。
- 設計 Redis-backed rate limit 或先建立落地方案。

### 第 3 到 4 週：P2 可維護性

- 接入 shared contract 或 OpenAPI generated client。
- 補 Web/Admin 最小 E2E smoke tests。
- 拆分與整理文件。
- 補 deploy rollback runbook 與 scheduler runbook。

## 7. 建議分支與 PR 拆分

為降低風險，建議拆成以下 PR：

1. `fix/alembic-single-head`
   - 移動 0042-0044 migrations。
   - 移除測試 schema 補丁。
   - 補 migration health check。

2. `security/remove-tracked-secrets`
   - 清理 README/env。
   - 更新 `.gitignore`。
   - 加 secret scanning。

3. `fix/multitenant-rfq-tracking`
   - 修 Contact/RFQ/Visitor/Tracking 租戶邊界。
   - 補跨租戶 regression tests。

4. `fix/tracking-summary-tenant-scope`
   - 修 summary tenant filter。
   - 補 analytics isolation tests。

5. `chore/ci-build-version-alignment`
   - 對齊 CI、build、Docker、README、ARCHITECTURE。

6. `test/frontend-critical-flows`
   - 導入最小 E2E smoke tests。

7. `chore/shared-contracts`
   - 接入 shared 或 generated API client。

## 8. Release 前檢查清單

每個修復批次進 main 前，至少確認：

- `api` migration 為單一 head。
- `api` 測試通過。
- `web` type-check、lint、build 通過。
- `admin` type-check、lint、build 通過。
- secret scan 無高風險結果。
- 新增或修改的 public/admin endpoint 有 tenant boundary。
- 涉及 DB schema 的 PR 有 downgrade 或 rollback 說明。
- README/ARCHITECTURE 未新增過期或敏感資訊。

## 9. 完成定義

當以下條件都成立時，可以視為本輪修復與優化計畫完成：

1. Migration 只有單一來源與單一 head。
2. repo 中沒有真實或疑似真實 secrets。
3. RFQ、Contact、Visitor、Tracking 的跨租戶測試完整通過。
4. CI 與 production build 行為一致且文件化。
5. Web/Admin 至少有最小高價值流程測試。
6. shared contract 或 API client 生成策略已落地。
7. 部署、回滾、scheduler、secret rotation 都有可執行文件。

## 10. 最終建議

ForgeBase 的產品方向與架構骨架已經具備可商業化基礎。接下來不建議優先堆更多功能，而應先完成 P0 與 P1 項目，讓資料隔離、schema、憑證、CI 與部署流程達到可長期營運的水位。等這些地基穩定後，再投入 shared contract、E2E、observability 與前端體驗優化，效益會更高。
