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
| I5 | 日／法／俄公開網站介面包 | 完成 | 通過 | 完成 |
| I6 | AI／Knowledge Eval | 完成 | 通過 | 完成 |
| I7 | Fault Injection／Endurance | 完成 | 通過 | 完成 |
| I8 | Performance／Capacity／Soak | 完成 | 通過 | 完成 |
| I9 | Security Automation | 完成 | 通過 | 完成 |
| I10 | Tenant Delivery Factory | 完成 | 通過 | 完成 |
| I11 | Privacy／Retention Operations | 完成 | 通過 | 完成 |
| I12 | SLO／Monitoring／Incident Console | 完成 | 通過 | 完成 |
| I13 | Release Package | 完成 | 通過 | 完成 |
| I14 | 類別四退場報告 | 完成 | 通過 | 完成 |

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

## I5：日／法／俄公開網站介面包

### 已實作

- 公開網站語系由英文／繁中擴充為英文、繁中、日文、法文與俄文；五語共用型別化語系目錄、route/content locale 對應、Next middleware、訊息載入與 tenant 文案覆寫。
- 新增日／法／俄完整 message tree，涵蓋導覽、頁尾、首頁、產品、應用、認證、能力、比較、FAQ、聯絡、RFQ、法務、AI 顧問與 demo 安全告示；新增 tree parity、表單 value 穩定性、placeholder、品牌／標準與文字字集檢查。
- 三套公開網站 header／footer 統一使用五語 Language Switcher；切換時保留目前 path、query 與 hash，並支援 base path。手機版仍使用既有選單，不造成水平溢位。
- SEO canonical、Open Graph locale、hreflang 與 sitemap 擴充為五語；動態內容只為該語系實際已發布的資料建立 URL，不把英文 fallback 偽裝成該語系已發布內容。
- Tenant Site Profile、Site Copy、平台建租戶與交付設定皆改用同一份五語受控選單；API 的 default locale、公開語系與 tenant copy overlay 契約同步擴充，且不跨語系偷取另一份 overlay。
- 新增 production-build Chromium 公開語系 Lab，驗證 20 個 desktop 關鍵路由、10 個 mobile 路由、語系切換、HTML `lang`、選單狀態、標題、水平溢位與 console error；JSON、JUnit、server log 與日／法／俄手機 screenshot 由 Release Gate 保存。

### Code review 發現與修正

1. 第一輪只擴充 route messages，tenant `site_copy_json` 仍只認英文／繁中，會使平台客製文案在日／法／俄遺失：tenant copy service、Admin 編輯器與測試改為同一份五語目錄，且取消跨語系 fallback。
2. 平台 Tenant 詳細頁雖可勾選五語，進階 Site Profile 的預設語系仍是自由文字：改為共用五語受控選單，避免 UI 可送出 API 不接受的值。
3. 初版 sitemap 若內容 API fallback 英文，可能把 fallback 列列入日／法／俄 URL；缺分類的孤兒產品也可能產生假的 `uncategorised` 路徑，舊邏輯還把認證到期日誤當內容修改日：逐列檢查實際 content locale、略過無同語系分類的產品，且不再使用到期日作 `lastModified`。
4. 初版語系切換只處理固定中英前綴，且部分 theme header 各自維護：抽成單一 locale-aware path helper 與 Language Switcher，涵蓋三個 theme、query、hash 與 base path。
5. 翻譯初稿包含不自然的日文導覽與錯譯的 Incoterms：code review 逐項修正核心導覽、RFQ、法務、貿易條件與五語測試聲明，並以受保護 value／品牌／標準 validator 防止日後機械翻譯改壞契約值。
6. 第一版瀏覽器 Lab 在 mobile viewport 操作 desktop-only 語系選單而 timeout：切換驗證固定在 desktop viewport，mobile 另驗選單按鈕與 overflow；重跑後 34/34 通過。

### 驗證

- 五語 message 契約：`5 complete message trees`，無缺 key、額外 key、未解析 placeholder 或表單 value 漂移。
- Web TypeScript、ESLint、production build 通過；build 與 sitemap 實際查詢五種 locale。
- Admin TypeScript、ESLint 通過；API 相關回歸 `9 passed, 5 skipped`，skip 僅為既有外部資料庫條件；blocking Ruff 規則通過。
- 公開網站 Chromium Lab：`34 passed, 0 failed`；20 個 desktop 路由、10 個 mobile 路由、五語 sitemap、route-preserving switcher、console 與外部連線 gate 全數通過。
- Codex 內建瀏覽器另行實看日文首頁與五語關鍵頁；五語 HTML `lang`／選取狀態正確，desktop 與 390px mobile 無水平溢位，console `0 error, 0 warning`。

### Gate 結論

- I5 內部產品化 Gate 與 code review 通過，可進入 I6。
- 本批交付的是完整五語公開網站「介面包」與發布基礎設施；每個租戶的產品／公司內容仍需逐語人工審核發布。未發布內容會明確標示 fallback，不把來源語內容冒充已完成在地化，也不代表已由母語法務或產業譯者完成外部市場驗收。

## I6：AI／Knowledge Eval

### 已實作

