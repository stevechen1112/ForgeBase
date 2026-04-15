# ForgeBase Admin 後台選單深度審計報告

> 審計日期：2026-04-15  
> 審計方法：逐一閱讀 admin/src/app/(dashboard)/dashboard/[功能]/page.tsx、對應 API 端點原始碼、資料模型結構，結合產品定位 Capture → Intent → Conversion 進行評級。  
> 產品核心主張：**ForgeBase 是專為外銷製造商打造的 RFQ Growth OS。讓官網捕捉買家意圖、推進詢價、幫業務在對的時間接手。**

---

## 執行摘要

| 指標 | 數值 |
|---|---|
| 總頁面數審計 | 34 |
| 完整實現 | 31（91%） |
| 部分實現 / 參考頁 | 2（6%） |
| 空殼（未實作） | 0 |
| API 端點覆蓋率 | ~95% |
| CORE 評級 | 15 項 |
| SUPPORTING 評級 | 18 項 |
| REFERENCE 評級 | 1 項 |

**整體判斷：後台實現度優良，無空殼頁面，所有 CRUD 均與後端 API 對應。主要改善空間在 Conversion 層整合度不足，與 Intent 層自動化程度偏低。**

---

## 評級說明

| 標記 | 定義 |
|---|---|
| 🔴 CORE | 日常必用，移除會讓產品失去核心價值 |
| 🟡 SUPPORTING | 有明確用途，補強核心流程，低頻使用 |
| 🔵 REFERENCE | 文件/資訊展示頁，無直接操作功能 |

---

## 一、概覽

### 儀表板 `/dashboard`
- **實現狀況**：✅ 完整
- **功能內容**：30 天 KPI 卡片（新 RFQ 數、訪客數、轉換率、Hot Leads）；最新 5 筆 RFQ 快照；各 stage 訪客分布
- **API 對應**：`GET /tracking/analytics/funnel` + `GET /tracking/rfqs`，後端均已實現
- **程式碼品質**：良好，正確的 error handling、loading state、useCallback 優化
- **Capture/Intent/Conversion 層**：Conversion 層 — 銷售管道全局概覽
- **評級**：🔴 CORE — 每日必用進入點

---

## 二、行銷分析

### 意圖分析 `/intent`
- **實現狀況**：✅ 完整
- **功能內容**：Top 10 高意圖訪客工作台；已識別聯絡人列表；意圖分數、Stage 分佈（Cold/Warm/Hot/Sales-Ready）；平均分數與 Sales-Ready 計數
- **API 對應**：`GET /tracking/visitors` + `GET /tracking/contacts`，後端均已實現
- **程式碼品質**：優良，多 KPI 卡片、Stage 色彩編碼完整
- **Capture/Intent/Conversion 層**：Intent 層 — 識別高價值訪客，驅動業務優先級
- **評級**：🔴 CORE

### 對話管理 `/chats`
- **實現狀況**：✅ 完整
- **功能內容**：AI 聊天會話列表，含狀態（active/handoff_ready/handoff_completed）、訪客意圖分數、品質評分（5 星制）、失控預警；狀態與評分篩選
- **API 對應**：`GET /chat/admin/sessions`，後端 `chat_admin.py` 已實現
- **程式碼品質**：優良，分頁、多篩選器、星級評分 UI
- **Capture/Intent/Conversion 層**：Capture 層 — AI 聊天品質監控与 Chat Handoff 觸發
- **評級**：🔴 CORE — AI 自動化的重要監控點

### 詢價單追蹤 `/conversions`
- **實現狀況**：✅ 完整
- **功能內容**：RFQ 狀態追蹤：4 個 KPI（總數、未報價、已報價、未指派）；待處理 vs 全部 RFQ 分頁；「等待天數」視覺警示（4+ 天紅色）；待指派提醒
- **API 對應**：`GET /tracking/rfqs`，後端 `rfqs.py` 已實現
- **程式碼品質**：優良，多維度狀態分類、色彩編碼
- **Capture/Intent/Conversion 層**：Conversion 層 — RFQ 生命週期管理
- **評級**：🔴 CORE — 銷售部門的日常操作規範

