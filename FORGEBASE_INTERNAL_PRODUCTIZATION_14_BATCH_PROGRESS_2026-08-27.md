# ForgeBase 內部產品化 14 批實作與 Code Review 紀錄

> 日期：2026-08-27  
> 北極星：匿名訪客 → 行為追蹤 → 意圖評分 → 推測公司 → 尋找公司相關聯絡窗口 → 依旅程產生個人化信件 → 寄送與追蹤 → 對方回覆 → 真人業務接手 → RFQ／成交  
> 執行原則：每一批須依序完成實作、測試、code review、修正審查發現及回歸，才可進入下一批。內部產品化完成不代表外部資料授權、法遵、寄送信譽或市場成效 Gate 自動通過。

## 14 批狀態

| 批次 | 範圍 | 實作 | Code review | 狀態 |
|---|---|---|---|---|
| I1 | 完整 North Star E2E Lab | 完成 | 通過 | 完成 |
| I2 | Browser／RBAC 自動化 | 完成 | 通過 | 完成 |
| I3 | 完整 Release CI | 完成 | 通過 | 完成 |
| I4 | Restore／Rollback 自動化 | 完成 | 通過 | 完成 |
| I5 | 日／法／俄公開網站介面包 | 未開始 | 未開始 | 待辦 |
| I6 | AI／Knowledge Eval | 未開始 | 未開始 | 待辦 |
| I7 | Fault Injection／Endurance | 未開始 | 未開始 | 待辦 |
| I8 | Performance／Capacity／Soak | 未開始 | 未開始 | 待辦 |
| I9 | Security Automation | 未開始 | 未開始 | 待辦 |
| I10 | Tenant Delivery Factory | 未開始 | 未開始 | 待辦 |
| I11 | Privacy／Retention Operations | 未開始 | 未開始 | 待辦 |
| I12 | SLO／Monitoring／Incident Console | 未開始 | 未開始 | 待辦 |
| I13 | Release Package | 未開始 | 未開始 | 待辦 |
| I14 | 類別四退場報告 | 未開始 | 未開始 | 待辦 |

## I1：完整 North Star E2E Lab

### 已實作

- 新增單一、可重跑的 PostgreSQL 全鏈整合測試，實際穿越匿名訪客、行為事件、規則式意圖評分、公司推測與人工確認、商務窗口補全與人工核准、旅程快照、個人化草稿、人工核准、模擬寄送、簽章送達 webhook、簽章回覆路由、回覆分類、真人接手、RFQ 建立、成交與直接歸因。
- 外部公司／聯絡資料與 ESP 呼叫全部使用 deterministic in-process fake；測試保留真實 DB transaction、migration、policy、feature entitlement、加密／遮罩、簽章、API route、audit、job、tenant filter 與 attribution 邏輯，且不會連線外部服務或寄送真實郵件。
- 對 snapshot、草稿、company lookup、contact enrichment、send queue、provider send、delivery webhook、inbound receipt 與 RFQ conversion 驗證 replay／idempotency，避免重試產生重複公司、窗口、信件、事件、回覆或 RFQ。
- 以第二租戶驗證歸因查詢不可跨租戶存取，且第二租戶不會取得第一租戶的 network observation。
- 新增一鍵執行器；只有 `APP_ENV=test` 且資料庫名稱含 `test`／`lab`／`batch`／`ci` 時允許執行，否則在連線或 migration 前 fail closed。
- 每次執行輸出 JUnit XML 與不含 email／IP 的 JSON milestone evidence；失敗會覆寫舊報告，避免 stale pass 被誤認為本次成功。產物統一放在 gitignore 的 `artifacts/`。

### Code review 發現與修正

1. 第一版把「系統自動建立交接」誤認為「真人已接受交接」：改為先驗證 runtime 建立 `new` handoff，再由租戶業務呼叫專用 `/accept` 動作，維持自動化與人工責任分界。
2. 第一版失敗報告在既有 JSON 存在時不覆寫，可能讓同一 artifacts 目錄留下舊的 passed 狀態：改為失敗一律覆寫 JSON；成功測試則寫入本次 milestones 與完成時間。
3. 一鍵執行器由 repository root 啟動時，Python import path 不一定包含 `api/`：明確加入 API root，確保 root／CI 呼叫方式一致。

### 驗證