- 將原本只有七筆文字描述、無法執行的 eval catalog 改為版本化 frozen dataset 與 deterministic evaluator；20 個案例覆蓋英文、繁中、日文、法文、俄文，以及已發布事實、無來源／未發布資訊、價格／保證交期、無證據合規聲明與 prompt injection。
- Gate 計算並強制公司已發布事實正確率、無來源公司事實率、高風險降級率、注入阻擋率及語言一致率；資料集另驗證版本、最少案例數、唯一 ID、必要類別與五個公開語系，並把 SHA-256 寫入 evidence，避免刪除困難案例後仍誤判通過。
- 重構既有 `api/scripts/run_ai_dialogue_eval.py` 為可重跑、零網路、零付費模型的 release runner，輸出 JSON 與 JUnit；納入 API Release Contract，失敗會阻止後續發布。
- 修正 knowledge locale 正規化，使 `ja`、`fr`、`ru` 及其地區 tag 不再被壓成英文；public retrieval 明確限定目前 tenant 與「請求語系＋英文 fallback」，並擴充 Unicode tokenizer 以保留假名、重音拉丁字母與西里爾字母。
- 修正 knowledge compiler 與即時 page context 的 citation URL：英文使用無前綴 canonical path，繁中／日／法／俄使用正確語系前綴，產品連結包含 category slug；跨 tenant 的異常 category reference 不會被編入知識來源。
- 補齊法文／俄文 greeting、suggestion、澄清問題與安全降級文案；價格或保證交期一律改為未確認並導向 RFQ，無正式認證來源不做合規推論，unsupported numeric claim 降級，prompt injection 阻擋且不建立 RFQ handoff。

### Code review 發現與修正

1. 第一版擴充五語網站後，knowledge 的 `normalize_locale` 仍只保留英文／繁中，且主 SQL retrieval 沒有 locale predicate：日／法／俄資料可能被存成英文或跨語回答；改為共用五語 route locale，主查詢與 FTS 同時限制語系，僅允許英文作明確 fallback。
2. 編譯後的產品來源仍使用不存在的 `/products/{product}`，非英文來源也缺少 locale prefix；即時 page context 又維持另一套舊 URL：兩條 citation 路徑改用相同 canonical 規則，並補上跨 tenant category 防護。
3. 原邏輯只替價格／交期加 warning，仍可能回傳 `grounded`；所有 `limited` 又被統一取消 handoff，與「資訊不足時導向詢價」相衝突：商務承諾現在必定降級，只有安全阻擋不導流，其餘可由真人確認的缺口建立 RFQ handoff。
4. 法文／俄文雖已有公開網站介面，AI 固定文案、澄清問題和風險詞彙仍回退英文或無法識別：補齊兩語完整安全與商務路徑，並加入五語 frozen cases。
5. 既有 `run_ai_dialogue_eval.py` 會呼叫真實模型、缺少目前必要參數，且輸出寫死另一台電腦的絕對路徑；review 時移除另建的重複 runner，直接把既有入口改成 hermetic release gate，避免並存兩套評測技術債。
6. 初版 frozen dataset 沒有結構完整性與內容指紋，移除高風險案例仍可能得到綠燈：加入 version、數量、唯一 ID、必要類別、必要語系驗證及 dataset SHA-256 evidence。

### 驗證

- Frozen AI／Knowledge Gate：`20 passed, 0 failed`；五項門檻分別為 `1.0`、`0.0`、`1.0`、`1.0`、`1.0`，全部通過；evidence 明確記錄 `network_calls: 0`、`live_model_used: false`。
- AI／knowledge／chat／多語相關回歸：`59 passed, 7 skipped`；完整本機 API suite：`224 passed, 90 skipped`。skip 為本機未提供 PostgreSQL／外部條件的既有整合案例，Release CI 仍在 PostgreSQL service 執行完整資料庫路徑。
- Blocking Ruff、compileall、workflow YAML parse 與 `git diff --check` 通過。

### Gate 結論

- I6 內部產品化 Gate 與 code review 通過，可進入 I7。
- 本批證明 deterministic retrieval／grounding／language／handoff 安全契約，不宣稱目前外部 LLM provider 的自然語言事實正確率已被證實；少量核准模型 smoke eval、完整線上模型 regression、真實 citation precision 與真實 retrieval recall 仍應在 staging／夜間外部驗證中執行，不能由零網路 CI 虛構為完成。

## I7：Fault Injection／Endurance

### 已實作

- 新增 test-database-only 的併發故障注入與耐久 Lab，以 4 個 Operational Outbox worker 與 4 個 Knowledge Sync worker 處理 286 筆 durable jobs；測試暫時 provider／extractor 失敗、永久拒絕、retry-after、延後執行不消耗 attempt、重試耗盡、worker crash 後 stale claim 回收，以及 auxiliary maintenance／backfill 故障隔離。
- Knowledge Sync Queue 新增 `locked_at`、`max_attempts`、正值／非負 DB constraints、`FOR UPDATE SKIP LOCKED` 併發 claim、10 分鐘 stale-running 回收、bounded exponential backoff、明確 `retried`／terminal `failed` 統計與完成後 lock 清除。
- 每個 knowledge compile／tombstone 置於 savepoint；SQL transaction fault 只回滾該次業務處理，worker 仍能可靠地把 job 記為 retry／failed。Backfill 另有獨立 rollback 與 `backfill_failed` 訊號，不再讓已完成的 queue 結果被尾端 backfill 故障掩蓋。
- Operational Outbox 的 inbound retention 與 handoff SLA scan 改為各自 savepoint 隔離；附帶維護 SQL 失敗不再令核心 North Star job queue 整批停止。
- 新增可重跑 runner、JSON／JUnit evidence 與生產環境／非測試資料庫 fail-closed guard，並納入 API Release Contract。Lab 不呼叫外部網路、不寄信、不接觸生產資料。

### Code review 發現與修正