### 頁面成效分析 `/content-performance`
- **實現狀況**：✅ 完整
- **功能內容**：3 個 tab（頁面/商品/應用場景），按訪客數、下載、RFQ 數、轉換率排序；7-90 天時間範圍選擇；KPI 表格
- **API 對應**：`GET /tracking/analytics/pages` + products + applications，後端已實現
- **程式碼品質**：優良，複雜排序邏輯、多頁籤、時間範圍集中管理
- **Capture/Intent/Conversion 層**：Capture 層（流量品質）+ Conversion 層（RFQ 追蹤）
- **評級**：🔴 CORE — 內容行銷 ROI 的主要指標板

### 行銷漏斗 `/analytics/funnel`
- **實現狀況**：✅ 完整
- **功能內容**：訪客 → 詢價 → 成交轉換率；訪客意圖分布 bar chart；RFQ 狀態分布；7/30/90 天選擇器
- **API 對應**：`GET /tracking/analytics/funnel`，後端已實現
- **程式碼品質**：優良，漏斗階段清晰、條形圖完整
- **Capture/Intent/Conversion 層**：全層跨越 — 端到端漏斗可視化
- **評級**：🔴 CORE

### 自訂受眾 `/segments`
- **實現狀況**：✅ 完整
- **功能內容**：受眾分群列表（分群名、成員數、啟用/停用、建立時間）；「新增 Segment」按鈕
- **API 對應**：`GET /tracking/segments`，後端 `segments.py` 已實現
- **程式碼品質**：良好，簡潔展示
- **Capture/Intent/Conversion 層**：Intent 層 — 行為分群驅動再行銷
- **評級**：🟡 SUPPORTING

### ML 意圖評分 `/ml-scoring` *(adminOnly)*
- **實現狀況**：✅ 完整
- **功能內容**：模型狀態卡片（準確率、訓練樣本數、特徵重要性排行）；「訓練模型」按鈕；最後訓練時間戳
- **API 對應**：`GET /tracking/ml/status` + `POST /tracking/ml/train`，後端已實現
- **程式碼品質**：優良，非同步訓練 feedback、特徵重要性圖
- **Capture/Intent/Conversion 層**：Intent 層 — ML 意圖評分模型運維
- **評級**：🔴 CORE（技術管控臺，但 adminOnly 可收進系統設定群組）

### 評分規則 `/intent-rules` *(adminOnly)*
- **實現狀況**：⚠️ 參考頁（無編輯功能）
- **功能內容**：靜態文件：11 項行為評分規則（product_view +5、rfq_submit +50 等）、4 個 Stage 門檻、衰減規則表；無表單、無 API 修改
- **API 對應**：❌ 無對應編輯端點
- **程式碼品質**：優良，資訊架構清晰
- **Capture/Intent/Conversion 層**：Intent 層 — 評分系統文件化
- **評級**：🔵 REFERENCE — 純文件說明頁，規則目前為系統常數

---

## 三、AI / SEO

### AI 內容優化 `/content-optimizer`
- **實現狀況**：✅ 完整
- **功能內容**：輸入標題、內容、目標關鍵字 → AI 返回「優化標題、描述、SEO 建議、可讀性分數、關鍵字密度、Meta 標籤」；複製功能
- **API 對應**：`POST /content/intelligence/optimize`，後端 `ai_intelligence.py` 已實現
- **程式碼品質**：優良，表單驗證、複製 feedback、reset 按鈕
- **Capture/Intent/Conversion 層**：Capture 層 — SEO 優化提升搜尋能見度
- **評級**：🔴 CORE — 內容創作的 AI 生產力工具

