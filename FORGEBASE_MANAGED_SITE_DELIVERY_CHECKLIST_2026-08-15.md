# ForgeBase 代管式網站交付清單

- 適用模式：網站設計、版型、網域與部署由 ForgeBase 團隊負責；客戶只維護授權的結構化內容。
- 不包含：拖拉式建站、客戶自行改版、客戶自行綁網域、客戶自行發布整站。
- 執行原則：每一項必須留下負責人、日期與證據連結；未通過阻擋項目不得正式上線。

## A. 接案與範本確認

- [ ] 記錄客戶公司、產業、目標市場、語系與主要詢價類型。
- [ ] 客戶已從 Demo 中選定基礎範本。
- [ ] 書面確認需要修改的頁面、導覽、CTA、表單欄位與特殊功能。
- [ ] 明確標示由客戶提供並確認的公司、產能、認證、產品與圖片資料。
- [ ] 不使用未經確認的工廠、法人、認證或產能宣稱。

## B. 租戶與權限

- [ ] 建立唯一 Tenant slug。
- [ ] ForgeBase 團隊保留 Owner／Admin 管理帳號。
- [ ] 客戶內容帳號使用 `marketing_manager`，不交付平台超級管理權限。
- [ ] SiteProfile、SiteBuild、產品、素材、Chat、RFQ 與 Analytics 均綁定同一 Tenant。
- [ ] 以第二租戶帳號驗證跨租戶讀取、預覽、發布及寫入皆被拒絕。

## C. 網站製作與 CMS 串接

- [ ] 從選定範本建立 Connected Site，不直接修改靜態 Demo 為正式資料來源。
- [ ] Header、Footer、首頁結構、Theme 與 Layout 由 ForgeBase 團隊維護。
- [ ] 產品、分類、應用、能力、FAQ、證書與素材由 Tenant CMS 提供。
- [ ] 所有 CTA 使用 ForgeBase 支援的 intent，並能追蹤來源頁。
- [ ] Contact、RFQ、Chat 與 Analytics 寫入正確 Tenant。
- [ ] 各語系沒有其他品牌、其他租戶或 Demo 文案洩漏。

## D. 預覽與客戶核准

- [ ] 建立不冒充正式網站的 staging／preview 網址。
- [ ] 預覽 Token 只能由該 Tenant 管理員或平台超級管理員建立。
- [ ] 桌機與手機完成首頁、列表、詳情、Contact、RFQ、Chat 操作檢查。
- [ ] 圖片零破圖，連結零 404，表單錯誤訊息可理解。
- [ ] AI 回答以已發布內容為依據，未知資訊會拒答。
- [ ] 客戶以可追溯方式確認文案、產品、認證、圖片與聯絡資料。

## E. 正式網域與部署

- [ ] DNS 已指向核准的主機，正式 host 與 SiteProfile／SiteBuild 一致。
- [ ] 新租戶前台服務遵循 `web_<tenant>` 命名，納入 production Compose。
- [ ] Caddy 路由已加入且設定驗證通過。
- [ ] 真實客戶資料開始寫入前，啟用資料庫備份。
- [ ] 使用 `deploy/safe-deploy.sh`，確認所有 `web`／`web_*` 服務 healthy。
- [ ] 記錄 release image 與 rollback manifest。

## F. 上線驗收

- [ ] API `/health/ready` 回傳 ready。
- [ ] 每個租戶的 Web container 為 running／healthy。
- [ ] 正式網域 HTTPS、canonical、robots 與 sitemap 正確。
- [ ] 公開頁面、圖片、下載與多語路徑可用。
- [ ] 送出一筆明確標記的測試 Contact 與 RFQ，資料只出現在正確 Tenant。
- [ ] Chat 使用該網站語言回答，並能正確導向 RFQ。
- [ ] 未啟用的 ESP、CRM、AgentOS 或自動回信以 no-op／disabled 安全結束。
- [ ] 完成部署後瀏覽器 smoke test，保存驗收結果。

## G. 客戶交付

- [ ] 客戶只收到內容維護帳號與操作說明。
- [ ] 說明可自行維護與必須由 ForgeBase 團隊處理的範圍。
- [ ] 客戶知道版型、導覽、首頁結構、網域與整合變更需提出需求。
- [ ] 記錄支援窗口、回應方式與資料保存政策。

## H. 回復判定

發生以下任一狀況，停止交付並回復前一版本：

- 跨租戶資料可見或可寫。
- 正式網站無法載入、核心頁面大量 404 或圖片健康檢查失敗。
- Contact、RFQ 或 Chat 寫入錯誤 Tenant。
- 新版 API migration 與應用程式不相容。
- 未授權的自動回信或外聯被觸發。

應用程式使用 `deploy/rollback.sh <manifest>` 回復；資料庫回復必須先審查 migration 影響，不自動執行。

## I. 本次交付紀錄

| 欄位 | 紀錄 |
|---|---|
| Tenant |  |
| 範本 |  |
| Staging URL |  |
| Production URL |  |
| 客戶確認日期 |  |
| Release image／tag |  |
| Rollback manifest |  |
| 部署執行者 |  |
| 最終驗收日期 |  |
| 未完成但核准延後項目 |  |