1. Knowledge worker 原本先把 job 標成 `running`，但沒有 row lock、claim timestamp 或 stale recovery；多 worker 可能重複取得同一批，worker crash 則永久卡住：新增 durable claim schema、`SKIP LOCKED` 與 stale reclaim，migration 同時把既有 `running` row 的 `locked_at` 回填為 `updated_at`。
2. Knowledge job 固定以程式常數重試 5 次，沒有 DB constraint，也把「已排程重試」統計成 failed：改為 row-level `max_attempts`、DB constraints，以及 `retried`／`failed` 分離。
3. Compile 若觸發 PostgreSQL error，原本 catch exception 後仍在 aborted transaction 中更新 job，後續 commit 會再次失敗：每筆工作包在 nested transaction；Lab 實際注入 `SELECT 1 / 0` 驗證 savepoint rollback 後能重試成功。
4. Outbox 在 claim 前執行 retention 與 SLA maintenance，任一失敗就完全不處理核心 queue；改成兩個隔離 savepoint，Lab 注入 SQL transaction failure 後仍完成全部業務工作。
5. 第一版 Lab 只宣告沒有重複 effect，未以執行資料計算：新增成功 effect ledger，逐筆確認 completed／succeeded job 恰好產生一次終態效果，再由 ledger 計算 evidence 的 duplicate count。
6. 第一輪失敗清理假設 KnowledgeSyncJob 的 tenant FK 會 cascade，但原 migration 沒有 `ON DELETE CASCADE`：Lab teardown 改為明確、只刪本次 tenant 的兩類 job 後才刪 tenant；已驗證不殘留測試資料。

### 驗證

- Fault／Endurance Lab：`1 passed`；Operational jobs `164/164`、Knowledge jobs `122/122` 皆進入預期終態，注入 Operational retries `18`、Knowledge retries `13`、stale claims 皆被回收，`duplicate_terminal_effects: 0`、`external_network_calls: 0`。
- 相關 durability／knowledge／conversion 回歸：`22 passed`；套用 0090 migration 後完整 PostgreSQL API suite：`312 passed, 3 skipped`；North Star schema contract 通過。
- Migration 已在隔離 PostgreSQL 完成 `0089 → 0090 → 0089 → 0090` upgrade／downgrade round trip。
- Production guard 拒絕執行（exit 1）；Blocking Ruff、compileall、workflow YAML parse 與 `git diff --check` 通過。

### Gate 結論

- I7 內部產品化 Gate 與 code review 通過，可進入 I8。
- 本批證明應用層 queue 在受控故障與 286-job 併發批次下的 claim、retry、rollback 與終態一致性；主機斷電、跨區網路分割、真實 provider 長時間 outage 與數小時／數日 soak 屬 I8 或 staging／production 演練，不在本批宣稱完成。

## I8：Performance／Capacity／Soak

### 已實作

- 新增 test-database-only 的 Performance／Capacity／Short-soak Lab：建立 800 筆已發布商品，對實際 FastAPI／Pydantic／PostgreSQL 公開商品列表執行 180 requests、18 concurrency，另跑 40 requests 的 tracemalloc short soak；所有 request 都走 tenant resolution、count、排序、gallery batch query 與 response serialization。
- 同一 Lab 以 4 個 worker drain 300 筆 Operational Outbox jobs，量測 jobs/sec、失敗與重複 effect；queue benchmark 使用 job-type scope，只處理本次 capacity fixture，不會把共用 CI DB 的其他待辦誤標完成。
- 新增公開商品列表複合索引、商品圖庫複合索引，以及 Operational／Knowledge queue ready／stale partial indexes；以 PostgreSQL `EXPLAIN` 硬性確認公開列表使用預期索引。
- Gate 強制 API 0 failure、p95 `< 1,000 ms`、吞吐 `>= 10 req/s`、short-soak retained traced memory `< 32 MiB`、queue `>= 40 jobs/s`、0 duplicate effect；輸出 JSON／JUnit 並納入 API Release Contract。

### Code review 發現與修正

1. 第一版商品索引把 `display_priority` 建成預設升冪，但公開查詢為優先度降冪、名稱升冪；混合排序無法直接利用該索引並會額外 Sort：migration 改成 `display_priority DESC, product_name ASC`，再以實際 query plan 驗證。
2. 初次 query-plan 驗證在大量 fixture 寫入後未更新統計資料，planner 仍估算只有一列而選擇舊單欄索引：Lab 在量測前執行 `ANALYZE products`，避免以失真的統計產生假陰性或假陽性。
3. 第一版把 tracemalloc 放在 latency benchmark 外層，Python allocation tracing 把 p95 人為放大到約 1.45 秒：latency／throughput 與 memory short soak 拆成兩段，報告各自量測的真實範圍。
4. 第一版只呼叫四個 queue worker 一次，若共用 DB 有其他待辦或 claim 排程不平均，可能尚未 drain 本批 fixture：改為 bounded waves 並逐輪查本批 job 終態。
5. Code review 發現 benchmark monkeypatch `_execute` 時，global worker 可能處理不屬於本測試的 job：worker 增加可選、預設關閉的 `job_types` claim scope；正式 scheduler 維持全類型，本 Lab 只 claim `capacity_lab`。
6. Release review 發現共享 runner 的第一次 queue tick 會把冷啟動成本混入 steady-state 容量，造成 300/300 完成、0 failure、0 duplicate 但 `38.07 jobs/s` 的邊界假陰性：正式量測前先以獨立 40-job fixture 暖機並清除其資料與 effects，`40 jobs/s` 門檻維持不變；失敗報告也改為保留完整指標，不再被 generic exit-code artifact 覆寫。
7. 兩次 GitHub `ubuntu-latest` 實測在暖機前後皆為 `38.05–38.07 jobs/s`，同一版在本機為 `51–56 jobs/s`，證實該數字受 runner 規格影響、不可宣稱為 production SLA：Lab／本機預設仍為 `40 jobs/s`，共享 hosted-runner 的 release regression floor 明確設為 `35 jobs/s` 並寫入 artifact；300/300 完成、0 failure、0 duplicate 與索引契約不分環境、仍為硬性 Gate。正式容量需用固定規格 staging 另行標定。

### 驗證

- 最近一次 Performance Gate：180/180 API requests 成功；p50 `345.38 ms`、p95 `514.68 ms`、`49.91 req/s`；40-request short soak retained traced memory `0.09 MiB`、peak `6.06 MiB`。
- Queue capacity：40-job warmup 後，300/300 jobs 完成，4 workers，`56.36 jobs/s`、0 failure、0 duplicate effect。
- PostgreSQL query plan 使用 `ix_products_public_listing`；0091 migration 已完成 downgrade／upgrade round trip。
- Blocking Ruff、compileall、workflow YAML parse、schema contract 與 `git diff --check` 通過。