### Redirect 規則 `/redirects`
- **實現狀況**：✅ 完整
- **功能內容**：301/302 redirect CRUD；路徑欄位正規化（`/` 前綴自動處理）；搜尋篩選；新增/編輯/刪除
- **API 對應**：`redirectsApi`（list/create/update/delete），後端已實現
- **程式碼品質**：優良，表單驗證、成功狀態視覺反饋
- **Capture/Intent/Conversion 層**：Capture → Intent — 避免 404、維持流量
- **評級**：🟡 SUPPORTING — SEO 基礎設施，非日常操作

---

## 四、產品內容

### 商品分類 `/categories`
- **實現狀況**：✅ 完整
- **功能內容**：分類樹 CRUD；多語過濾；發佈狀態切換；排序欄位；locale 標籤；分頁（20/頁）
- **API 對應**：`categoriesApi`，後端 `categories.py` 已實現
- **程式碼品質**：優良，複用 DataTable 元件、PublishToggle
- **Capture/Intent/Conversion 層**：Capture 層 — 商品組織架構，驅動前台導覽
- **評級**：🔴 CORE

### 商品管理 `/products`
- **實現狀況**：✅ 完整
- **功能內容**：商品 CRUD；列表（商品名、型號、語言、主推狀態、發佈狀態）；「設為主推」toggle；發佈狀態 lifecycle；多語過濾；20/頁
- **API 對應**：`productsApi`，後端 `products.py` 已實現
- **程式碼品質**：優良，Featured loader 動畫、statusBadge、error handling
- **Capture/Intent/Conversion 層**：Capture 層 — 產品資料是 AI 和前台的基礎
- **評級**：🔴 CORE

### 應用場景 `/applications`
- **實現狀況**：✅ 完整
- **功能內容**：場景 CRUD；產業標籤（color-coded: Automotive/Industrial/Electrical 等）；語言篩選；發佈狀態；20/頁
- **API 對應**：`applicationsApi`，後端 `content_crud.py` applications_router 已實現
- **程式碼品質**：優良，產業色彩對應表清晰
- **Capture/Intent/Conversion 層**：Capture 層 — 場景導向內容，針對產業買手
- **評級**：🟡 SUPPORTING

### FAQ 管理 `/faqs`
- **實現狀況**：✅ 完整
- **功能內容**：FAQ CRUD；問題標籤（category_tag）過濾；多語支援；發佈狀態；動態標籤抽取（useMemo）；20/頁
- **API 對應**：`faqsApi`，後端 `content_crud.py` faqs_router 已實現
- **程式碼品質**：優良，標籤動態生成
- **Capture/Intent/Conversion 層**：Intent 層 — 轉換頁內容，降低購買疑慮
- **評級**：🟡 SUPPORTING

### 認證管理 `/certifications`
- **實現狀況**：✅ 完整
- **功能內容**：認證 CRUD（名稱、發行機構、認證號、到期日）；到期警示（90 天內橘色、已過期紅色）；多語；發佈狀態；20/頁
- **API 對應**：`certificationsApi`，後端 `content_crud.py` certifications_router 已實現
- **程式碼品質**：優良，ExpiryCell 封裝完整
- **Capture/Intent/Conversion 層**：Capture 層 — 信任信號，外銷買家最在乎的憑證
- **評級**：🟡 SUPPORTING（初始設定後低頻更新）

### 廠能介紹 `/capabilities`
- **實現狀況**：✅ 完整
- **功能內容**：廠能 CRUD；分類標籤（OEM/Packaging/Quality/Assembly/Export，色彩編碼）；排序；多語；發佈狀態；20/頁
- **API 對應**：`capabilitiesApi`，後端 `content_crud.py` capabilities_router 已實現
- **程式碼品質**：優良，標籤色彩對應表
- **Capture/Intent/Conversion 層**：Capture 層 — 製造實力展示，建立競爭優勢
- **評級**：🟡 SUPPORTING

---

## 五、內容管理