- 一鍵 Lab：`1 passed`，產生 JUnit 與 JSON，完整鏈路到 `won` RFQ，direct attribution，模擬外部網路呼叫數為 0。
- 相關功能回歸：`56 passed`，涵蓋公司辨識、窗口補全、旅程草稿、受控寄送、回覆／接手與閉環歸因。
- Ruff、compileall 與 `git diff --check` 通過。
- 安全閘測試：`APP_ENV=production` 即使資料庫名稱符合測試標記仍拒絕執行，exit code 1。

### Gate 結論

- I1 內部產品化 Gate 與 code review 通過，可進入 I2。
- 本 Lab 證明的是產品程式閉環、隔離、重試安全與資料血緣，不取代外部供應商授權、真實 precision、正式 ESP／mailbox、deliverability、法遵及真實客戶成效驗證。

## I2：Browser／RBAC 自動化

### 已實作

- 新增可重跑的 Admin RBAC 驗收器，啟動隔離 API 與 Next.js Admin，建立 `owner`、`admin`、`marketing_manager`、`sales` 四種系統實際支援的租戶角色，以及獨立 Platform Superuser；未虛構系統不存在的 Viewer 角色。
- 以真實 Chromium 登入 UI 驗證未登入導向、角色標籤、允許路由、明確 403、租戶能力鎖、Platform／Tenant 分界、Sales 唯讀內容入口，以及 Owner／Sales 手機版無水平溢位。
- 以同一批短效 JWT 驗證 Team、Locale Editor、Reply Viewer 及 Platform API 權限邊界，避免 UI 與 API 權限模型各自漂移。
- 監聽全部瀏覽器 HTTP(S) request；只允許 localhost，任何外部 origin 都會使 Lab 失敗。Next telemetry 亦在驗收環境明確停用。
- 僅允許 `APP_ENV=test` 且資料庫名稱含 `test`／`lab`／`batch`／`ci`；啟動前清除精確命名的中斷殘留與本機測試登入 bucket，結束後刪除臨時 Site Profile、使用者、租戶與 bucket，並立即反查確認零殘留。
- 每次執行先移除舊 JSON、JUnit 與 failure screenshots，再輸出本次證據；Windows 使用 process-tree 終止，避免 Next child process 或測試埠殘留。

### Code review 發現與修正

1. Sales 首頁雖可正常顯示，卻在背景呼叫僅 Owner／Admin／Marketing 可讀的 locale coverage API，導致 console 403：Dashboard 現在先依角色判定，Sales 不再發出該請求。
2. 第一版僅在報告宣告外部連線數為 0，沒有實際攔查：改為對每個 BrowserContext 監聽 request，非 localhost 即留下 origin 並使專用檢查失敗。
3. 第一版在快速重跑時可能撞上共用登入限流，且僅刪除資料、沒有反查：在強制隔離測試 DB 內精確清理 localhost login bucket，並於刪除後查詢三類實體確認零殘留。
4. 第一版可能留下前一次 JSON／JUnit，且 Next dev 的 parent process 終止後仍可能留下 child：啟動時先清舊證據，Windows 改為終止完整 process tree。
5. 快速 cache hit 時，SSR input 可能在 React hydration 完成前被填值而遺失 email：登入動作等待 hydration 後才操作，消除非產品性的測試 race。

### 驗證

- 自動化 Browser／API RBAC Lab：`61 passed, 0 failed`；外部瀏覽器連線 `0`，cleanup `passed`。
- 實際 Codex 內建瀏覽器：登入頁可見，未登入開啟 `/backend/dashboard` 會導回 `/backend/login`，console error 為 0。
- Admin production build（74 routes）、ESLint、TypeScript 全數通過。
- API 權限／交付邊界回歸：`24 passed`。
- Ruff、compileall、`git diff --check` 通過；Lab 結束後測試租戶、使用者、登入限流紀錄與監聽 port 均為 0。

### Gate 結論

- I2 內部產品化 Gate 與 code review 通過，可進入 I3。
- 本批證明 RBAC UI／API 一致性與主要 desktop／mobile 管理路徑；完整瀏覽器相容矩陣、輔助科技與真實裝置驗證仍屬後續對外驗收範圍。

## I3：完整 Release CI

### 已實作