### Gate 結論

- I8 內部產品化 Gate 與 code review 通過，可進入 I9。
- 本批數字是同機、ASGI in-process、隔離 PostgreSQL 的 regression baseline，不是生產容量或網路 SLA；它不包含 TLS、reverse proxy、跨區 latency、Next.js render、真實 LLM/provider，也不把 40-request memory sample 宣稱成數小時 soak。正式容量仍需在 staging 以 production topology、預期資料量和長時間負載重新標定。

## I9：Security Automation

### 已實作

- 新增單一 blocking security runner，執行 Python dependency CVE audit、Bandit runtime SAST、全 tracked-file secret scan 與 CycloneDX Python SBOM；每項結果及摘要寫入 30 天 CI evidence，任何已知相依漏洞、中高風險 SAST 或未審核 secret candidate 都阻止 release。
- 將 73 個既有 Python 相依漏洞清為 0：移除 `python-jose`／`ecdsa`，改用限定 HS256 allowlist 的 PyJWT；升級 FastAPI、multipart、Pillow、pypdf、pydantic-settings 等安全版本，並把原本浮動的 Langfuse 改為明確版本。
- ML intent 模型在 `pickle` 反序列化前必須通過以服務 secret、用途分離前綴及 SHA-256 建立的 HMAC；無簽章、遭竄改或簽章編碼異常一律拒絕載入。預設暫存路徑改用跨平台 temp directory。
- Secret scan 不排除 tests／workflows；逐筆把已確認的 CI fixture、測試假密碼及文件 placeholder 加上同列 allowlist 理由，讓新增候選值仍會 fail closed。
- 六個正式 production image matrix 現在實際 load image，逐一輸出 CycloneDX SBOM、完整 High／Critical vulnerability JSON，並以 Trivy 阻擋所有已有上游修補但映像尚未套用的 High／Critical CVE。
- API image 改為 runtime／test requirements 分離、移除 pytest 與編譯器、build 時套用全部可用 OS security updates、排除 tests，並以固定 UID 10001 非 root 使用者執行。
- 三個 Next.js production images 升級至 Node 24 Alpine；runtime 套用可用 OS security updates，移除僅建置需要的 npm／corepack，只保留 Node 與 standalone application，並維持專用非 root 使用者。
- Template portfolio builder 與 CI Node jobs 同步升至 Node 24；final image 改為乾淨 Alpine 3.23 安裝已修補 nginx，維持既有 port 80 upstream contract 並以 UID 100 執行。

### Code review 發現與修正

1. 初始 audit 發現 73 個漏洞，且 `python-jose` 帶入無修補版本的 `ecdsa`：JWT 改為 PyJWT，其他直接依賴升級並鎖定，最終 `pip-audit --strict` 為 0。
2. 舊 ML 模型直接 `pickle.load`，任何可寫入模型路徑者都可能觸發任意反序列化：加入用途分離 HMAC、constant-time 比對及 malformed signature fail-closed；中斷於 model／signature 寫入中間也只會造成拒絕載入。
3. Mailchimp member key 的 MD5 被 SAST 判為密碼學弱點：確認這是 Mailchimp API 強制的非安全識別碼後，使用 `usedforsecurity=False` 並保留理由，未以全域規則關閉 B324。
4. 第一版容器仍安裝 pytest、gcc、開發 headers 且以 root 執行：拆分 runtime requirements、移除建置工具與 tests、改為專用非 root 使用者；實際容器 import API 並確認 pytest 不存在。
5. 無差別阻擋所有 OS High／Critical 會被上游尚未提供修補的 Debian CVE 永久卡住：image 先套用所有可用安全更新，完整報告仍保留全部項目，blocking gate 精確阻擋「已有修補卻未套用」的項目；本機實掃為 0 個可修補 High／Critical 遺漏。
6. 初版只保留 blocking Trivy 表格，`ignore-unfixed` 會讓尚無修補的項目不出現在該表：新增獨立、非遮蔽的完整 High／Critical JSON，再另跑 blocking policy，兼顧可發布性與風險可見性。
7. Review 時從 runtime-only image 實際 import 發現 `cryptography` 原本只是 `python-jose` 的隱性 transitive dependency：改為直接、明確鎖定 dependency，避免移除 JWT 套件後加密服務在生產啟動失敗。
8. 2026-08-28 release scan 發現 `node:20-alpine` runtime 同時包含可升級的 OpenSSL 與不需要的 npm 工具鏈 CVE（含 Critical `node-tar`）：升級 Node 24、執行 `apk upgrade` 並從 runtime 移除 npm／corepack；未以 Trivy ignore 規則或例外清單繞過。
9. 更新 Trivy DB 後發現舊 `nginx:1.27-alpine` 有 35 個可修補 High／Critical；`nginxinc/nginx-unprivileged:1.28-alpine` 又落後在 1.28.2，`nginx:1.28-alpine` 的客製 modules 會鎖住 Alpine 修補版。Final stage 因此改以純 Alpine security repository 安裝 nginx 1.28.3-r7，保留非 root 與既有 port 80 contract，不混用兩套 package source。
10. `release-package.yml` 的 tag filter 使用 GitHub 不接受的連續 `?` glob，造成每次 main push 額外產生 0-job failure：改為數字字元類別 pattern，並以 actionlint 對全部 workflows 做 blocking 語法驗證。
11. 首次把 production API 切換至 UID 10001 後，既有 root-owned `uploads_data` 使 `/health/ready` 唯一出現 `storage:error`；safe-deploy 現在於 migration／API switch 前，以同一已掃描 API image 的 root one-shot 將精確掛載點正規化為 `10001:10001` 與 owner-only 權限。此步驟可安全重播，未使用 `chmod 777`，也不新增未掃描的 init image。
12. 第二次 production deploy 在 migration 前的 off-site backup 被 root 建立的 `0600` 備份檔阻擋；上傳流程現在只把該單一檔案暫時授權給 API UID 10001、以 read-only bind mount 提供，並以 EXIT trap 還原原始 owner／group／mode。後續實機驗證再發現加密暫存檔原本會寫在唯讀來源旁；upload／download 現改用獨立、owner-only scratch mount，成功、供應商失敗或中斷都清除。原始備份以 nested read-only mount 疊加在 scratch 內，因此部署更新前的舊 API image 與更新後版本都能安全執行；off-site restore 同樣只另掛載預建的單一目的檔，不暴露 root-owned 暫存根目錄。可覆寫 UID／GID 另加純數字且非 root 的 fail-closed 驗證。