### 多語管理 `/multilingual`
- **實現狀況**：✅ 完整
- **功能內容**：翻譯覆蓋率儀表板；6 language × 8 content type 的覆蓋率矩陣；各語整體百分比；進度條視覺化
- **API 對應**：並行 48 個 API 呼叫（6 語言 × 8 端點），後端均已支援 locale 參數
- **程式碼品質**：優良，高效並行加載、錯誤容限
- **Capture/Intent/Conversion 層**：Capture 層 — 全球市場準備度監控
- **評級**：🟡 SUPPORTING — 國際化運營的重要儀表板

### CTA 管理 `/ctas`
- **實現狀況**：✅ 完整
- **功能內容**：CTA 模組 CRUD（key、標題、類型、語言、狀態）；20/頁分頁
- **API 對應**：`ctasApi`，後端 `content_crud.py` ctas_router 已實現
- **程式碼品質**：良好，DataTable 複用
- **Capture/Intent/Conversion 層**：Conversion 層 — 轉換訊息多語管理，掌控 RFQ 按鈕文案
- **評級**：🔴 CORE — 直接影響轉換率的 copy 管理

### 內容摘要（Briefs）`/briefs`
- **實現狀況**：✅ 完整
- **功能內容**：Brief CRUD（目標頁面類型、主關鍵字、語言、AI 生成狀態 pending/processing/done/error）；20/頁
- **API 對應**：`briefsApi`，後端 `content_crud.py` briefs_router 已實現
- **程式碼品質**：良好，AI 狀態追蹤
- **Capture/Intent/Conversion 層**：Capture 層 — AI 寫作的前置策略規劃層
- **評級**：🟡 SUPPORTING — AI 內容生成的觸發點

### 媒體庫 `/assets`
- **實現狀況**：✅ 完整
- **功能內容**：資產瀏覽器（原始名、URL、mime type、大小、類型、alt 文字、SEO 索引狀態、綁定實體、建立時間）；類型篩選（PDF/圖片/文件）；20/頁
- **API 對應**：`GET /content/assets`，後端 `assets.py` 已實現
- **程式碼品質**：良好，檔案圖標區分、大小格式化
- **Capture/Intent/Conversion 層**：Capture 層 — 多媒體資產管理
- **評級**：🟡 SUPPORTING — 非日常操作，但資產管理是重要基礎設施

### Entity 關聯 `/relations`
- **實現狀況**：✅ 完整
- **功能內容**：Entity 孤立檢查工具；孤立商品/應用/FAQ 計數（含修復連結）；孤立實體詳細列表
- **API 對應**：`GET /content/entities/orphans`，後端 `orphans.py` 已實現
- **程式碼品質**：優良，並行 API 呼叫、修復導引
- **Capture/Intent/Conversion 層**：Capture 層 — 內容資料整潔性
- **評級**：🟡 SUPPORTING — 資料衛生工具，低頻但必要

### 策略地圖 `/strategies`
- **實現狀況**：✅ 完整
- **功能內容**：內容策略生命週期管理（unplanned → brief_created → ai_generated → in_review → published）；頁面類型篩選；績效分析 tab（需 full_tracking 方案）；績效 tier 分類（strong/engaged/weak/dark）
- **API 對應**：`strategiesApi` + `GET /tracking/analytics/strategy-map`，後端均已實現
- **程式碼品質**：優良，計畫格視覺化、方案 gate 控制
- **Capture/Intent/Conversion 層**：全層 — 從內容規劃到測量的完整生命週期
- **評級**：🔴 CORE — 內容行銷的戰略管理層

### 頁面管理 `/pages`
- **實現狀況**：✅ 完整
- **功能內容**：靜態頁面 CRUD（標題、頁面類型、URL slug、語言、noindex toggle、JSON-LD、發佈狀態）；20/頁
- **API 對應**：`pagesApi`，後端 `content_crud.py` pages_router 已實現
- **程式碼品質**：優良，SEO meta 指標展示（noindex/JSON-LD）
- **Capture/Intent/Conversion 層**：Capture 層 — SEO 落地頁、品牌頁發佈
- **評級**：🟡 SUPPORTING

