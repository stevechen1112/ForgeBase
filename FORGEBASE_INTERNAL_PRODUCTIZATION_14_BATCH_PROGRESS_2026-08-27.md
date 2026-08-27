# ForgeBase 內部產品化 14 批實作與 Code Review 紀錄

> 日期：2026-08-27  
> 北極星：匿名訪客 → 行為追蹤 → 意圖評分 → 推測公司 → 尋找公司相關聯絡窗口 → 依旅程產生個人化信件 → 寄送與追蹤 → 對方回覆 → 真人業務接手 → RFQ／成交  
> 執行原則：每一批須依序完成實作、測試、code review、修正審查發現及回歸，才可進入下一批。內部產品化完成不代表外部資料授權、法遵、寄送信譽或市場成效 Gate 自動通過。

## 14 批狀態

| 批次 | 範圍 | 實作 | Code review | 狀態 |
|---|---|---|---|---|
| I1 | 完整 North Star E2E Lab | 完成 | 通過 | 完成 |
| I2 | Browser／RBAC 自動化 | 完成 | 通過 | 完成 |
| I3 | 完整 Release CI | 未開始 | 未開始 | 待辦 |
| I4 | Restore／Rollback 自動化 | 未開始 | 未開始 | 待辦 |
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