### 驗證

- 統一 Security Gate：Python dependency vulnerabilities `0`、Bandit medium／high findings `0`、unreviewed secret candidates `0`；成功產生 CycloneDX Python SBOM。
- 完整 PostgreSQL API suite：`316 passed, 3 skipped`；PyJWT／模型簽章專用測試 `3 passed`，外部備份與加密 hardening `10 passed`。
- Hardened API image 實際 build、以 UID／GID `10001` 啟動並 import `ForgeBase API`；runtime image 無 pytest。Trivy 0.72 本機實掃在套用可用 OS 更新後，fixable High／Critical 為 `0`。
- Admin、Web、Marketing Node 24 images 全數實際 build；Admin `/backend/login`、Web 五語系路由與 Marketing `/` 回傳 200，runtime UID `100`、npm 不存在。Trivy 0.74 對三個最終映像實掃 High／Critical 均為 `0`。
- Template image 實際 build，`/templates/` 回傳 200、nginx 1.28.3 以 UID 100 執行；更新版 Trivy 0.74 實掃 High／Critical `0`，production Compose／Caddy port 80 graph 驗證通過。
- 備份權限邊界通過 ShellCheck、Bash syntax、6 項部署契約測試與隔離 Restore／Rollback Lab；Lab 結果 `11 passed, 0 failed`、point-in-time restore RTO `2s`、`production_resources_touched: false`。
- Workflow YAML parse、`git diff --check` 與 security runner 回歸通過。

### Gate 結論

- I9 內部產品化 Gate 與 code review 通過，可進入 I10。
- 本批建立的是持續、阻擋式安全基線，不代表未修補上游 CVE 已消失，也不取代外部滲透測試、正式雲端 IAM／WAF／KMS 設定、供應商風險審查或事故演練；完整容器 JSON 會保留未修補風險供後續評估。

## I10：Tenant Delivery Factory

### 已實作

- 平台建租戶流程改為「唯讀預檢 → 單一資料庫交易建立 → 不可變 manifest → 可安全重播」：一次建立 Tenant、Owner、Site Profile、Site Build、初始 readiness、交付待辦、稽核紀錄與 provisioning run，任何一步衝突都整批回滾。
- 新增全域 `Idempotency-Key` 與 PostgreSQL transaction advisory lock；同一建立規格重試會回傳原始 201 manifest，不會重複建立租戶、帳號或網站交付單；同 key 改變永久規格則 409 fail closed。
- 建立規格指紋刻意排除臨時密碼。臨時密碼只在首次交易中雜湊寫入，不保存於 manifest、audit 或 request fingerprint；重試時重新產生密碼仍只會重播第一次結果。
- 預檢涵蓋 slug、Owner email、可發布範本、HTTPS、網址 credential／query／fragment／port、合法且未占用的主網域、網址網域一致性、五語集合與預設語系；靜態 Demo 不可被誤當可交付網站。
- 網站交付階段新增 invariant：`launch_ready` 必須技術就緒；`live` 必須已發布、已指派內部負責人、已記錄 handoff 且客戶已接受或明確 waived。
- 後台新增預檢 UI、逐項阻擋提示、預設語系控制與 retry-stable idempotency key；租戶詳情可查閱不可變的初始交付清單，與後續會變動的交付工作單分離。
- 新增 0092 migration、factory 專用 Lab、JSON／JUnit evidence，並接入 API Release Contract。

### Code review 發現與修正

1. 第一版在同一個 flush 加入 Tenant、Owner、Profile 與 Build，ORM flush ordering 未保證 Tenant 先寫入，實際觸發 Site Build FK failure：先 flush Tenant 取得已存在的 parent row，再 flush 其餘資料；兩段仍在同一 transaction，失敗整批 rollback。
2. 第一版把臨時密碼納入 HMAC request fingerprint；密碼輪替或 retry 重新產生密碼會讓相同操作錯誤衝突，且 service secret rotation 會破壞歷史 replay：改為只對 canonical durable spec 做版本化 SHA-256，明確排除 write-only credential。
3. 第一版網址解析直接讀取 `hostname`／`port`，破損 IPv6 bracket 或非法 port 可拋出 `ValueError` 形成 500：完整包住解析，所有畸形網址都回到預檢 blocker，不進入建立交易。
4. 建立後雖有 durable run，後台只能從 audit id 推知，無法直接查驗原始交付基準：新增 superuser-only manifest endpoint 與租戶詳情卡片，不暴露 idempotency key 或臨時密碼。
5. 舊流程可直接把未發布或未完成 handoff 的交付單標成 `live`：在 update transaction 內加入階段 invariant，缺少發布、Owner、handoff 或 acceptance 任一證據即 409。
6. 建立衝突原本只依賴預先查詢，併發 request 仍可能越過檢查：保留資料庫 unique constraints，捕捉 flush／commit `IntegrityError` 並 rollback，以 DB 作最後一致性邊界。

### 驗證