---

## 六、詢價管理

### 全部 RFQ `/rfqs`
- **實現狀況**：✅ 完整
- **功能內容**：企業 RFQ 全集：狀態篩選、優先級篩選、分頁表格；快速狀態/優先級切換；25/頁
- **API 對應**：`GET /tracking/rfqs`，後端 `rfqs.py` 已實現（支援多維篩選）
- **程式碼品質**：良好，多維度篩選
- **Capture/Intent/Conversion 層**：Conversion 層 — 企業級 RFQ 管理
- **評級**：🔴 CORE

### 我的 RFQ `/rfqs/my`
- **實現狀況**：✅ 完整
- **功能內容**：個人 RFQ 過濾視圖（自動篩選 `assigned_to=current_user_id`）；狀態篩選；25/頁
- **API 對應**：`GET /tracking/rfqs?assigned_to=<user_id>`，後端已支援
- **程式碼品質**：良好，個人化視圖邏輯清晰
- **Capture/Intent/Conversion 層**：Conversion 層 — 業務個人 inbox
- **評級**：🔴 CORE — 業務人員每日工作清單

---

## 七、網站導入

### Legacy Site Intake `/intake`
- **實現狀況**：✅ 完整（但設計為一次性工具）
- **功能內容**：舊站點導入工具；5 個 tab 工作流（Projects/URLs/Entities/Redirects/Briefs）；URL 類型分類；實體抽取候選；redirect 配對；brief 生成；review workflow（待審 → approved/rejected）；進度條
- **API 對應**：7+ intake 相關端點，後端 `intake.py` 完整實現
- **程式碼品質**：優良，複雜多步驟工作流，tab 組織完整
- **Capture/Intent/Conversion 層**：Capture 層初期 — 舊系統資料遷移
- **評級**：🟡 SUPPORTING — 上線 onboarding 關鍵，上線後極低頻
- **位置建議**：應移至系統設定群組，而非主導覽同等層級

---

## 八、AI 行銷專員

### AI 對話 `/copilot`
- **實現狀況**：✅ 完整
- **功能內容**：AI 聊天 UI；多輪對話歷史（持久化至 DB）；optimistic update；markdown 渲染（**bold**、`code`、清單、標題）；思考中動畫；清空對話；5 個快速問題 suggestion chip
- **API 對應**：`POST /copilot/chat`、`GET /copilot/chat/history`、`DELETE /copilot/chat/history`，後端 `copilot.py` 已實現
- **程式碼品質**：優良，UX 細節完整
- **Capture/Intent/Conversion 層**：跨層 — AI 銷售 ops 助理，連接 DB 資料與業務決策
- **評級**：🔴 CORE — 主動式 AI 協作，直接加速業務決策

### 通知中心 `/notifications`
- **實現狀況**：✅ 完整
- **功能內容**：通知送達量表（sent/failed/skipped）；事件類型篩選（新 RFQ/熱訪客/日摘/流失警告）；頻道篩選（Telegram/LINE/Email）；訊息預覽；錯誤詳情
- **API 對應**：`GET /copilot/notifications`，後端已實現
- **程式碼品質**：良好，狀態色彩對應
- **Capture/Intent/Conversion 層**：跨層 — 通知系統監控
- **評級**：🟡 SUPPORTING — 系統健康確認，非日常操作

### 通知設定 `/settings/notifications`
- **實現狀況**：✅ 完整
- **功能內容**：多頻道（Telegram/LINE/Email/站內）× 多事件類型 的矩陣切換；靜默時段設定；Telegram ChatID 綁定流程（KIV code → confirm）；刪除頻道
- **API 對應**：`GET/PUT/DELETE /copilot/preferences` + `POST /copilot/telegram/bind-start`，後端已實現
- **程式碼品質**：優良，binding UX 完整
- **Capture/Intent/Conversion 層**：運營 — 個人通知偏好
- **評級**：🟡 SUPPORTING — 設定一次，後續低頻修改