- 將原本分散且重複的 API／Frontend／Deploy checks 重構為可重用的 API Release Contract、Frontend Release Contract 與單一 Complete Release Gate；PR、`develop` push、手動執行與 `main` 生產部署共用同一套契約。
- API Gate 強制執行全 migration、完整 unit／integration／tenant isolation／public form／outbound／claim tests、coverage、schema contract、North Star 全鏈 Lab 與 blocking Python lint；所有外寄、outreach 與 inbound switch 在 CI 明確 fail closed。
- Frontend Gate 使用 matrix 覆蓋 Admin、Tenant Web、ForgeBase Marketing 與 Template Portfolio，逐一執行 deterministic install、type-check、lint、production build、production dependency audit；Templates 另執行 structure 與 rendered compliance。
- Browser Gate 在獨立 PostgreSQL service 安裝 Chromium，執行 I2 的真實登入／RBAC matrix，並保存 JSON、JUnit、log 與 failure screenshot evidence。
- Production Image Gate 實際 build API、Admin、NorthForge Web、AxisForm Web、Marketing、Templates 六個生產 image 變體；BuildKit cache 依 image 隔離，任一變體失敗即阻止發布。
- Production Topology Gate 以完整必要環境變數解析 `docker-compose.prod.yml`，並對全部 deploy shell 執行 syntax validation。
- 生產 `deploy` job 現在只依賴單一 `release-gate`；前述任何 job 或 matrix cell 失敗，都不會進入 SSH、同步、migration 或服務切換。
- workflows 採最小 `contents: read` 權限、明確 timeout、release concurrency cancellation，以及失敗時仍上傳 14 天的 API／Browser machine-readable evidence。

### Code review 發現與修正

1. 舊 CI 僅 build Admin 與 Tenant Web，遺漏實際生產的 Marketing、Templates 與 AxisForm compile-time variant：改為四前端驗證與六 image build matrix，與 production Compose 服務一一對應。
2. I1 North Star Lab 與 I2 Browser/RBAC Lab 雖可本機執行，未接入部署前硬閘：納入可重用 Release Gate，並上傳不可被 console 摘要取代的 JSON／JUnit 證據。
3. 舊 deploy workflow 自行複製部分 API／Frontend checks，容易與一般 CI 漂移：抽成 `workflow_call` 契約，部署與 PR 只保留一份真實定義。
4. 逐一 image build 仍不能證明 Compose 變數與依賴圖有效：新增 production topology 與 deploy shell syntax Gate。
5. I2 runner 在 Windows 終止 process tree，但在 Linux 只終止 parent，GitHub runner 可能殘留 Next child：Linux 啟動獨立 process group，結束時對整組送出 TERM，逾時再 KILL。
6. 初稿把 CI 中 `push: false` 的 image build 稱為 immutable image，語意超過實際證據：更名為 production image contract；正式部署仍由既有 safe-deploy 在目標主機建置與記錄 manifest。

### 驗證

- `actionlint 1.7.12`：三個可重用／統一 Gate 及部署 workflow 全數通過。
- API：`299 passed, 3 skipped`；3 項 skip 僅屬已鎖定退場／外部 repository 才可執行的 AgentOS 測試，核心 ForgeBase 測試無 skip；migration、schema contract、North Star Lab（`1 passed`）及 blocking Ruff lint 通過。
- Admin／Tenant Web／Marketing／Templates：四組 type-check、lint、production build、production dependency audit 全數通過，各組 `0 vulnerabilities`；Template structure／compliance 通過（6 templates、66 static pages）。
- Docker：5 份 Dockerfile 的 BuildKit check 無警告；API、Admin、NorthForge、AxisForm、Marketing、Templates 共 6 個生產 image 變體皆完成實際 build。
- Production Compose `config --quiet`、全部 deploy shell `bash -n`、Browser/RBAC `61 passed, 0 failed`、Ruff、compileall 與 `git diff --check` 通過。

### Gate 結論

- I3 內部產品化 Gate 與 code review 通過，可進入 I4。
- CI 已阻擋程式、權限、資料庫契約、前端與 image build 回歸；外部供應鏈簽章、正式 registry immutable promotion 與更深入 security scanning 由 I9／I13 接續，不在本批虛構為已完成。

## I4：Restore／Rollback 自動化

### 已實作