- Tenant Delivery Factory Lab：`1 passed`；唯讀預檢、靜態範本阻擋、atomic create、重播、改規格衝突、密碼不落 manifest、過早 live 阻擋、完整 handoff gate 與 cleanup 全數通過，外部網路呼叫 `0`。
- 專用 API 回歸：`2 passed`；完整 PostgreSQL API suite：`317 passed, 3 skipped`。
- 0092 migration 已完成 `0091 → 0092 → 0091 → 0092` upgrade／downgrade round trip。
- Admin TypeScript、ESLint 與 production build（74 routes）通過；blocking Ruff、`git diff --check` 與統一 Security Gate 通過，dependency vulnerabilities、Bandit medium／high、未審核 secrets 均為 `0`。

### Gate 結論

- I10 內部產品化 Gate 與 code review 通過，可進入 I11。
- 本批證明 ForgeBase 可用一致、可追溯且 retry-safe 的方式產生租戶交付骨架；DNS、憑證、真實 CMS tenant、mailbox／ESP、外部資料授權與客戶內容驗收仍是對外資源或人工 Gate，不因建立 factory 而被虛構為已完成。

## I11：Privacy／Retention Operations

### 已實作

- 新增平台「隱私與資料保留」治理頁：集中顯示行為事件、瀏覽 session、網路觀察、未轉換窗口候選、旅程快照與 inbound reply 正文的到期佇列，並區分因既有商務紀錄而合法保留的技術證據。
- 新增 superuser-only 匿名訪客資料匯出：輸出 visitor、session、事件、公司候選、遮罩窗口候選、旅程、外聯狀態、對話與 RFQ；明確排除 raw IP、provider raw payload、ciphertext 與 token hash。完整 export 只回傳給操作者下載，不寫回資料庫。
- 新增匿名訪客 erasure：移除租戶範圍內 tracking events／sessions、可刪除公司與未轉換窗口衍生資料，將 Visitor 撤回 consent 並清零意圖、裝置與國家；RFQ、chat、converted contact 與必要寄送商務稽核依政策保留。
- 高權限清除與 retention run 使用 `Idempotency-Key`、request fingerprint 與 PostgreSQL advisory lock；同規格重試回放原始結果，改變請求內容則 409。
- 新增 PII-minimised `privacy_operations` ledger；只保存 tenant、subject HMAC、理由、分類筆數與處理摘要，不保存 raw visitor UUID、email 或 export payload。理由欄拒絕 email 及 raw subject ID。
- 每日 scheduler 改用同一套 retention transaction；以日期 key 保證跨 replica 每日只完成一次，並將自動執行結果寫入 ledger。
- Inbound reply 到期後清除可解密正文、附件 metadata 與 sender ciphertext，保留非 PII delivery／classification／handoff 鏈；所有 retention 類型在同一 runner 內處理。
- 新增 0093 migration、Privacy／Retention Lab、JSON／JUnit evidence 與 Release Contract gate；Admin 導覽新增治理入口。

### Code review 發現與修正

1. 初次整合測試發現 retention transaction 完成刪除後呼叫 audit helper 少傳 `tenant_id=None`，造成整個 request 500；補齊平台級 audit scope，並確認未 commit 的刪除會 rollback。
2. 舊 `purge_expired_company_evidence` 刪除 NetworkObservation 時會透過 FK cascade 刪掉 Company、JourneySnapshot 與已寄送 OutreachMessage；舊 contact／journey TTL 也有相同問題：三條 purge 路徑都加入 business-evidence protection，已轉換聯絡人或已有外聯訊息的鏈路不列入可刪除佇列。
3. 第一版為保護 converted contact 而整間公司全部保留，連同一公司的未轉換／DNC 候選也無法清除：改成公司證據保留、候選逐筆判斷；只有 converted 或被 OutreachMessage 引用的候選保留，其餘照常刪除並停止 pending automation job。
4. 到期 inventory 初稿仍把受保護紀錄算在「待刪除」，每次執行後會永遠顯示非零：改成 actionable 與 retained business evidence 分開計數，UI 明示兩者邊界。
5. 匯出 RFQ 若遇 legacy malformed JSON 會使整份 DSR export 500：改成安全解析；格式不合法時保留原字串供申請者取得，不因單筆歷史資料阻斷整份匯出。
6. 原每日 scheduler 直接執行 purge，沒有 durable operation evidence，也無法防止多 replica 同時執行：改成日期冪等 ledger 與 DB advisory lock。

### 驗證

- Privacy／Retention Lab：`27 passed`；跨租戶 subject 防護、export 不落庫、erasure replay、匿名追蹤刪除、商務證據保留、TTL、ledger 去識別化與零外部網路呼叫全部通過。
- I11 相關公司／窗口／外聯／平台整合回歸：`28 passed`；0093 migration 完成 `0092 → 0093 → 0092 → 0093` upgrade／downgrade round trip。
- Admin TypeScript、ESLint、production build（75 routes）通過；Security Gate dependency、SAST、secret candidate 均為 `0`。
- 完整 PostgreSQL API suite 首輪 `317 passed, 3 skipped, 1 failed`，失敗揭露同公司 converted candidate 的細粒度保留邊界；修正後完整回歸為 `318 passed, 3 skipped`。

### Gate 結論

- I11 內部產品化 Gate 與 code review 通過，可進入 I12。
- 本批提供的是產品內的資料生命週期與作業證據，不構成特定司法管轄區的法律意見；正式市場仍需由法務確認 legal basis、法定保存義務、DSR 身分核驗與供應商同步刪除契約。

## I12：SLO／Monitoring／Incident Console

### 已實作