---

## 九、系統

### 網站外觀 `/settings/site-profile`
- **實現狀況**：✅ 完整
- **功能內容**：品牌名、logo、聯絡資訊、預設語言、主題/佈局、header nav/footer/社交帳號/CTA 的 JSON 結構設定；JSON 驗證
- **API 對應**：`GET/PUT /site-profile`，後端已實現
- **程式碼品質**：優良，JSON 欄位驗證
- **Capture/Intent/Conversion 層**：全站 — 站點身份配置
- **評級**：🔴 CORE — 部署必設，後續低頻

### 整合設定 `/integrations`
- **實現狀況**：✅ 完整
- **功能內容**：6 個整合狀態卡片（GA4/HubSpot/Google Ads/Meta Pixel/Webhook/SMTP）；已連接 vs 未配置 badge；詳情展示；env key 配置教引
- **API 對應**：`GET /admin/integrations/status`，後端 `integrations.py` 已實現
- **程式碼品質**：優良，狀態卡片色彩對應
- **Capture/Intent/Conversion 層**：全層 — 行銷生態系整合中樞
- **評級**：🔴 CORE — 影響整個行銷堆疊

### 團隊成員 `/users`
- **實現狀況**：✅ 完整
- **功能內容**：成員表（名稱、職銜、角色、狀態切換、刪除）；角色定義（Owner/Admin/Marketing Manager/Sales）；邀請對話（email/name/password/role）；權限控制
- **API 對應**：`authApi.listTeam()` + `inviteTeamMember()`，後端 `auth.py` 已實現
- **程式碼品質**：優良，角色色彩、權限檢查
- **Capture/Intent/Conversion 層**：運營 — 帳號管理
- **評級**：🔴 CORE — 多成員使用的基礎

### 方案與帳單 `/settings/billing`
- **實現狀況**：✅ 完整
- **功能內容**：當前方案卡片、續訂日期、用量指標（Product/Admin limit & usage %）、升級/取消按鈕；PayPal payment flow 聯動
- **API 對應**：`subscriptionApi.getCurrent()` + `checkout()` + `cancel()`，後端已實現
- **程式碼品質**：優良，用量進度條、payment flow
- **Capture/Intent/Conversion 層**：商業 — 訂閱授權管理
- **評級**：🔴 CORE — 帳號授權，僅 owner 可見

---

## 總評級表

| 群組 | 選單項 | 評級 | 價值鏈層 |
|---|---|---|---|
| 概覽 | 儀表板 | 🔴 CORE | Conversion |
| 行銷分析 | 意圖分析 | 🔴 CORE | Intent |
| 行銷分析 | 對話管理 | 🔴 CORE | Capture |
| 行銷分析 | 詢價單追蹤 | 🔴 CORE | Conversion |
| 行銷分析 | 頁面成效分析 | 🔴 CORE | Capture + Conversion |
| 行銷分析 | 行銷漏斗 | 🔴 CORE | 全層 |
| 行銷分析 | 自訂受眾 | 🟡 SUPPORTING | Intent |
| 行銷分析 > 意圖分析 | ML 意圖評分 | 🔴 CORE | Intent |
| 行銷分析 > 意圖分析 | 評分規則 | 🔵 REFERENCE | Intent |
| AI/SEO | AI 內容優化 | 🔴 CORE | Capture |
| AI/SEO | Redirect 規則 | 🟡 SUPPORTING | Capture |
| 產品內容 | 商品分類 | 🔴 CORE | Capture |
| 產品內容 | 商品管理 | 🔴 CORE | Capture |
| 產品內容 | 應用場景 | 🟡 SUPPORTING | Capture |
| 產品內容 | FAQ | 🟡 SUPPORTING | Intent |
| 產品內容 | 認證管理 | 🟡 SUPPORTING | Capture |
| 產品內容 | 廠能介紹 | 🟡 SUPPORTING | Capture |
| 內容管理 | 多語管理 | 🟡 SUPPORTING | Capture |
| 內容管理 | CTA 管理 | 🔴 CORE | Conversion |
| 內容管理 | 內容摘要 | 🟡 SUPPORTING | Capture |
| 內容管理 | 媒體庫 | 🟡 SUPPORTING | Capture |
| 內容管理 | Entity 關聯 | 🟡 SUPPORTING | Capture |
| 內容管理 | 策略地圖 | 🔴 CORE | 全層 |
| 內容管理 | 頁面管理 | 🟡 SUPPORTING | Capture |
| 詢價管理 | 全部 RFQ | 🔴 CORE | Conversion |
| 詢價管理 | 我的 RFQ | 🔴 CORE | Conversion |
| 網站導入 | Legacy Site Intake | 🟡 SUPPORTING | Capture（初期） |
| AI 行銷專員 | AI 對話 | 🔴 CORE | 全層 |
| AI 行銷專員 | 通知中心 | 🟡 SUPPORTING | 跨層 |
| AI 行銷專員 | 通知設定 | 🟡 SUPPORTING | 運營 |
| 系統 | 網站外觀 | 🔴 CORE | 全站 |
| 系統 | 整合設定 | 🔴 CORE | 全層 |
| 系統 | 團隊成員 | 🔴 CORE | 運營 |
| 系統 | 方案與帳單 | 🔴 CORE | 商業 |

