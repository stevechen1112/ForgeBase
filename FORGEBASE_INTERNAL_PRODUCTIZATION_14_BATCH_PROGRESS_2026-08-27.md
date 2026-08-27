# ForgeBase 內部產品化 14 批實作與 Code Review 紀錄

> 日期：2026-08-27  
> 北極星：匿名訪客 → 行為追蹤 → 意圖評分 → 推測公司 → 尋找公司相關聯絡窗口 → 依旅程產生個人化信件 → 寄送與追蹤 → 對方回覆 → 真人業務接手 → RFQ／成交  
> 執行原則：每一批須依序完成實作、測試、code review、修正審查發現及回歸，才可進入下一批。內部產品化完成不代表外部資料授權、法遵、寄送信譽或市場成效 Gate 自動通過。

## 14 批狀態

| 批次 | 範圍 | 實作 | Code review | 狀態 |
|---|---|---|---|---|
| I1 | 完整 North Star E2E Lab | 完成 | 通過 | 完成 |
| I2 | Browser／RBAC 自動化 | 未開始 | 未開始 | 待辦 |
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