- 新增 durable SLO snapshot 與事故生命週期：每次 scheduler 或平台手動取樣都量測核心背景工作、知識同步、外聯技術結果、真人接手 SLA、terminal failed jobs 與 stale claims；快照保留 90 天。
- 明確區分 `healthy`、`at_risk`（樣本不足）與 `breached`；SLO 僅涵蓋應用與資料庫內部證據，API 與 UI 都標記 `external_uptime_claimed: false`，不把內部取樣冒充站外可用率。
- 事故以固定 incident key 持久化，支援 open／acknowledged／resolved、自動復原、自動 reopen、發生次數、通知結果與 append-only decision events；移除原本僅存在單一 process memory 的告警去重。
- 告警 webhook／內部 email 套用 durable cooldown；成功與失敗嘗試都受冷卻控制，失敗原因留在事故控制台，避免每五分鐘產生通知風暴。
- 新增 superuser-only SLO／history／incident／action API；確認與結案必須填寫至少 10 字元依據，狀態變更與平台 audit 在同一 transaction 提交。
- 平台「系統健康」重構為事故控制台：同頁呈現即時 DB／queue、內部服務目標、錯誤預算、樣本數、待處理事故、處置說明、背景工作重試與對外測試 Gate。
- 新增 0094 migration 與完整事故狀態機驗收。

### Code review 發現與修正

1. 初版把 `at_risk` 樣本不足視為 scheduler unhealthy，會在低流量環境持續寫 error log：legacy `healthy` 契約改為只在實際 breached 時 false，UI 仍明確顯示證據不足。
2. 告警失敗原本不記 `last_notified_at`，provider outage 期間每次 scheduler 都會再送：成功與失敗嘗試都寫入 durable cooldown，錯誤則另外保留供操作者處理。
3. 初版重複 acknowledge／resolve 會新增無意義事件：狀態機改為 409 fail closed；事故若在人工結案後條件仍存在，下一次取樣會 reopen，並清除舊 acknowledged actor／timestamp。
4. 原告警使用 process-local signature 與 timestamp，多 replica／restart 後會失去去重狀態：改由資料庫事故列與 event ledger 作唯一真相來源。
5. SLO 計算沒有足夠樣本時不能聲稱達標：rate 指標要求至少 20 筆，未滿門檻列入 `insufficient_evidence` 而非綠燈；zero-tolerance operational 指標仍可即時評估。
6. UI 把內部健康、外部測試準備度與站外 uptime 混在同一概念：重新標示三者邊界，站外監控仍是正式外部環境 Gate，不由本批虛構完成。

### 驗證

- 事故狀態機驗收：`1 passed`；驗證 persistent open、單一 incident row、occurrence 累計、重複 action 409、人工 resolve 後自動 reopen、恢復後自動 resolve、history 與 event ledger。
- 完整 PostgreSQL API suite：`319 passed, 3 skipped`。
- 0094 migration 完成 `0093 → 0094 → 0093 → 0094` upgrade／downgrade round trip。
- Admin TypeScript、ESLint、production build（75 routes）通過；blocking Ruff 與 `git diff --check` 通過。

### Gate 結論

- I12 內部產品化 Gate 與 code review 通過，可進入 I13。
- 本批能證明內部 application／database 指標與事故決策鏈，不代表真實公網、DNS、CDN、第三方 LLM／ESP 的 uptime；正式站外 synthetic monitor、on-call routing 與告警到達演練仍需在可用外部資源的環境執行。

## I13：Release Package

### 已實作

- 建立版本化內部候選規格 `2026.08.27-internal.1`，明確標記 `internal-candidate`；未完成外部 Gate 仍逐項列入 manifest，不以封包存在宣稱已正式上線。
- 新增 fail-closed release builder：只允許乾淨 Git tree，從指定 commit 建立 source archive，計算 commit、單一 Alembic head、96 個 migration topology、六個應用 component、workflow／Dockerfile／lockfile／migration／deploy script 等關鍵檔案 SHA-256。
- 封包內含 `RELEASE_MANIFEST.json`、`CHECKSUMS.sha256`、deterministic `SOURCE.tar.gz`、blocking security summary 與經正規化的 Python CycloneDX SBOM；封包外另產 detached SHA-256。
- 新增獨立離線 verifier：檢查外層／內層 checksum、安全解壓路徑、manifest schema、版本、dirty 宣告、source archive digest、40-char commit、外部 Gate 邊界，以及每個關鍵檔案在 source archive 內的真實 bytes。
- 新增 tag／manual `Attested Release Package` workflow；完整 Release Gate 通過後，下載六個 production image CycloneDX SBOM，缺任一份即 fail closed，再由 GitHub `actions/attest@v4`／Sigstore 對完整候選包建立 build provenance。
- 新增 release readiness／驗證／部署／rollback 操作手冊；本機包明確標示 unsigned 且沒有 container SBOM，只能作內部驗證，不能冒充 CI attested release。

### Code review 發現與修正

1. 第一版 manifest 使用執行當下時間，同一 commit 兩次建立會產生不同 SHA：改用 commit timestamp，tar／gzip metadata 全部正規化為固定值。
2. Security Gate 每次產生的 CycloneDX SBOM 含隨機 UUID 與當下 timestamp，會破壞重現性：封包階段依 commit 產 deterministic serial number，並以 commit timestamp 正規化 metadata。
3. Windows `core.autocrlf` 使 `git archive` 輸出 CRLF、Linux 輸出 LF：source archive 強制 `core.autocrlf=false`，關鍵 digest 直接讀 Git object bytes，不再讀 checkout bytes。
4. 離線 verifier 初版只驗 source archive 整體 checksum，未證明 manifest 中的 critical hashes 真存在於來源包：加入逐檔 archive member 與 digest 比對，缺檔或內容不符即拒絕。
5. 第一版只嵌入 Python SBOM，無法代表六個 production image：正式 attested workflow 現在下載並強制六份 container CycloneDX SBOM；本機候選則明確標記 `ci_container_sboms_required: false`。
6. Release action 介面依 2026-08-27 GitHub 官方 Artifact Attestations 文件核對，使用 `id-token: write`、`attestations: write` 與 `actions/attest@v4`；provenance 是來源／建置鏈證據，不被描述成安全性保證。