- `backup.sh` 改為 restricted umask、`.partial` 寫入、gzip integrity check 與 atomic rename；同名 database／Compose／manifest 任一存在即 fail closed，不覆寫既有 recovery point。
- 每個 DB backup 伴隨不展開 secrets 的 Compose snapshot 與 JSON manifest，記錄 SHA-256、compressed bytes、Alembic head、public table count、North Star 關鍵資料表 row counts、off-site 狀態及 object key。
- 本機 recovery point 即使設定中的 off-site upload 失敗仍保留完整 manifest，並把 `offsite_status` 寫成 failed；部署則維持失敗，不把「本機可用」誤當成「異地備份成功」。
- Off-site download 在 AES-256-GCM authentication 外，強制讀取 object metadata 的 plaintext SHA-256 並以 constant-time compare 驗證；metadata 缺失、checksum 錯誤或 ciphertext 損壞時刪除所有 partial plaintext／encrypted temp file。
- `restore-drill.sh` 同時支援 `--local` 與 `--offsite`，只建立唯一 `forgebase_restore_drill_*` disposable database；驗證 gzip、checksum、Alembic head、table count 與核心 row counts後輸出 RTO／backup age evidence，結束時只刪除該 drill database。
- `rollback.sh` 新增完整 preflight 與 `--dry-run`：拒絕未知／重複 service、遺失 image、與 Compose 不一致的 target；所有項目先通過才 tag／recreate。manifest 含 API 時必須明確提供 `--approve-api-schema-compatibility`。
- 實際 rollback 後逐一等待 container running／healthy，再輸出 JSON evidence；資料庫永不自動回復，evidence 明確記錄 `database_restored: false`。
- 新增隔離 Recovery Lab：啟動專屬 PostgreSQL／Compose project，建立 point-in-time 資料，跑真實 backup／restore，拉兩版 Alpine images，先驗 dry-run 再實際回切 API／Web，最後刪除 container、network、volume、image tags、temp DB、temp files 與 lock。
- Complete Release Gate 新增 Recovery Drill job 並保存 JSON／JUnit／restore／rollback evidence；production topology job 另以 ShellCheck 驗證五支 recovery／deployment 控制腳本。

### Code review 發現與修正

1. 舊 restore drill 只能使用 off-site key，且只確認「至少有一張表」：加入 local recovery point 模式，以及 checksum、schema version、table count 與核心 row counts 對帳。
2. Off-site object 雖保存 plaintext checksum，下載時從未驗證：新增 metadata 格式驗證與 plaintext 串流 SHA-256 比對；corrupt／missing metadata 都 fail closed。
3. 第一版 checksum failure 已刪 destination，但 AES-GCM decrypt failure 可能留下部分 plaintext：所有 decrypt／checksum exception 現在都先刪 plaintext，再刪 encrypted temp。
4. 舊 rollback 邊讀 manifest 邊 tag，後段才發現壞資料時可能形成 partial mutation：改為完整解析、去重、Compose target 與所有 image preflight 後才允許第一個 tag。
5. 舊 rollback 可讓舊 API 直接碰新 schema：API 回切新增人工 schema compatibility acknowledgement；dry-run 可在不變更 image 或 container 下完成同一套 preflight。
6. 同秒或指定相同 stamp 可能覆寫備份／evidence：備份拒絕任何既有 target，restore／rollback evidence 增加唯一 suffix；Lab 也以 atomic lock 阻止同 checkout 並行污染共用測試 tags。
7. Lab 初稿成功才輸出總報告，失敗可能讓 CI 上傳舊證據：每次先刪精確舊 evidence，EXIT trap 會在失敗時輸出本次 failed JSON／JUnit，再清理隔離資源。
8. 初稿先做 off-site upload 才寫 local manifest，網路失敗會留下無 metadata 的 SQL：manifest 改為先落盤，upload 成功／失敗再更新 off-site 狀態。

### 驗證

- 隔離 Restore／Rollback Lab：`11 passed, 0 failed`；最近一次 point-in-time restore RTO `2s`，backup age `2s`，`production_resources_touched: false`。
- Lab 後殘留驗證：container `0`、測試 image tag `0`、lock `0`、disposable restore database `0`。
- Off-site encryption／download／checksum／corruption 與 external hardening：`8 passed`。
- ShellCheck、`bash -n`、Actionlint、blocking Ruff 與 `git diff --check` 通過；Recovery Lab 已接入 release deployment dependency graph。

### Gate 結論

- I4 內部產品化 Gate 與 code review 通過，可進入 I5。
- 本批證明 recovery tooling 與隔離演練可重跑，不宣稱 production RPO／RTO 已達標；正式數字仍須由排程頻率、off-site bucket、真實資料量及 production restore drill evidence 決定。資料庫正式回復維持人工核准，避免自動覆寫客戶資料。