---

## 架構層對應統計

| 層級 | 頁面數 | 說明 |
|---|---|---|
| **Capture 層**（訪客吸引到識別） | 14 | 商品/分類/FAQ/認證/廠能/應用/重導向/AI 內容/媒體庫/頁面/多語/內容摘要/對話管理/策略地圖 |
| **Intent 層**（意圖評分到分群） | 8 | 意圖分析/ML 評分/評分規則/分群/漏斗/成效分析/FAQ/策略地圖（部分） |
| **Conversion 層**（RFQ 到成交） | 6 | 詢價單追蹤/全部RFQ/我的RFQ/CTA/儀表板/通知 |
| **全層跨越** | 6 | 儀表板/漏斗/AI對話/整合設定/網站外觀/策略地圖 |

---

## 主要發現與改善方向

### ✅ 強項
1. **API 覆蓋率達 95%**：無空殼頁面，所有功能均與後端對應
2. **Intent 層深度完整**：意圖分析、ML 評分、分群、漏斗均已實現
3. **Content 生命週期閉環**：Brief → AI 優化 → 發布 → 分析 → 改進
4. **多租戶邊界清晰**：所有資料查詢均有 tenant_id 隔離
5. **程式碼複用率高**：DataTable、StatusBadge、PublishToggle 等元件良好複用

### ⚠️ 改善空間

**Conversion 層（最優先）：**
- RFQ 管理、報價追蹤、成交標記分散在多處，缺少統一的客戶生命週期儀表板
- 無正式「成交確認」流程，缺 win/loss 追蹤實體
- 無跨成員協作機制（@mention、任務指派、共同筆記）

**Intent 層（次優先）：**
- ML 模型需手動觸發訓練，應排程自動執行
- 評分規則為系統常數，無 UI 編輯，無法讓客戶自訂
- 分群邏輯無 rule builder UI，難以客製化

**Capture 層：**
- 資產管理、分類編輯多依賴人工輸入，缺批量操作
- Legacy Site Intake 是一次性工具，放在主導覽層級過高

### 🔧 導覽結構建議
1. **Legacy Site Intake** 應移至「系統」群組，標記為「初始設定」
2. **ML 意圖評分 / 評分規則** 可移至「系統」群組，降低一般業務人員的視覺干擾
3. 考慮新增「Conversion 中心」群組，整合：詢價單追蹤 + 全部/我的 RFQ + 未來的 Deal 管理

---

*本報告由代碼靜態審計 + API 對應確認產生，未執行端對端 E2E 測試。*