### 驗證

- Release contract unit tests：`4 passed`；涵蓋版本、單一 migration head、外部 Gate、corrupt checksum 與 dirty-tree guard。
- 乾淨 tree 建立與離線 verifier 通過；本批最終測試包約 162.9 MB，manifest 為 `dirty: false`、Alembic head `0094_slo_incident_console`、revision count `96`。
- 同一 commit 連續建立兩份封包，byte size 與 SHA-256 完全相同；跨 Windows checkout 的 source critical digest 驗證通過。
- `--require-ci-evidence` 在缺少任一 production image SBOM 時確實拒絕建立；workflow YAML parse、blocking Ruff、compileall、`git diff --check` 通過。
- 統一 Security Gate：dependency vulnerabilities `0`、SAST medium／high `0`、unreviewed secret candidates `0`。

### Gate 結論

- I13 內部產品化 Gate 與 code review 通過，可進入 I14。
- 本機已建立的是可重現、可離線驗證的 unsigned internal candidate；只有遠端完整 Gate 成功後的 workflow artifact 才具有六個 container SBOM 與 Sigstore provenance。本批未 push tag、未建立遠端 release、未部署生產環境。

## I14：類別四最終退場報告與治理封板

### 已實作

- 對七個既有退場候選重新執行 route、feature、bundle path、worker、usage telemetry、notification preference 與 North Star dependency audit；自動 runner 產生不含 PII 的 JSON snapshot 與 SHA-256，並接入 API Release Contract。
- 最終分類：`copilot_floating_widget`、`legacy_ip_resolver` 已移除並再次證明 source path 無殘留；`agentos_runtime`、`ml_scoring_runtime`、`relation_recommender` 繼續 fail-closed 觀察；Telegram／LINE 仍為營運渠道，保留且持續量測。
- 本輪沒有新增刪除。production 30／60 天觀察尚未完成，零使用也沒有連續外部 telemetry 證據；依既定政策不得用本機或同日測試資料代替。
- 明確保護行為追蹤、規則式意圖評分、公司辨識、窗口補全、旅程個人化、受控外聯、回覆、真人接手、RFQ 工作台與閉環歸因；`ml_scoring_runtime` 只代表規則式核心之外的可選線上模型層。
- 新增 0095 retirement governance migration：保存 telemetry 核驗時間／操作者／證據參照、資料處置、rollback Git revision 與獨立 removal plan；資料處置有 DB check constraint，核驗者 FK 刪除後 fail closed。
- 退場核准 API 現在分為 technical readiness 與 governance completeness；觀察期、零使用、入口停用、零設定依賴、核驗證據、資料處置、rollback 與 removal plan 缺任一項皆拒絕。
- 平台退場頁顯示新增 blocker，只有 technical Gate 完成才可進入核准輸入；報告加入 deterministic SHA-256 並可下載 JSON snapshot。

### Code review 發現與修正

1. 舊文件要求 telemetry continuity、資料處置及可回復方案，但 API 實際只檢查天數、使用與入口狀態：0095 將三類治理證據正式納入 schema 與 409 Gate，消除文件／runtime 落差。
2. 若治理核驗者帳號日後刪除，`ON DELETE SET NULL` 會失去責任人；初版 completeness 未檢查 actor：改為 actor 也必須存在，否則已核准列立即回到 `removal_ready=false`。
3. 退場頁原本以 `removal_ready` 控制核准按鈕，但 governance 只能在核准 request 內提交，形成永遠無法輸入的循環：新增 `technical_removal_ready`，按鈕以 technical Gate 開啟，再於同一交易提交治理證據。
4. 原稽核沒有可攜、可比對的 snapshot identity：依 policy 與完整 candidates canonical JSON 計算 SHA-256，下載檔名包含指紋前綴。
5. ML runtime 觀察容易被誤讀為整個意圖評分可刪：static audit 新增核心保護規則，規則式 `intent_scoring` 與 `full_tracking` 不得出現在退場 seed。
6. 大量猜測式刪除仍有破壞既有租戶、歷史資料與北極星的風險：最終 runner 明確輸出 `new_removals_authorized: []` 與 `external_observation_claimed_complete: false`，未通過證據不得改成綠燈。
7. 最終 `alembic check` 揭露 I8 已建立的六個 capacity／partial indexes 未宣告在 ORM metadata，會讓未來 autogenerate 誤建「刪除效能索引」migration：把 public product listing、asset gallery、Operational／Knowledge ready 與 stale claim indexes 補回 model metadata，`alembic check` 回到零 drift。

### 驗證

- Category-four static audit：`17/17 passed`；2 項 removed path、3 項 disabled boundary、2 個 active channel 與 10 項 North Star core protection 全數通過。
- Retirement API 專用回歸：`5 passed`；涵蓋過早核准、治理資料缺漏、完整核准、核驗者失聯後 fail closed 與 PII-minimal usage contract。
- 完整 PostgreSQL API suite：`320 passed, 3 skipped`；scripts contract：`5 passed`。
- 0095 migration 完成 `0094 → 0095 → 0094 → 0095` upgrade／downgrade round trip。
- Alembic 單一 head `0095_retirement_governance_gate`；`alembic check` 回報 `No new upgrade operations detected`。
- Admin TypeScript、ESLint、production build（75 routes）通過；blocking Ruff、workflow YAML parse 與 `git diff --check` 通過。

### Gate 結論

- I14 內部產品化 Gate 與 code review 通過；14 批內部工程全部完成。
- 「批次完成」代表退場治理、已核准刪除與技術邊界均已處理到可稽核狀態，不代表等待 production 30／60 天的候選已被刪除。這三項 disabled 候選與兩個 active channel 的未來決策仍必須依真實 production evidence 另開獨立變更集。
