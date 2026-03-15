# ForgeBase — 外銷製造商官網成長系統 完整開發任務計畫（Task Plan）

本文件將《完整開發計畫》的 Phase 規劃與《產品規格文件》的 10 份規格，拆解為可估時、可指派、有依賴關係的開發任務。

---

## 總覽

| Phase | Epic 數 | Task 數 | 核心目標 |
|-------|---------|---------|----------|
| 0 - 基礎建設 | 1 | 7 | 專案骨架、CI/CD、開發環境 |
| 1a - 頁面與內容 | 6 | 38 | 網站能上線、內容能生成、頁面能被搜尋 |
| 1b - 事件與轉換 | 5 | 30 | 追蹤行為、辨識意圖、收詢盤、做再行銷 |
| 2 - 成長營運 | 5 | 22 | 擴展 audience、nurture、多語、進階 SEO |
| 3 - 智慧層 | 3 | 10 | AI 決策、預測、自動化 |
| **合計** | **20** | **107** | |

---

## Phase 0：專案基礎建設

> 目標：建立專案骨架、開發環境與部署管道，讓後續所有開發有統一基礎。

### Epic 0.1：專案初始化與基礎設施

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 0.1.1 | 專案 repo 建立與結構定義 | monorepo 結構：`/api`（後端）、`/web`（前端）、`/admin`（管理後台）、`/shared`（共用型別與工具） | — | repo + README |
| 0.1.2 | 技術棧確認與範本建立 | 後端框架、前端框架、ORM、資料庫選型確認。建立各子專案的初始範本。 | 0.1.1 | 技術棧文件 + boilerplate |
| 0.1.3 | 資料庫 schema 初始化 | 依規格 12.2 建立所有 content entity 的資料表。含 migration 機制。 | 0.1.2 | DB schema + migration scripts |
| 0.1.4 | API 架構與 route 骨架 | RESTful API 基礎架構、認證機制（JWT）、錯誤處理、請求驗證中介層。 | 0.1.2 | API 骨架 + auth middleware |
| 0.1.5 | Admin 後台 UI 骨架 | 管理後台 layout、側邊欄導航、登入頁、角色權限基礎。 | 0.1.2 | Admin UI shell |
| 0.1.6 | 前台 rendering 骨架 | SSR/SSG 渲染框架、頁面路由、基礎 layout（header/footer/breadcrumb）。 | 0.1.2 | Web 前台 shell |
| 0.1.7 | CI/CD 與部署管道 | 自動化測試、build、staging 部署、production 部署流程。 | 0.1.1 | CI/CD pipeline |

**Phase 0 交付標準**：
- [ ] 所有成員可 clone、build、run local dev
- [ ] DB migration 可執行
- [ ] API 可回應 health check
- [ ] Admin 可登入看到空後台
- [ ] 前台可渲染空白首頁
- [ ] Push 到 main 可自動部署到 staging

---

## Phase 1a：頁面與內容底座

> 目標：先讓網站能上線、內容能生成、頁面能被搜尋。
> 對應規格：12.1、12.2、12.3、12.4、12.9、12.10

### Epic 1a.1：結構化內容模組（Structured Content Module）

**對應規格**：12.2 內容模型 + 12.10 Entity 關聯

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1a.1.1 | Product CRUD API | Product 的建立、讀取、更新、刪除 API。含規格鍵值對的 JSON 欄位處理。 | 0.1.3 | API endpoints |
| 1a.1.2 | ProductCategory CRUD API | 分類管理，支援兩層巢狀（parent_id）。含 sort_order。 | 0.1.3 | API endpoints |
| 1a.1.3 | Application CRUD API | 應用場景管理。含產業標籤（tags）。 | 0.1.3 | API endpoints |
| 1a.1.4 | FAQItem CRUD API | FAQ 問答管理。含主題分群。 | 0.1.3 | API endpoints |
| 1a.1.5 | ComparisonTopic CRUD API | 比較主題管理。含比較面向 JSON。至少 2 個被比較產品。 | 0.1.3 | API endpoints |
| 1a.1.6 | Certification & Capability CRUD API | 認證與能力管理。含適用市場標籤。 | 0.1.3 | API endpoints |
| 1a.1.7 | CTA CRUD API | CTA 元件管理。含 action_type 與目標連結/表單/文件指向。 | 0.1.3 | API endpoints |
| 1a.1.8 | ContentAsset 上傳與管理 API | 文件/圖片上傳、自動壓縮、自動重新命名（entity-slug-序號）、alt text 自動生成。 | 0.1.3 | API + file storage |
| 1a.1.9 | Entity 關聯管理 API | 所有多對多關聯的建立/刪除 API。支援批次關聯。含替代料號雙向自動建立。 | 1a.1.1 ~ 1a.1.6 | API endpoints |
| 1a.1.10 | 孤立 Entity 檢測 API | 找出沒有任何關聯的 Product / Application。供後台顯示警告。 | 1a.1.9 | API endpoint |

**Epic 交付標準**：
- [ ] 所有 11 個 entity 可在後台 CRUD
- [ ] Entity 之間的關聯可建立與查詢
- [ ] 替代料號雙向自動建立
- [ ] 圖片上傳後自動壓縮與重命名
- [ ] 孤立 entity 可被偵測

---

### Epic 1a.2：內容管理後台 UI

**對應規格**：12.2 + 12.10

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1a.2.1 | Product 管理介面 | 產品列表、建立/編輯表單、規格鍵值對編輯器、圖片上傳、關聯設定面板。 | 1a.1.1, 0.1.5 | Admin UI |
| 1a.2.2 | ProductCategory 管理介面 | 分類樹狀結構、拖拽排序、建立/編輯表單。 | 1a.1.2 | Admin UI |
| 1a.2.3 | Application 管理介面 | 應用列表、建立/編輯表單、產業標籤選擇、關聯產品面板。 | 1a.1.3 | Admin UI |
| 1a.2.4 | FAQ / Comparison / Certification 管理介面 | 各 entity 的列表與編輯介面。FAQ 支援問答對編輯。Comparison 支援多產品比較面向表格。 | 1a.1.4 ~ 1a.1.6 | Admin UI |
| 1a.2.5 | CTA 管理介面 | CTA 列表、建立/編輯表單、預覽。 | 1a.1.7 | Admin UI |
| 1a.2.6 | Entity 關聯管理介面 | 從任一 entity 查看所有關聯。批次關聯彈窗。關聯統計。孤立 entity 警告。 | 1a.1.9, 1a.1.10 | Admin UI |
| 1a.2.7 | ContentAsset 媒體庫 | 文件/圖片列表、上傳、搜尋、篩選（依 entity）、alt text 編輯。 | 1a.1.8 | Admin UI |

**Epic 交付標準**：
- [ ] 非技術人員可在後台建立完整產品資料
- [ ] 可批次設定 entity 關聯
- [ ] 媒體庫可上傳與管理所有文件

---

### Epic 1a.3：內容定義模組（Content Definition Module）

**對應規格**：12.3 內容任務定義

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1a.3.1 | 內容策略地圖資料模型與 API | 支援定義：目標市場、客群、意圖分層、產品優先序、頁面規劃矩陣。提供 API 查詢規劃進度。 | 0.1.3 | API + schema |
| 1a.3.2 | 內容策略地圖管理介面 | 矩陣式介面：頁型 × 產品/應用 → 狀態（未規劃/已建 brief/已上線）。可從此處直接建立 PageBrief。 | 1a.3.1, 0.1.5 | Admin UI |
| 1a.3.3 | PageBrief CRUD API | PageBrief 建立/讀取/更新/刪除。含必填驗證（7 項必填條件）。 | 0.1.3 | API endpoints |
| 1a.3.4 | PageBrief 生命週期引擎 | 狀態機：Draft → Approved → In Progress → Completed → Published / Revision。含狀態轉換規則與權限控制。 | 1a.3.3 | 狀態機邏輯 |
| 1a.3.5 | PageBrief 管理介面 | Brief 列表（依狀態篩選）、建立/編輯表單、狀態轉換按鈕、審核功能。 | 1a.3.3, 1a.3.4 | Admin UI |
| 1a.3.6 | PageBrief 與 Entity 關聯 | Brief 可指定 related_entity（Product/Application 等），自動帶入該 entity 的資料作為 brief 上下文。 | 1a.3.3, 1a.1.9 | API 邏輯 |

**Epic 交付標準**：
- [ ] 可建立內容策略地圖，看到全局規劃狀態
- [ ] 可建立 PageBrief 並走完審核流程
- [ ] Brief 狀態為 Approved 時才允許觸發 AI 生成

---

### Epic 1a.4：AI 內容輔助模組（AI Content Assist Module）

**對應規格**：12.4 AI 生成規格

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1a.4.1 | AI 生成引擎核心 | 依頁型模板組裝 prompt，呼叫 LLM API，解析結構化輸出（JSON）。支援重試與錯誤處理。 | 0.1.2 | AI 引擎模組 |
| 1a.4.2 | 產品詳頁 AI 生成 | 輸入：PageBrief + Product 資料 + 關聯 entity。輸出：seo_title、description、full_description、FAQ 建議、CTA 文案。 | 1a.4.1, 1a.3.3 | 生成模板 |
| 1a.4.3 | 應用頁 AI 生成 | 輸入：PageBrief + Application 資料 + 適用產品規格。輸出：seo_title、description、problem_statement、full_description、FAQ 建議。 | 1a.4.1, 1a.3.3 | 生成模板 |
| 1a.4.4 | FAQ / 比較頁 AI 生成 | FAQ：依產品/應用資料生成 Q&A。比較：依多產品規格生成比較分析與建議。 | 1a.4.1 | 生成模板 |
| 1a.4.5 | 分類 / 認證頁 AI 生成 | 部分支援：生成分類描述、認證說明文案。 | 1a.4.1 | 生成模板 |
| 1a.4.6 | AI 生成結果預覽與編修介面 | 生成結果逐欄位顯示。支援：接受 / 逐欄修改 / 重新生成 / 手動覆寫。每欄標記 ai_generated / human_reviewed / human_written。 | 1a.4.1 ~ 1a.4.5, 0.1.5 | Admin UI |
| 1a.4.7 | AI 生成追溯紀錄 | 記錄每次生成的：時間、model 版本、輸入 Brief/Entity IDs、完整輸出、觸發者、後續修改紀錄。 | 1a.4.1 | DB + API |

**Epic 交付標準**：
- [ ] 4 種頁型可由 AI 生成初稿
- [ ] 生成結果可逐欄位審核與修改
- [ ] 每段內容有 ai_generated / human_reviewed / human_written 狀態
- [ ] 所有生成紀錄可追溯

---

### Epic 1a.5：前台頁面渲染與 SEO 基礎設施（Experience Module）

**對應規格**：12.1 頁型 + 12.9 SEO 與 IA

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1a.5.1 | 首頁模板與渲染 | 依規格 12.1.1 實作首頁固定區塊。含 Hero、產品分類、應用場景、認證、公司簡介。 | 0.1.6, 1a.1.1 ~ 1a.1.6 | 前台首頁 |
| 1a.5.2 | 產品分類頁模板與渲染 | 依規格 12.1.2。分類標題、產品列表卡片、相關應用、分類 FAQ。URL：`/products/{category-slug}/` | 0.1.6, 1a.1.2 | 前台頁面 |
| 1a.5.3 | 產品詳頁模板與渲染 | 依規格 12.1.3。產品標題、圖片集、規格表、說明、應用、認證、相關產品、FAQ、下載。URL：`/products/{category-slug}/{product-slug}/` | 0.1.6, 1a.1.1 | 前台頁面 |
| 1a.5.4 | 應用頁模板與渲染 | 依規格 12.1.4。應用標題、說明、適用產品、產業標籤、證據、FAQ。URL：`/applications/{application-slug}/` | 0.1.6, 1a.1.3 | 前台頁面 |
| 1a.5.5 | FAQ / 比較 / 規格頁模板與渲染 | 依規格 12.1.5。三個子頁型各自實作。 | 0.1.6, 1a.1.4, 1a.1.5 | 前台頁面 |
| 1a.5.6 | 認證 / 能力頁模板與渲染 | 依規格 12.1.6。 | 0.1.6, 1a.1.6 | 前台頁面 |
| 1a.5.7 | Contact / About 頁模板與渲染 | 依規格 12.1.8。含一般聯絡表單（前端 UI，邏輯在 1b）。 | 0.1.6 | 前台頁面 |
| 1a.5.8 | URL 路由引擎 | 依規格 12.9.1 自動生成 URL。由 taxonomy + entity slug 決定 URL 結構。最深 3 層。全部小寫、`-` 分隔。 | 0.1.6, 1a.1.1 ~ 1a.1.6 | 路由系統 |
| 1a.5.9 | Breadcrumb 自動生成 | 依 taxonomy 層級自動產出 breadcrumb。含 BreadcrumbList schema JSON-LD 輸出。 | 1a.5.8, 1a.1.2 | 前台元件 |
| 1a.5.10 | SEO metadata 系統 | 每頁自動輸出：title / description / og:title / og:description / og:image / canonical。支援手動覆寫。 | 1a.5.1 ~ 1a.5.7 | SEO 基礎 |
| 1a.5.11 | Structured Data 自動輸出 | 依規格 12.9.5。每種頁型自動輸出對應 JSON-LD schema（Product、FAQPage、Organization、TechArticle、BreadcrumbList 等）。 | 1a.5.1 ~ 1a.5.7, 1a.1.1 | Schema 輸出 |
| 1a.5.12 | 內連自動化引擎 | 依規格 12.9.3。根據 entity 關聯自動在頁面上建立內部連結區塊（相關產品、適用應用、相關 FAQ 等）。 | 1a.1.9, 1a.5.1 ~ 1a.5.7 | 內連系統 |
| 1a.5.13 | Sitemap 自動生成 | 依規格 12.9.7。6 個子 sitemap + 主索引。頁面發布/下架時自動更新。僅收錄 published 且非 noindex。 | 1a.5.8 | sitemap.xml |
| 1a.5.14 | Robots.txt 與 Noindex 控制 | 依規格 12.9.6。預設 index,follow。RFQ/搜尋結果/草稿/後台自動 noindex。robots.txt 靜態規則。 | 0.1.6 | robots.txt |
| 1a.5.15 | 圖片 SEO 處理 | 依規格 12.9.8。alt text 自動生成、檔名自動重命名、lazy loading、上傳壓縮。 | 1a.1.8 | 圖片處理管線 |

**Epic 交付標準**：
- [ ] 8 種頁型全部可渲染
- [ ] URL 結構正確且由系統自動生成
- [ ] 每頁有 breadcrumb + canonical + meta + schema
- [ ] 內連區塊依 entity 關聯自動出現
- [ ] sitemap 自動生成且僅含已發布頁
- [ ] robots.txt 正確阻擋非公開路徑

---

### Epic 1a.6：發布與頁面管理

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1a.6.1 | Page 資料模型與 API | Page entity CRUD。含 status（draft/published/archived）、與 entity 及 PageBrief 的關聯。 | 0.1.3 | API endpoints |
| 1a.6.2 | 發布/下架流程 | 發布：將 Page status 設為 published、設定 published_at、觸發 sitemap 更新。下架：status 改 archived、noindex。 | 1a.6.1, 1a.5.13 | 發布邏輯 |
| 1a.6.3 | 頁面管理介面 | 頁面列表（依頁型/狀態篩選）、發布/下架按鈕、頁面預覽連結、SEO 欄位編輯。 | 1a.6.1, 1a.6.2, 0.1.5 | Admin UI |
| 1a.6.4 | 內容預覽功能 | 未發布頁面的預覽 URL（含 token 驗證），讓 Marketing Manager 在發布前確認頁面呈現。 | 1a.6.1, 1a.5.1 ~ 1a.5.7 | 預覽系統 |

**Epic 交付標準**：
- [ ] 頁面可從後台發布上線
- [ ] 發布時 sitemap 自動更新
- [ ] 可在發布前預覽頁面
- [ ] 下架後頁面自動 noindex

---

### Phase 1a 整體交付檢查清單

- [ ] 後台可建立所有 content entity 並設定關聯
- [ ] 可建立內容策略地圖與 PageBrief
- [ ] AI 可依 Brief 生成 4 種頁型的初稿
- [ ] 8 種前台頁型可渲染
- [ ] URL/canonical/sitemap/robots/breadcrumb/structured data 全部自動運作
- [ ] 內連依 entity 關聯自動生成
- [ ] 頁面可發布上線並可預覽

---

## Phase 1b：事件、意圖與轉換閉環

> 目標：讓網站能追蹤訪客行為、辨識意圖、收取詢盤、啟動再行銷。
> 對應規格：12.5、12.6、12.7、12.8

### Epic 1b.1：事件追蹤模組（Tracking & Event Module）

**對應規格**：12.5 事件字典

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1b.1.1 | 前端事件 SDK 開發 | 輕量化 JS SDK，自動收集 page_view，提供 API 讓前台頁面觸發自訂事件。含 session_id、visitor_id（first-party cookie）自動管理。 | Phase 1a 完成 | JS SDK |
| 1b.1.2 | 事件接收 API | 後端事件接收端點。驗證事件格式、補充伺服器端屬性（GeoIP、device_type）、寫入事件表。 | 0.1.4 | API endpoint |
| 1b.1.3 | 事件資料表與儲存 | 事件 log 表設計（依規格 12.5.4 JSON 格式）。支援按月分區、24 個月保留。 | 0.1.3 | DB schema |
| 1b.1.4 | 前台埋點實作 | 在 Phase 1a 的所有頁型中埋入事件。依規格 12.5.1 所有 Phase 1a 事件（page_view、category_view、product_view、application_view）自動觸發。 | 1b.1.1, 1a.5.1 ~ 1a.5.7 | 前端埋點 |
| 1b.1.5 | Phase 1b 事件埋點 | 補充 Phase 1b 事件：faq_expand、comparison_view、spec_download、certification_view、cta_click、form_start、form_submit、rfq_start、rfq_submit。 | 1b.1.1 | 前端埋點 |
| 1b.1.6 | 後端計算型事件 | return_visit（24h+ 回訪偵測）與 session_depth_reached（閾值預設 5）的後端計算邏輯。 | 1b.1.2, 1b.1.3 | 後端邏輯 |
| 1b.1.7 | 事件查詢 API | 依 visitor、session、event_name、時間範圍、page_type 查詢事件。支援聚合統計。 | 1b.1.3 | API endpoints |

**Epic 交付標準**：
- [ ] 15 個事件全部可收集
- [ ] 事件資料格式符合規格
- [ ] 事件可依多維度查詢
- [ ] visitor_id 以 first-party cookie 管理

---

### Epic 1b.2：訪客身份與受眾模組（Identity & Audience Module）

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1b.2.1 | Visitor 資料模型與管理 | Visitor entity：visitor_id、first_seen、last_seen、total_visits、total_page_views、device 資訊、country。 | 0.1.3 | DB schema + API |
| 1b.2.2 | Session 資料模型與管理 | Session entity：session_id、visitor_id、start_time、end_time、page_count、entry_page、exit_page、traffic_source。 | 0.1.3 | DB schema + API |
| 1b.2.3 | Contact 資料模型與管理 | Contact entity：表單提交後建立。email 為去重鍵。含 full_name、company、phone、country、job_title。 | 0.1.3 | DB schema + API |
| 1b.2.4 | Visitor → Contact 身份合併 | 表單提交後將匿名 visitor 與 contact 關聯。同一 email 的多次提交合併到同一 contact。 | 1b.2.1, 1b.2.3 | 身份邏輯 |
| 1b.2.5 | Audience Tag 管理 | 可定義 audience tag（如：hydraulic-seal-interest、high-intent-visitor）。手動或規則自動打標。 | 1b.2.1 | API + Admin UI |
| 1b.2.6 | Remarketing Audience 建立 | 依規則自動建立再行銷受眾群組（如：看過產品頁 ≥ 3 次的訪客）。受眾定義可儲存。 | 1b.2.5, 1b.1.7 | 受眾邏輯 |

**Epic 交付標準**：
- [ ] 匿名訪客有獨立 visitor 記錄
- [ ] 表單提交後 visitor 與 contact 合併
- [ ] 可建立受眾標籤與規則
- [ ] 可建立再行銷受眾群組

---

### Epic 1b.3：意圖評分模組（Intent Scoring Module）

**對應規格**：12.6 意圖規則規格

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1b.3.1 | 評分規則引擎 | 依規格 12.6.1 實作 rule-based 評分。每個事件依規則加分。支援加權條件。 | 1b.1.2 | 評分引擎 |
| 1b.3.2 | 分數累積與即時更新 | 每個 visitor 維護累積 intent_score。事件觸發時即時更新分數。 | 1b.3.1, 1b.2.1 | 計分邏輯 |
| 1b.3.3 | 分數衰減排程 | 每日凌晨批次計算衰減（7 天 ×0.8 / 14 天 ×0.5 / 30 天 ×0.2 / 60 天歸零）。 | 1b.3.2 | 排程任務 |
| 1b.3.4 | Intent Stage 判定 | 依分數門檻判定 Cold/Warm/Hot/Sales-Ready。stage 變化時觸發對應動作。 | 1b.3.2 | 階段邏輯 |
| 1b.3.5 | Intent 觸發動作 | Warm → 加入再行銷受眾。Hot → sales alert。Sales-Ready → 高優先 alert + email。Hot→Warm 衰退 → nurture 受眾。 | 1b.3.4, 1b.2.6 | 觸發引擎 |
| 1b.3.6 | 評分規則管理介面 | Admin 可檢視/調整評分規則、衰減設定、stage 門檻（Phase 1 以設定檔管理，不需要複雜 UI）。 | 1b.3.1 | Admin UI |

**Epic 交付標準**：
- [ ] 訪客行為即時計分
- [ ] 分數每日自動衰減
- [ ] 4 個 intent stage 正確判定
- [ ] stage 變化自動觸發對應動作

---

### Epic 1b.4：轉換流程模組（Conversion Orchestration Module）

**對應規格**：12.7 表單與 RFQ 流程

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1b.4.1 | RFQ 表單前端實作 | 依規格 12.7.2 的 14 個欄位實作。含驗證、自動帶入（從產品/應用頁帶入 product/application）、localStorage 草稿。 | 1a.5.3, 1a.5.4 | 前端表單 |
| 1b.4.2 | RFQ 頁面完整實作 | 依規格 12.1.7。表單 + 信任元素 + 聯絡替代方式。noindex 設定。 | 1b.4.1, 1a.5.8 | RFQ 頁面 |
| 1b.4.3 | Contact 表單前端實作 | 依規格 12.7.3 的 6 個欄位實作。 | 1a.5.7 | 前端表單 |
| 1b.4.4 | 表單提交 API | 接收表單資料、驗證、建立 Contact（或合併）、建立 RFQRequest。寫入事件（form_submit / rfq_submit）。 | 1b.2.3, 1b.2.4, 1b.1.2 | API endpoints |
| 1b.4.5 | RFQRequest 資料模型與狀態機 | 依規格 12.7.4。狀態：new → assigned → in_progress → quoted → won / lost / expired。自動編號 RFQ-YYYYMMDD-NNN。 | 0.1.3 | DB + 狀態機 |
| 1b.4.6 | RFQ 路由分流引擎 | 依規格 12.7.5。依產品分類/國家/意圖分數自動分流指派業務。設定檔管理。 | 1b.4.5, 1b.3.2 | 分流邏輯 |
| 1b.4.7 | 通知引擎 | 依規格 12.7.6。新 RFQ email + 系統通知。高優先另行標記。24h 未處理提醒、48h 升級 Admin。 | 1b.4.5, 1b.4.6 | 通知系統 |
| 1b.4.8 | RFQ 管理介面 | RFQ 列表（依狀態/優先/指派人篩選）、詳情頁（含訪客事件時間軸、意圖分數、瀏覽過的產品）、狀態更新、指派。 | 1b.4.5 | Admin UI |
| 1b.4.9 | Sales User 視圖 | Sales 登入後看到：指派給自己的 RFQ、高意圖訪客提醒、待跟進列表。 | 1b.4.8, 1b.3.5 | Admin UI |

**Epic 交付標準**：
- [ ] RFQ 可從產品/應用頁一鍵帶入詢價
- [ ] RFQ 提交後自動分流指派
- [ ] 業務收到 email 通知
- [ ] 24h/48h 未處理有升級機制
- [ ] Sales 可在後台管理 RFQ 並看到訪客意圖資訊

---

### Epic 1b.5：基礎整合與 Dashboard

**對應規格**：12.8 整合規格

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 1b.5.1 | GA4 事件同步 | 依規格 12.8.1 映射 8 個事件到 GA4。透過 gtag 或 server-side Measurement Protocol。 | 1b.1.1 | GA4 整合 |
| 1b.5.2 | HubSpot Contact 同步 | 依規格 12.8.2。RFQ 提交時建立/更新 HubSpot Contact + Deal。intent_score 定期同步。 | 1b.4.4, 1b.2.3 | CRM 整合 |
| 1b.5.3 | Webhook 發送引擎 | 依規格 12.8.4。支援 5 種 webhook 事件。HMAC-SHA256 簽章。失敗重試 3 次。發送紀錄。 | 1b.4.5, 1b.3.4 | Webhook 引擎 |
| 1b.5.4 | Google Ads Audience 同步 | 依規格 12.8.3。透過 Customer Match 同步高意圖訪客受眾。每日批次。 | 1b.2.6 | Ads 整合 |
| 1b.5.5 | Meta Conversions API 同步 | 依規格 12.8.3。product_view → ViewContent、rfq_submit → Lead 等事件同步。 | 1b.1.2 | Meta 整合 |
| 1b.5.6 | 整合設定介面 | Admin 設定 GA4、HubSpot、Google Ads、Meta 的 API key / token。整合狀態監控（上次同步時間、成功/失敗）。 | 1b.5.1 ~ 1b.5.5 | Admin UI |
| 1b.5.7 | 內容成效 Dashboard | 哪些頁帶來流量、哪些頁有高意圖互動、哪些頁帶來 RFQ。依頁型、產品、應用維度。 | 1b.1.7, 1b.4.5 | Dashboard UI |
| 1b.5.8 | Intent Dashboard | 訪客 intent stage 分布、Top N 高意圖訪客、intent stage 轉換漏斗、特定訪客事件時間軸。 | 1b.3.4, 1b.1.7 | Dashboard UI |
| 1b.5.9 | Conversion Dashboard | RFQ 數量趨勢、表單轉換率、高意圖到 inquiry 轉換率、RFQ 狀態分佈、平均回應時間。 | 1b.4.5 | Dashboard UI |

**Epic 交付標準**：
- [ ] GA4 事件可同步
- [ ] RFQ 提交同步到 HubSpot
- [ ] 高意圖受眾可同步到 Google Ads
- [ ] 3 個 Dashboard 可查看核心指標
- [ ] 整合狀態可在後台監控

---

### Phase 1b 整體交付檢查清單

- [ ] 15 個事件全部可收集且正確觸發
- [ ] 訪客意圖即時評分，4 個 stage 可判定
- [ ] RFQ 可提交、分流、通知、追蹤
- [ ] 再行銷受眾可同步至 Google Ads 與 Meta
- [ ] GA4 與 HubSpot 整合可運作
- [ ] 3 個 Dashboard 提供可操作的 insight
- [ ] 從頁面到 inquiry 的完整閉環驗證通過

---

## Phase 2：Growth Operations

> 目標：擴展受眾、nurture、多語、進階 SEO、診斷能力。

### Epic 2.1：進階受眾與 Nurture

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 2.1.1 | 進階 Audience Segmentation | 多條件組合篩選（事件 + 屬性 + 意圖 + 標籤）。可儲存 segment 定義。 | Phase 1b | Segment 引擎 |
| 2.1.2 | 第三方公司識別接入 | 接入 Clearbit / 6sense 等 IP-to-company 服務。建立 Account entity 並關聯 Visitor。 | 1b.2.1 | Account 識別 |
| 2.1.3 | Account Enrichment | 公司規模、產業、地區等資料擴充。Account 層級的意圖彙總分數。 | 2.1.2 | Account 資料 |
| 2.1.4 | Email Nurture 引擎 | 設定 nurture sequence（觸發條件 → email 序列）。依 intent stage 和 persona 分流。 | 1b.3.5 | Nurture 引擎 |
| 2.1.5 | Download Gate 表單 | 下載規格書/白皮書前需留資。自動建立 Contact。 | 1b.4.4 | 前端表單 |
| 2.1.6 | LinkedIn Audience 同步 | 透過 LinkedIn Marketing API 同步公司名單與 email。 | 1b.2.6, 2.1.2 | LinkedIn 整合 |

---

### Epic 2.2：多語內容管理

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 2.2.1 | 多語資料架構 | 每個 content entity 支援多個 locale 版本。locale 為 entity 的必要欄位。 | Phase 1a | DB 擴展 |
| 2.2.2 | 多語內容管理介面 | 後台可切換語言版本編輯。可看到哪些語言版本已建/缺少。 | 2.2.1 | Admin UI |
| 2.2.3 | hreflang 自動輸出 | 多語頁面自動互指 hreflang。語言子目錄 `/zh/`、`/ja/` 等。 | 2.2.1, 1a.5.10 | SEO 輸出 |
| 2.2.4 | 多語 sitemap | 每個語言版本獨立子 sitemap。 | 2.2.1, 1a.5.13 | sitemap 擴展 |
| 2.2.5 | AI 多語生成 | AI Content Assist 支援以英文以外語言生成（先支援繁中、簡中、日文）。 | 2.2.1, 1a.4.1 | AI 擴展 |

---

### Epic 2.3：進階 SEO 與診斷

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 2.3.1 | Faceted Navigation Control | 分類頁篩選參數的 canonical / noindex 自動處理。避免重複索引。 | 1a.5.2 | SEO 邏輯 |
| 2.3.2 | PDF 與文件索引策略 | PDF 檔案的 meta 資訊注入。決定哪些 PDF 可被索引。 | 1a.1.8 | 索引策略 |
| 2.3.3 | 完整 Entity-level Schema | Product schema 含 isSimilarTo（替代料號）、additionalProperty（認證）等完整欄位。 | 1a.5.11 | Schema 擴展 |
| 2.3.4 | SEO 診斷儀表板 | 有效索引率、低 CTR 頁面、排名 6-20 潛力頁、keyword cannibalization、structured data 輸出率。接 Google Search Console API。 | Phase 1b | Dashboard |
| 2.3.5 | 內容優化建議 | 依 SEO 診斷結果自動產出優化建議（如：此頁 CTR 低建議修改 title）。 | 2.3.4 | 建議引擎 |

---

### Epic 2.4：進階 CRM 整合

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 2.4.1 | Salesforce 整合 | Contact + Opportunity 同步。 | 1b.5.2 | CRM 整合 |
| 2.4.2 | CRM 雙向同步 | CRM 的 deal status 回寫到系統。closed-won / closed-lost 對應 RFQ 狀態。 | 2.4.1 | 雙向同步 |
| 2.4.3 | Email Service Provider 整合 | 與 Mailchimp / SendGrid 等 ESP 整合，用於 nurture sequence 發送。 | 2.1.4 | ESP 整合 |

---

### Epic 2.5：進階內容回饋

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 2.5.1 | 頁面層級成效分析 | 每個頁面的流量、互動深度、轉換率、意圖分數貢獻。 | 1b.5.7 | 分析加強 |
| 2.5.2 | 產品/應用層級分析 | 哪些產品/應用帶來最多高意圖訪客與 RFQ。 | 2.5.1 | 分析加強 |
| 2.5.3 | 內容策略地圖成效視圖 | 在策略地圖上顯示每個已上線頁面的成效指標。標記表現差的頁面。 | 1a.3.2, 2.5.1 | 策略地圖加強 |
| 2.5.4 | A/B Test 基礎 | CTA 文案 / 頁面區塊的簡易 A/B test 機制。 | Phase 1b | A/B 引擎 |

---

## Phase 3：Intelligence Layer

> 目標：導入 AI 與模型化能力，提高自動化與決策品質。

### Epic 3.1：AI 決策輔助

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 3.1.1 | AI RFQ 分析 | 自動分析 RFQ 內容，判斷產品匹配度、建議報價範圍（需歷史資料）。 | Phase 2 | AI 分析 |
| 3.1.2 | AI RFQ 回覆草稿 | 依 RFQ 內容自動草擬回覆 email。業務可編修後發送。 | 3.1.1 | AI 生成 |
| 3.1.3 | 智慧內容優化建議 | AI 分析頁面內容與表現，建議修改方向（標題、關鍵字、結構調整）。 | 2.3.5 | AI 分析 |
| 3.1.4 | CTA / Workflow 推薦 | AI 依訪客行為推薦最佳 CTA 展示或 workflow 觸發。 | Phase 2 | AI 推薦 |

### Epic 3.2：預測型意圖

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 3.2.1 | ML Intent Scoring 模型 | 用歷史事件+轉換資料訓練意圖預測模型，輸出轉換機率。 | Phase 2 | ML 模型 |
| 3.2.2 | 預測分數融合 | ML 模型分數與 rule-based 分數加權融合。可設定信任比例。 | 3.2.1, 1b.3.1 | 融合邏輯 |
| 3.2.3 | Account-level Insight | 彙總 account 下所有 visitor 的行為、intent、RFQ 資料，產出 account 等級的洞察報告。 | 2.1.3 | 報告 |

### Epic 3.3：自動化擴展

| # | Task | 說明 | 依賴 | 產出 |
|---|------|------|------|------|
| 3.3.1 | 動態 CTA 引擎 | 依訪客 intent stage + 瀏覽歷史動態替換 CTA 內容。 | Phase 2 | 動態 CTA |
| 3.3.2 | 自動 Nurture 路徑優化 | AI 依 nurture 序列的開信率/點擊率自動調整發送節奏與順序。 | 2.1.4 | 自動優化 |
| 3.3.3 | 關聯推薦 AI | AI 建議可能的 entity 關聯（如：此產品可能適用此應用），供人工確認。 | 1a.1.9 | AI 推薦 |

---

## 任務依賴總圖

```
Phase 0
  └── 0.1 專案初始化
        ├── repo + boilerplate
        ├── DB schema
        ├── API 骨架
        ├── Admin 骨架
        ├── 前台骨架
        └── CI/CD

Phase 1a（依賴 Phase 0）
  ├── Epic 1a.1 結構化內容 CRUD ──────────────────────────┐
  ├── Epic 1a.2 內容管理後台 UI（依賴 1a.1）              │
  ├── Epic 1a.3 內容定義模組（依賴 1a.1 部分）            │
  ├── Epic 1a.4 AI 內容輔助（依賴 1a.3）                  ├── 前台渲染的資料來源
  ├── Epic 1a.5 前台頁面渲染 + SEO（依賴 1a.1）───────────┘
  └── Epic 1a.6 發布管理（依賴 1a.5）

Phase 1b（依賴 Phase 1a）
  ├── Epic 1b.1 事件追蹤（依賴 1a.5 的前台頁面）
  ├── Epic 1b.2 訪客身份與受眾（依賴 1b.1）
  ├── Epic 1b.3 意圖評分（依賴 1b.1 + 1b.2）
  ├── Epic 1b.4 轉換流程（依賴 1b.2 + 1b.3）
  └── Epic 1b.5 整合與 Dashboard（依賴 1b.1 ~ 1b.4）

Phase 2（依賴 Phase 1b）
  ├── Epic 2.1 進階受眾 + Nurture
  ├── Epic 2.2 多語管理
  ├── Epic 2.3 進階 SEO + 診斷
  ├── Epic 2.4 進階 CRM
  └── Epic 2.5 進階內容回饋

Phase 3（依賴 Phase 2）
  ├── Epic 3.1 AI 決策
  ├── Epic 3.2 預測意圖
  └── Epic 3.3 自動化
```

---

## 建議開發順序（Phase 1a 內部）

Phase 1a 內部的 Epic 並非全部序列，可以平行推進：

```
Week 1-2：
  ├── 1a.1 結構化內容 CRUD（後端）      ← 最優先，所有模組的資料基礎
  └── 0.1.6 前台骨架（前端可平行）

Week 3-4：
  ├── 1a.2 內容管理後台 UI（依賴 1a.1）
  ├── 1a.5.8 URL 路由引擎（前端可平行）
  └── 1a.3.1~1a.3.3 內容定義 PageBrief 基礎

Week 5-6：
  ├── 1a.5.1~1a.5.7 前台 8 種頁型渲染
  ├── 1a.3.4~1a.3.6 PageBrief 生命週期
  └── 1a.4.1 AI 生成引擎核心

Week 7-8：
  ├── 1a.5.9~1a.5.15 SEO 基礎設施（breadcrumb / schema / sitemap / robots / 圖片）
  ├── 1a.4.2~1a.4.5 各頁型 AI 生成
  └── 1a.4.6~1a.4.7 AI 編修介面 + 追溯

Week 9-10：
  ├── 1a.5.12 內連自動化引擎
  ├── 1a.6 發布管理
  └── 整合測試 + 修正

Week 11-12：
  └── Phase 1a 驗收 + 第一個客戶資料導入試跑
```

---

## 建議開發順序（Phase 1b 內部）

```
Week 1-2：
  ├── 1b.1.1~1b.1.3 前端 SDK + 事件 API + 事件表
  └── 1b.2.1~1b.2.3 Visitor / Session / Contact 模型

Week 3-4：
  ├── 1b.1.4~1b.1.6 全部事件埋點
  ├── 1b.2.4~1b.2.6 身份合併 + Audience
  └── 1b.4.1~1b.4.3 RFQ + Contact 表單

Week 5-6：
  ├── 1b.3 意圖評分全部（規則 + 衰減 + stage + 觸發）
  └── 1b.4.4~1b.4.7 RFQ 後端（提交 / 分流 / 通知）

Week 7-8：
  ├── 1b.4.8~1b.4.9 RFQ 管理 + Sales 視圖
  ├── 1b.5.1~1b.5.3 GA4 + HubSpot + Webhook
  └── 1b.5.4~1b.5.5 Ads Audience 同步

Week 9-10：
  ├── 1b.5.6 整合設定介面
  ├── 1b.5.7~1b.5.9 三個 Dashboard
  └── 整合測試 + 閉環驗證

Week 11-12：
  └── Phase 1b 驗收 + 第一個客戶完整閉環測試
```

---

## 驗收關鍵場景（End-to-End Scenarios）

### Scenario 1：內容建站閉環（Phase 1a）

```
Marketing Manager 登入後台
  → 建立內容策略地圖（定義 3 個優先產品 + 2 個應用場景）
  → 建立產品資料（含規格、圖片、分類、應用關聯）
  → 建立 PageBrief（選定頁型、意圖、關鍵字、CTA）
  → 審核 Brief
  → 點擊「AI 生成初稿」
  → 檢視 AI 產出，逐欄修改
  → 標記內容完成
  → 發布頁面
  → 前台可見：正確 URL、breadcrumb、schema、內連、sitemap 更新
```

### Scenario 2：詢盤閉環（Phase 1b）

```
訪客 Google 搜尋進入產品詳頁
  → 系統記錄 page_view + product_view 事件
  → 訪客瀏覽應用頁、下載規格書
  → intent score 累積到 Hot
  → 系統觸發 sales alert（但訪客尚未留資料）
  → 訪客加入 Google Ads 再行銷受眾
  → 3 天後訪客回訪，看比較頁
  → return_visit 事件，分數繼續累積
  → 訪客點擊 RFQ CTA，填寫表單
  → RFQ 提交：建立 Contact、合併 Visitor、建立 RFQRequest
  → 依產品分類 + 國家分流指派業務 A
  → 業務 A 收到 email（含高優先標記）
  → 業務 A 登入後台，看到 RFQ 詳情 + 訪客事件時間軸
  → 業務 A 更新 RFQ 狀態為 quoted
  → HubSpot 同步 Contact + Deal
```

### Scenario 3：分數衰減與 Nurture（Phase 1b + 2）

```
訪客 2 週前達到 Hot（score=45）
  → 14 天無活動 → 分數衰減至 45×0.5=22.5 → 降為 Warm
  → 系統觸發：從 Hot 衰退，加入 nurture 再行銷受眾
  → Phase 2：觸發 email nurture sequence
```

---

## 附錄：Task 統計

### Phase 0
| Epic | Tasks |
|------|-------|
| 0.1 專案初始化 | 7 |
| **小計** | **7** |

### Phase 1a
| Epic | Tasks |
|------|-------|
| 1a.1 結構化內容 CRUD | 10 |
| 1a.2 內容管理後台 UI | 7 |
| 1a.3 內容定義模組 | 6 |
| 1a.4 AI 內容輔助 | 7 |
| 1a.5 前台渲染 + SEO | 15 |
| 1a.6 發布管理 | 4 |
| **小計** | **49** |

### Phase 1b
| Epic | Tasks |
|------|-------|
| 1b.1 事件追蹤 | 7 |
| 1b.2 訪客身份與受眾 | 6 |
| 1b.3 意圖評分 | 6 |
| 1b.4 轉換流程 | 9 |
| 1b.5 整合與 Dashboard | 9 |
| **小計** | **37** |

### Phase 2
| Epic | Tasks |
|------|-------|
| 2.1 進階受眾 + Nurture | 6 |
| 2.2 多語管理 | 5 |
| 2.3 進階 SEO + 診斷 | 5 |
| 2.4 進階 CRM | 3 |
| 2.5 進階內容回饋 | 4 |
| **小計** | **23** |

### Phase 3
| Epic | Tasks |
|------|-------|
| 3.1 AI 決策 | 4 |
| 3.2 預測意圖 | 3 |
| 3.3 自動化 | 3 |
| **小計** | **10** |

### 總計：126 Tasks / 20 Epics / 5 Phases

---

## 開發進度追蹤

> 最後更新：2026-03-14 Session 3（Phase 1b 全部任務完成：事件埋點擴充 + 後端 computed events + Intent trigger + My RFQs + APScheduler + GA4 + HubSpot + Remarketing + 3 個 Dashboard，新增 ~15 routes，總計 ~149 routes）

### Phase 0：專案基礎建設 ✅ 全部完成

| Task | 狀態 | 說明 |
|------|------|------|
| 0.1.1 Monorepo 結構 | ✅ | `/api` `/web` `/admin` `/shared` |
| 0.1.2 技術棧 + Boilerplate | ✅ | Python/FastAPI + Next.js 15 + PostgreSQL |
| 0.1.3 DB Schema 初始化 | ✅ | 11 entity + 7 M2M 表，手動 Alembic migration |
| 0.1.4 API 骨架 + 全域錯誤處理 | ✅ | JWT 認證、middleware、validation handler |
| 0.1.5 Admin UI 骨架 | ✅ | Sidebar + RouteGuard + AuthProvider |
| 0.1.6 前台 Layout | ✅ | Header / Footer / Breadcrumb (schema.org) |
| 0.1.7 CI/CD Staging | ✅ | GitHub Actions → Linode (API+Admin) + Vercel (Web) |

---

### Phase 1a：頁面與內容底座 — 🔄 進行中（1a.5.15 待完成）

#### Epic 1a.1：結構化內容 CRUD API

| Task | 狀態 | 說明 |
|------|------|------|
| 1a.1.1 Product CRUD API | ✅ | `/content/products` CRUD |
| 1a.1.2 ProductCategory CRUD API | ✅ | `/content/categories` + tree endpoint |
| 1a.1.3 Application CRUD API | ✅ | `/content/applications` CRUD |
| 1a.1.4 FAQItem CRUD API | ✅ | `/content/faqs` CRUD |
| 1a.1.5 ComparisonTopic CRUD API | ✅ | `/content/comparisons` CRUD |
| 1a.1.6 Certification & Capability CRUD | ✅ | `/content/certifications` + `/content/capabilities` |
| 1a.1.7 CTA CRUD API | ✅ | `/content/ctas` CRUD |
| 1a.1.8 ContentAsset 上傳 API | ✅ | `api/app/api/v1/endpoints/assets.py`，R2 上傳、MIME 白名單、50MB 限制 |
| 1a.1.9 Entity 關聯管理 API | ✅ | `api/app/api/v1/endpoints/relations.py`，18 routes（product↔apps/certs/faqs/alternatives 雙向，application↔faqs/related-applications 雙向） |
| 1a.1.10 孤立 Entity 檢測 API | ✅ | `api/app/api/v1/endpoints/orphans.py`，4 routes（OrphanSummary + 3 孤立實體清單） |

**後端總計：113 routes 載入正確（+8 routes：alternative_parts/related_applications 各 3 endpoints + comparisons publish/unpublish 2 routes）**

---

#### Epic 1a.2：內容管理後台 UI

| Task | 狀態 | 說明 |
|------|------|------|
| 1a.2.1 Product 管理介面 | ✅ | list / new / edit 頁面 |
| 1a.2.2 ProductCategory 管理介面 | ✅ | list / new / edit 頁面 |
| 1a.2.3 Application 管理介面 | ✅ | list / new / edit 頁面 |
| 1a.2.4 FAQ / Comparison / Certification 管理介面 | ✅ | 各 list / new / edit |
| 1a.2.5 CTA 管理介面 | ✅ | list / new / edit 頁面 |
| 1a.2.6 Entity 關聯管理介面 | ✅ | `admin/.../relations/page.tsx`，OrphanSummary banner + RelationsPanel 元件（product↔apps/certs/faqs，application↔faqs） |
| 1a.2.7 ContentAsset 媒體庫 | ✅ | `admin/.../assets/page.tsx`，拖曳上傳 + 網格瀏覽 + alt text 編輯 modal，Sidebar 已加連結 |

**共用 UI 元件**：`DataTable`, `Pagination`, `StatusBadge`（支援 labelMap）  
**API Client**：`admin/src/lib/api/content.ts` — 9 個 typed API instances

---

#### Epic 1a.3：內容定義模組

| Task | 狀態 | 說明 |
|------|------|------|
| 1a.3.1 ContentStrategy 資料模型 + API | ✅ | `ContentStrategy` model + `/content/strategies` CRUD |
| 1a.3.2 內容策略地圖管理介面 | ✅ | `admin/.../strategies/`，Kanban 看板（5 個狀態欄）+ new/edit 頁面，側邊欄已加連結 |
| 1a.3.3 PageBrief CRUD API | ✅ | `/content/briefs` CRUD（已有） |
| 1a.3.4 PageBrief 生命週期引擎 | ✅ | `POST /briefs/{id}/transition`，狀態機：draft → approved → in_progress → completed → published / revision |
| 1a.3.5 PageBrief 管理介面 | ✅ | list / new / edit，含「觸發 AI 生成」按鈕 |
| 1a.3.6 PageBrief 與 Entity 關聯 | ✅ | `PageBrief` model 加入 `related_entity_type`/`related_entity_id` 欄位；`PageBriefCreate/Update/Read` schema 已更新；migration `0003_page_brief_entity_page_fields.py` 已建立 |

---

#### Epic 1a.4：AI 內容輔助模組

| Task | 狀態 | 說明 |
|------|------|------|
| 1a.4.1 AI 生成引擎核心 | ✅ | `api/app/services/ai_engine.py`，OpenAI JSON mode，4 種 page_type 模板，重試機制 |
| 1a.4.2 產品詳頁 AI 生成 | ✅ | prompt 模板 + `POST /content/generate` |
| 1a.4.3 應用頁 AI 生成 | ✅ | prompt 模板整合 |
| 1a.4.4 FAQ / 比較頁 AI 生成 | ✅ | prompt 模板整合 |
| 1a.4.5 分類 / 認證頁 AI 生成 | ✅ | `_build_category_prompt` + `_build_certification_prompt`，PAGE_TYPE_BUILDERS 擴充至 6 種 |
| 1a.4.6 AI 生成結果預覽與編修介面 | ✅ | `admin/.../briefs/[id]/preview/page.tsx`，顯示 brief 資訊、AI logs、觸發重生成按鈕 |
| 1a.4.7 AI 生成追溯紀錄 | ✅ | `AIGenerationLog` model + `GET /content/generate/logs/{brief_id}` |

---

#### Epic 1a.5：前台頁面渲染 + SEO 基礎 ✅ 核心完成

| Task | 狀態 | 說明 |
|------|------|------|
| 1a.5.1 首頁模板 | ✅ | `web/src/app/page.tsx`，Hero + 分類 + 應用 + 認證 + About 區塊 |
| 1a.5.2 產品分類頁模板 | ✅ | `web/src/app/products/[categorySlug]/page.tsx`，含 `generateMetadata` |
| 1a.5.3 產品詳頁模板 | ✅ | `web/src/app/products/[categorySlug]/[productSlug]/page.tsx`，含規格表、FAQ、JSON-LD |
| 1a.5.4 應用頁模板 | ✅ | `web/src/app/applications/[applicationSlug]/page.tsx`，Challenge/Solution + 相關產品 |
| 1a.5.5 FAQ / 比較 / 規格頁 | ✅ | `web/src/app/faq/page.tsx`（分 tag 群組）+ `faq/[tag]/page.tsx`（`generateStaticParams`）+ `comparisons/page.tsx` + `comparisons/[slug]/page.tsx`（比較表格/結論） |
| 1a.5.6 認證 / 能力頁 | ✅ | `web/src/app/certifications/page.tsx`，`CertificationBadge` 元件 |
| 1a.5.7 Contact / About 頁 | ✅ | `web/src/app/about/page.tsx` + `web/src/app/contact/page.tsx` |
| 1a.5.8 URL 路由引擎 | ✅ | Next.js App Router 動態路由：`/products/[cat]/[product]`、`/applications/[app]` |
| 1a.5.9 Breadcrumb 自動生成 | ✅ | 各頁 inline breadcrumb + `BreadcrumbList` JSON-LD（`buildBreadcrumbSchema`） |
| 1a.5.10 SEO metadata 系統 | ✅ | 每頁 `generateMetadata`，使用 `seo_title`/`seo_description`，含 canonical |
| 1a.5.11 Structured Data 輸出 | ✅ | `web/src/components/seo/StructuredData.tsx`，支援 Product / FAQ / BreadcrumbList / Organization |
| 1a.5.12 內連自動化引擎 | ✅ | `public_relations.py`（5 public GET routes，無須 auth）；產品詳頁加 Related Applications/Certifications 區塊 + 產品 FAQ；Application 頁改用真實 M2M 資料 + Application FAQs |
| 1a.5.13 Sitemap 自動生成 | ✅ | `web/src/app/sitemap.ts`，動態產出 products + applications + categories |
| 1a.5.14 Robots.txt + Noindex | ✅ | `web/src/app/robots.ts`，封鎖 `/dashboard/` + `/api/` |
| 1a.5.15 圖片 SEO 處理 | ⚠️ | 待開發（佔位符已實作，需整合 R2 CDN 圖片） |

**共用 UI 元件**：`ProductCard`, `ApplicationCard`, `CertificationBadge`, `FAQAccordion`, `StructuredData`  
**API Client**：`web/src/lib/api.ts` — ISR (60s revalidate)，16 個 Server Component fetch 函式（含 5 個 M2M public 函式）

---

#### Epic 1a.6：發布與頁面管理

| Task | 狀態 | 說明 |
|------|------|------|
| 1a.6.1 Page 資料模型 + API | ✅ | `Page` model + `/content/pages` CRUD；model 已加入 `entity_type`/`entity_id`/`brief_id`/`noindex` 欄位（spec 12.2.9）；migration 0003 已建立 |
| 1a.6.2 發布/下架流程 | ✅ | `publish.py`，14 routes（7 entities × publish+unpublish，新增 comparisons）；unpublish 時自動設 `noindex=True`；`PublishToggle.tsx` 已整合至 products/applications/faqs/certifications/comparisons 列表 |
| 1a.6.3 頁面管理介面 | ✅ | list / new / edit 頁面 |
| 1a.6.4 內容預覽功能 | ✅ | `preview.py`（POST token + GET 公開驗證）；`web/src/app/preview/[token]/page.tsx`（PREVIEW banner，no-store，robots noindex）；Admin pages edit 頁加「預覽頁面」按鈕 |

---

### 新增模型清單（本 session 建立）

| 模型 | 表格 | 說明 |
|------|------|------|
| `ContentStrategy` | `content_strategies` | 內容策略規劃矩陣 |
| `AIGenerationLog` | `ai_generation_logs` | AI 生成追溯紀錄 |

> ✅ Alembic migration 已手動建立：`0002_content_strategies_ai_logs.py`（down_revision = 0001_initial）

> ✅ Alembic migration 已手動建立：`0003_page_brief_entity_page_fields.py`（down_revision = 0002_content_strategies）
>   - `page_briefs`: 新增 `related_entity_type` (varchar 40), `related_entity_id` (uuid)
>   - `pages`: 新增 `entity_type` (varchar 40), `entity_id` (uuid), `brief_id` (uuid FK→page_briefs), `noindex` (bool default false)

---

### 下一步開發優先序（Phase 1c）

1. **Phase 2** — SEO 進階（多語系路由、動態 sitemap、canonical URL）
2. **Phase 3** — 報僷生成與 PDF 輸出系統
3. **Phase 2** — SEO 進階功能（多語系、sitemap 自動化、cannical 聯動）
4. **Phase 3** — 報價生成與 PDF 輸出系統

---

### Phase 1b：事件、意圖與轉換閉環 — ✅ 全部完成

> 最後更新：2026-03-14 Session 4

#### Epic 1b.1：事件追蹤模組

| Task | 狀態 | 說明 |
|------|------|------|
| 1b.1.1 前端事件 SDK | ✅ | `web/src/lib/analytics.ts`，visitor_id cookie + session_id + 15 個 helper fn + 離線 queue |
| 1b.1.2 事件接收 API | ✅ | `POST /api/v1/tracking/events`（single + batch），server-side ip/ua 補充 |
| 1b.1.3 事件資料表與儲存 | ✅ | `tracking_events`, `tracking_sessions`, `visitors` + migration `0004` |
| 1b.1.4 前台埋點實作 | ✅ | `PageViewTracker.tsx` 嵌入 product / category / application / comparison 頁 |
| 1b.1.5 Phase 1b 事件埋點 | ✅ | `FAQAccordion` trackFAQExpand + `CertificationBadge` trackSpecDownload + `ProductCTAButtons` trackCTAClick |
| 1b.1.6 後端計算型事件 | ✅ | `_upsert_visitor` 偵測 return_visit (24h gap)；`_upsert_session` 偵測 session_depth_reached (page ≥ 5) |
| 1b.1.7 事件查詢 API | ✅ | `GET /tracking/events`（filter + 聚合統計） |

---

#### Epic 1b.2：訪客身份與受眾模組

| Task | 狀態 | 說明 |
|------|------|------|
| 1b.2.1 Visitor 資料模型與管理 | ✅ | `Visitor` model + `GET/PUT /tracking/visitors` API |
| 1b.2.2 Session 資料模型與管理 | ✅ | `TrackingSession` model + `GET /tracking/sessions/{id}` |
| 1b.2.3 Contact 資料模型與管理 | ✅ | `Contact` model + `GET/PUT /tracking/contacts` + `POST /forms/contact` |
| 1b.2.4 Visitor → Contact 身份合併 | ✅ | 表單提交時以 email dedup + visitor_id FK 關聯 |
| 1b.2.5 Audience Tag 管理 | ✅ | `AudienceTag` + `VisitorTagLink` + `GET/POST /tracking/audiences` + visitor tag assign/remove |
| 1b.2.6 Remarketing Audience 建立 | ✅ | `GET /tracking/audiences/{id}/members`：manual tag + auto_rule（event_name / min_count / within_days） |

---

#### Epic 1b.3：意圖評分模組

| Task | 狀態 | 說明 |
|------|------|------|
| 1b.3.1 評分規則引擎 | ✅ | `api/app/services/intent_scoring.py`，15 個事件規則 + 加權條件 |
| 1b.3.2 分數累積與即時更新 | ✅ | 每次事件觸發時在 `_upsert_visitor()` 中即時更新 |
| 1b.3.3 分數衰減排程 | ✅ | `api/app/services/score_decay.py`，4 個衰減門檻，`run_daily_score_decay()` |
| 1b.3.4 Intent Stage 判定 | ✅ | `get_intent_stage()` + `should_alert()` in `intent_scoring.py` |
| 1b.3.5 Intent 觸發動作 | ✅ | `events.py` 中 `should_alert()` 觸發 `notify_visitor_hot()`，stage 升至 hot/sales_ready → 非同步發送 alert |
| 1b.3.6 評分規則管理介面 | ✅ | `admin/.../intent-rules/page.tsx`，靜態顯示計分規則、stage 門檻、衰減排程（設定檔管理）

---

#### Epic 1b.4：轉換流程模組

| Task | 狀態 | 說明 |
|------|------|------|
| 1b.4.1 RFQ 表單前端實作 | ✅ | `web/src/components/forms/RFQForm.tsx`，11 欄位 + localStorage 草稿 + URL 帶入 |
| 1b.4.2 RFQ 頁面完整實作 | ✅ | `web/src/app/rfq/page.tsx`，trust sidebar + 信任元素 + noindex |
| 1b.4.3 Contact 表單前端實作 | ✅ | `web/src/components/forms/ContactForm.tsx` + 更新 `contact/page.tsx` |
| 1b.4.4 表單提交 API | ✅ | `POST /forms/rfq`（`rfqs.py`）+ `POST /forms/contact`（`contacts.py`）|
| 1b.4.5 RFQRequest 資料模型與狀態機 | ✅ | `RFQRequest` + `RFQProductLink` model + `PUT /tracking/rfqs/{id}/status` |
| 1b.4.6 RFQ 路由分流引擎 | ✅ | `api/app/services/rfq_routing.py`，round-robin + score/country priority 規則 |
| 1b.4.7 通知引擎 | ✅ | `api/app/services/notifications.py`，SMTP，4 種觸發：new/assigned/reminder/escalation |
| 1b.4.8 RFQ 管理介面 | ✅ | `admin/.../rfqs/page.tsx` 列表 + `admin/.../rfqs/[id]/page.tsx` 詳情 + 狀態/指派更新 |
| 1b.4.9 Sales User 視圖 | ✅ | `admin/.../rfqs/my/page.tsx`，依 `assigned_to=current_user_id` 過濾的 My RFQ 頁面 + sidebar 連結 |

---

#### Epic 1b.5：基礎整合與 Dashboard

| Task | 狀態 | 說明 |
|------|------|------|
| 1b.5.1 GA4 事件同步 | ✅ | `analytics.ts` 中 `_fireGA4()` 並行觸發，`GA4_EVENT_MAP` 映射 8 個標準 GA4 事件名；`layout.tsx` 加入 `<Script>` GA4 gtag 注入（env: `NEXT_PUBLIC_GA_MEASUREMENT_ID`）|
| 1b.5.2 HubSpot Contact 同步 | ✅ | `api/app/services/hubspot.py`，`sync_contact_to_hubspot()` + `sync_rfq_to_hubspot()`；RFQ 提交後非同步觸發；`HUBSPOT_API_KEY` env var |
| 1b.5.3 Webhook 發送引擎 | ✅ | `api/app/services/webhook.py`，HMAC-SHA256、重試 3次（0s/60s/300s）、支援 5 種事件：rfq.created / rfq.status_changed / contact.created / contact.intent_stage_changed / visitor.became_hot |
| 1b.5.4 Google Ads Audience 同步 | ✅ | `api/app/services/google_ads.py`，Customer Match（SHA-256 email 雜湊），APScheduler 每日 03:00 UTC |
| 1b.5.5 Meta Conversions API 同步 | ✅ | `api/app/services/meta_conversions.py`，4 種事件：product_view / rfq_start / rfq_submit / spec_download；回傳 event_id 做去重 |
| 1b.5.6 整合設定介面 | ✅ | `api/app/api/v1/endpoints/integrations.py` GET /admin/integrations/status；admin/.../settings/integrations/page.tsx 顯示全部整合狀態 |
| 1b.5.7 內容成效 Dashboard | ✅ | `/dashboard/content-performance` |
| 1b.5.8 Intent Dashboard | ✅ | `/dashboard/intent` |
| 1b.5.9 Conversion Dashboard | ✅ | `/dashboard/conversions` |

---

### 新增模型清單（Phase 1b）

| 模型 | 表格 | 說明 |
|------|------|------|
| `Visitor` | `visitors` | 訪客主記錄（intent_score, intent_stage） |
| `TrackingSession` | `tracking_sessions` | 瀏覽 session（UTM, entry/exit page） |
| `TrackingEvent` | `tracking_events` | 事件 log（15 種事件名稱, properties JSON） |
| `Contact` | `contacts` | 表單提交後的已知聯絡人（email dedup）|
| `RFQRequest` | `rfq_requests` | 儀表板詢價單（狀態機, 自動編號） |
| `RFQProductLink` | `rfq_product_links` | RFQ ↔ Product M2M |
| `AudienceTag` | `audience_tags` | 受眾標籤定義 |
| `VisitorTagLink` | `visitor_tag_links` | Visitor ↔ AudienceTag M2M |

> ✅ Alembic migration 已手動建立：`0004_phase1b_tracking_identity.py`（down_revision = 0003_page_brief_entity_page_fields）

### 新增服務清單（Phase 1b）

| 服務 | 路徑 | 說明 |
|------|------|------|
| `intent_scoring.py` | `api/app/services/` | 計分規則引擎（15 事件規則 + stage 判定 + should_alert） |
| `score_decay.py` | `api/app/services/` | 每日衰減排程（APScheduler 每日 02:00 UTC 執行） |
| `rfq_routing.py` | `api/app/services/` | RFQ 分流指派（round-robin + score/country） |
| `notifications.py` | `api/app/services/` | SMTP 通知（new/assigned/reminder/escalation/visitor_hot） |
| `hubspot.py` | `api/app/services/` | HubSpot CRM 同步（sync_contact + sync_rfq → Deal + Association） |
| `webhook.py` | `api/app/services/` | Webhook 引擎（HMAC-SHA256、3 次重試、5 種事件） |
| `google_ads.py` | `api/app/services/` | Google Ads Customer Match（每日 03:00 UTC） |
| `meta_conversions.py` | `api/app/services/` | Meta CAPI server-side 事件（4 種事件映射） |

### 新增 API 端點（Phase 1b）

| 路由 | 檔案 | 說明 |
|------|------|------|
| `POST /api/v1/tracking/events` | `events.py` | 接收單一事件（public） |
| `POST /api/v1/tracking/events/batch` | `events.py` | 批次接收 ≤20 事件（public）|
| `GET /api/v1/tracking/events` | `events.py` | 查詢事件（admin） |
| `GET /api/v1/tracking/events/summary` | `events.py` | 事件聚合統計（admin） |
| `GET /api/v1/tracking/visitors` | `visitors.py` | 訪客列表（admin） |
| `GET /api/v1/tracking/visitors/{id}` | `visitors.py` | 訪客詳情（admin） |
| `GET /api/v1/tracking/visitors/{id}/events` | `visitors.py` | 訪客事件時間軸（admin）|
| `GET /api/v1/tracking/sessions/{id}` | `visitors.py` | Session 詳情（admin） |
| `GET /api/v1/tracking/audiences` | `visitors.py` | 受眾標籤列表（admin） |
| `POST /api/v1/tracking/audiences` | `visitors.py` | 建立受眾標籤（admin） |
| `GET /api/v1/tracking/audiences/{id}/members` | `visitors.py` | 受眾成員查詢（manual + auto_rule，admin） |
| `POST /api/v1/tracking/visitors/{id}/tags/{tag_id}` | `visitors.py` | 指派標籤（admin）|
| `DELETE /api/v1/tracking/visitors/{id}/tags/{tag_id}` | `visitors.py` | 移除標籤（admin） |
| `GET /api/v1/tracking/contacts` | `contacts.py` | 聯絡人列表（admin） |
| `GET /api/v1/tracking/contacts/{id}` | `contacts.py` | 聯絡人詳情（admin） |
| `PUT /api/v1/tracking/contacts/{id}` | `contacts.py` | 更新聯絡人（admin） |
| `POST /api/v1/forms/contact` | `contacts.py` | 提交聯絡表單（public） |
| `POST /api/v1/forms/rfq` | `rfqs.py` | 提交 RFQ（public） |
| `GET /api/v1/tracking/rfqs` | `rfqs.py` | RFQ 列表（admin） |
| `GET /api/v1/tracking/rfqs/{id}` | `rfqs.py` | RFQ 詳情（admin） |
| `PUT /api/v1/tracking/rfqs/{id}/status` | `rfqs.py` | 更新 RFQ 狀態（admin） |
| `PUT /api/v1/tracking/rfqs/{id}/assign` | `rfqs.py` | 指派 RFQ（admin） |

| `GET /api/v1/admin/integrations/status` | `integrations.py` | 整合狀態（env var 存否、pixel id 等，admin） |

**Phase 1b 新增 API 端點總計：23 routes**

---

### Phase 2：Growth Operations — ✅ 全部完成

> 最後更新：2026-03-16 Session 10（2.1.5 Download Gate + 2.3.1 Faceted Navigation + 2.3.3 Entity Schema + 2.5.1/2.5.2/2.5.3 Analytics 全部完成，Phase 2 封板）

#### Epic 2.1：進階受眾與 Nurture

| Task | 狀態 | 說明 |
|------|------|------|
| 2.1.1 進階 Audience Segmentation | ✅ | `Segment` model + `/tracking/segments` CRUD；多條件 AND 組合（event/field/intent/tag），`GET /segments/{id}/members` 即時計算符合人數 |
| 2.1.2 第三方公司識別接入 | ✅ | `api/app/services/clearbit_service.py`；`Account` model；migration `0008_phase2_ip_to_company`；`POST /tracking/accounts/lookup-ip` Clearbit Reveal API |
| 2.1.3 Account Enrichment | ✅ | `api/app/services/enrichment_service.py`；Clearbit Company API + OpenAI fallback；`POST /tracking/accounts/{id}/enrich`；Account intent_score 彙總 |
| 2.1.4 Email Nurture 引擎 | ✅ | `NurtureSequence / NurtureStep / NurtureEnrollment` models；migration `0009`；`/nurture/sequences` CRUD + `/nurture/enroll` + `/nurture/process`；`email_service.py` `send_nurture_step()`；Admin UI `/dashboard/nurture` |
| 2.1.5 Download Gate 表單 | ✅ | `POST /forms/download-gate`；`DownloadGateModal.tsx` 整合（company_name + requires_gate 邏輯）；admin assets 頁加 🔒/🔓 Gate toggle；migration `0013_phase2_download_gate`，`content_assets` 加 `requires_gate` 欄位 |
| 2.1.6 LinkedIn Audience 同步 | ✅ | `linkedin_service.py`（DMP Segments, SHA-256 email hash）；`LinkedInAudience` model；migration `0010`；`/tracking/linkedin-audiences` CRUD + `/{id}/sync`；Admin UI `/dashboard/linkedin` |

---

#### Epic 2.2：多語內容管理

| Task | 狀態 | 說明 |
|------|------|------|
| 2.2.1 多語資料架構 | ✅ | `locale` 欄位加入 Page/Product/Application 等；migration `0007_phase2_multilingual_schema` |
| 2.2.2 多語內容管理介面 | ✅ | 後台語言版本切換面板；locale 缺漏警示 |
| 2.2.3 hreflang 自動輸出 | ✅ | 多語頁面互指 `<link rel="alternate" hreflang="...">`；`/zh/`、`/ja/` 子目錄 |
| 2.2.4 多語 sitemap | ✅ | 各語言獨立子 sitemap + 主索引擴展 |
| 2.2.5 AI 多語生成 | ✅ | AI Content Assist 支援 `zh-TW`、`zh-CN`、`ja` 語言生成；locale 參數傳入 prompt |

---

#### Epic 2.3：進階 SEO 與診斷

| Task | 狀態 | 說明 |
|------|------|------|
| 2.3.1 Faceted Navigation Control | ✅ | 分類頁篩選參數自動加 `rel=canonical` 指回無參數 URL；URL 含 `?` 時自動輸出 `<meta name="robots" content="noindex">` 避免重複索引 |
| 2.3.2 PDF 與文件索引策略 | ✅ | migration `0005_phase2_pdf_indexing`；`ContentAsset` 加入 `indexable` 欄位；Admin 可設定 PDF 是否開放索引 |
| 2.3.3 完整 Entity-level Schema | ✅ | Product JSON-LD 擴充 `isSimilarTo`（替代料號交互關聯）、`additionalProperty`（認證/能力 as QuantitativeValue）；Schema 輸出整合進 `StructuredData.tsx` |
| 2.3.4 SEO 診斷儀表板 | ✅ | `gsc_service.py`（GSC API JWT OAuth2）；`/content/seo-audit/` 5 個端點（summary / pages / opportunities / cannibalization / on-page）；Admin UI `/dashboard/seo-audit`（4 Tab）|
| 2.3.5 內容優化建議 | ✅ | `seo_optimize.py`；`POST /content/seo-audit/optimize`；OpenAI JSON mode 產出 seo_title / meta_description / content_suggestions；AiSuggestionPanel 整合進 SEO 診斷 UI |

---

#### Epic 2.4：進階 CRM 整合

| Task | 狀態 | 說明 |
|------|------|------|
| 2.4.1 Salesforce 整合 | ✅ | `salesforce_service.py`（REST API v60, OAuth2 password flow, token 快取 + 401 自動刷新）；`CrmSyncLog` model；migration `0011`；`/tracking/crm/sf/*` 5 個端點 |
| 2.4.2 CRM 雙向同步 | ✅ | `POST /crm/sf/pull-opportunity`；SF stage → 本地 RFQ 狀態雙向映射；Admin UI `/dashboard/crm` |
| 2.4.3 Email Service Provider 整合 | ✅ | `esp_service.py`（Mailchimp Audience upsert + SendGrid 清單 + 交易信件）；`email_service.py` 多 provider 路由（`ESP_PROVIDER` 設定）；`/tracking/esp/*` 5 個端點；Admin UI `/dashboard/esp` |

---

#### Epic 2.5：進階內容回饋

| Task | 狀態 | 說明 |
|------|------|------|
| 2.5.1 頁面層級成效分析 | ✅ | `analytics.py` `GET /tracking/analytics/pages`；JOIN products/applications/pages 取名稱；回傳 page_views/unique_visitors/spec_downloads/rfq_count/avg_intent_score；Admin UI `/dashboard/page-analytics`（ScoreBar 元件） |
| 2.5.2 產品/應用層級分析 | ✅ | `GET /tracking/analytics/products`（model_number, category_slug）+ `GET /tracking/analytics/applications`（industry）；Admin UI `/dashboard/page-analytics`（產品頁/應用情境 Tab） |
| 2.5.3 內容策略地圖成效視圖 | ✅ | `GET /tracking/analytics/strategy-map`（CTE 查詢 + performance_tier 判定：strong/engaged/weak/dark）；strategies 看板加 showPerf toggle、左側邊框顏色 + tier badge + 📊 inline metrics |
| 2.5.4 A/B Test 基礎 | ✅ | `ABTest / ABTestView` models；migration `0012`；`/tracking/ab-tests/*` 9 個端點（CRUD + 穩定 hash 分流 + conversion 記錄 + recalc-stats）；Admin UI `/dashboard/ab-tests` |

---

### Phase 2 新增模型清單

| 模型 | 表格 | Migration | 說明 |
|------|------|-----------|------|
| `Segment` | `segments` | 0006 | 多條件受眾篩選定義 |
| `Account` | `accounts` | 0008 | IP-to-Company 公司記錄 |
| `NurtureSequence` | `nurture_sequences` | 0009 | Nurture 序列定義 |
| `NurtureStep` | `nurture_steps` | 0009 | 序列中的每一封 email |
| `NurtureEnrollment` | `nurture_enrollments` | 0009 | 聯絡人註冊紀錄 |
| `LinkedInAudience` | `linkedin_audiences` | 0010 | LinkedIn DMP Segment 同步記錄 |
| `CrmSyncLog` | `crm_sync_logs` | 0011 | CRM 同步操作 log |
| `ABTest` | `ab_tests` | 0012 | A/B 測試定義 + 快取統計 |
| `ABTestView` | `ab_test_views` | 0012 | 每次曝光 / 轉換事件 |

### Phase 2 新增服務清單

| 服務 | 路徑 | 說明 |
|------|------|------|
| `clearbit_service.py` | `api/app/services/` | Clearbit Reveal + Company API |
| `enrichment_service.py` | `api/app/services/` | Account Enrichment（Clearbit + OpenAI fallback） |
| `linkedin_service.py` | `api/app/services/` | LinkedIn DMP Segments（SHA-256 hash） |
| `gsc_service.py` | `api/app/services/` | Google Search Console API（JWT OAuth2） |
| `salesforce_service.py` | `api/app/services/` | Salesforce REST API v60（token cache + 401 refresh） |
| `esp_service.py` | `api/app/services/` | Mailchimp Audience + SendGrid Marketing + 交易信件 |

---

### Phase 2 待完成任務清單

> ✅ **Phase 2 全部 23 個 Task 已完成（Session 10 封板）**

所有任務皆已完成，Phase 2 正式進入 Phase 3。

### Phase 2 Session 10 新增 API 端點

| 路由 | 檔案 | 說明 |
|------|------|------|
| `POST /api/v1/forms/download-gate` | `contacts.py` | Download Gate 留資 + 回傳 download_url（public） |
| `GET /api/v1/tracking/analytics/pages` | `analytics.py` | 頁面層級成效聚合（admin） |
| `GET /api/v1/tracking/analytics/products` | `analytics.py` | 產品層級成效（admin） |
| `GET /api/v1/tracking/analytics/applications` | `analytics.py` | 應用層級成效（admin） |
| `GET /api/v1/tracking/analytics/strategy-map` | `analytics.py` | 策略地圖 + performance tier 疊加（admin） |

**Session 10 新增 API 端點總計：5 routes**

---

## Phase 3 開發記錄（Session 11）

> ✅ **Phase 3 全部 10 個 Task 已完成（Session 11 封板）**

### Phase 3 任務完成狀況

#### Epic 3.1：AI 決策輔助

| # | Task | 狀態 | 實作檔案 |
|---|------|------|----------|
| 3.1.1 | AI RFQ 分析 | ✅ | `api/app/services/ai_rfq.py` + `api/app/api/v1/endpoints/ai_intelligence.py` |
| 3.1.2 | AI RFQ 回覆草稿 | ✅ | `api/app/services/ai_rfq.py` + `ai_intelligence.py` |
| 3.1.3 | 智慧內容優化建議 | ✅ | `api/app/services/content_optimizer.py` + `ai_intelligence.py` |
| 3.1.4 | CTA / Workflow 推薦 | ✅ | `api/app/services/ai_recommend.py` + `ai_intelligence.py` |

#### Epic 3.2：預測型意圖

| # | Task | 狀態 | 實作檔案 |
|---|------|------|----------|
| 3.2.1 | ML Intent Scoring 模型 | ✅ | `api/app/services/ml_intent.py` + `api/app/api/v1/endpoints/ml_scoring.py` |
| 3.2.2 | 預測分數融合 | ✅ | `ml_intent.py::blend_scores()` + `ml_scoring.py` |
| 3.2.3 | Account-level Insight | ✅ | `ai_intelligence.py::account_insight_endpoint()` |

#### Epic 3.3：自動化擴展

| # | Task | 狀態 | 實作檔案 |
|---|------|------|----------|
| 3.3.1 | 動態 CTA 引擎 | ✅ | `api/app/services/dynamic_cta.py` + `ai_intelligence.py` |
| 3.3.2 | 自動 Nurture 路徑優化 | ✅ | `api/app/services/nurture_optimizer.py` + `ai_intelligence.py` |
| 3.3.3 | 關聯推薦 AI | ✅ | `api/app/services/relation_recommender.py` + `ai_intelligence.py` |

### Phase 3 Session 11 新增服務

| 服務 | 路徑 | 說明 |
|------|------|------|
| `ai_rfq.py` | `api/app/services/` | AI RFQ 分析 + 回覆草稿（OpenAI JSON mode） |
| `content_optimizer.py` | `api/app/services/` | 頁面內容優化建議（依流量表現 + AI） |
| `ai_recommend.py` | `api/app/services/` | CTA/Workflow 個人化推薦（OpenAI + rule fallback） |
| `ml_intent.py` | `api/app/services/` | RandomForestClassifier 意圖模型 + 分數融合 |
| `dynamic_cta.py` | `api/app/services/` | 動態 CTA 選擇（pure rule-based，依 intent stage） |
| `nurture_optimizer.py` | `api/app/services/` | Nurture 序列 AI 優化（步驟重排 + 改寫建議） |
| `relation_recommender.py` | `api/app/services/` | AI 關聯推薦（行為共現 SQL + OpenAI 驗證） |

### Phase 3 Session 11 新增 API 端點

| 路由 | 方法 | 說明 |
|------|------|------|
| `/api/v1/tracking/rfqs/{id}/analyze` | POST | AI RFQ 分析（3.1.1） |
| `/api/v1/tracking/rfqs/{id}/draft-reply` | POST | AI 回覆草稿（3.1.2） |
| `/api/v1/content/intelligence/optimize` | POST | AI 內容優化（3.1.3） |
| `/api/v1/tracking/visitors/{id}/recommend-cta` | GET | CTA 推薦（3.1.4） |
| `/api/v1/tracking/accounts/{id}/insight` | GET | Account-level 洞察（3.2.3） |
| `/api/v1/content/dynamic-cta` | GET | 動態 CTA（3.3.1，public） |
| `/api/v1/nurture/sequences/{id}/optimize` | POST | Nurture 路徑優化（3.3.2） |
| `/api/v1/content/products/{id}/recommend-relations` | GET | 產品關聯推薦（3.3.3） |
| `/api/v1/content/applications/{id}/recommend-relations` | GET | 應用場景關聯推薦（3.3.3） |
| `/api/v1/tracking/ml/train` | POST | ML 模型訓練（3.2.1，async） |
| `/api/v1/tracking/ml/status` | GET | 模型狀態查詢（3.2.1） |
| `/api/v1/tracking/ml/visitors/{id}/score` | GET | 單一訪客 ML 評分（3.2.2） |
| `/api/v1/tracking/ml/visitors/batch-score` | POST | 批次更新 ML 評分（3.2.2） |

**Session 11 新增 API 端點總計：13 routes**

### Phase 3 Session 11 DB 變更

| 遷移 | 說明 |
|------|------|
| `0014_phase3_ml_scoring` | visitors 表新增 `ml_intent_score`（Float nullable）和 `ml_score_updated_at`（timestamptz nullable） |

### Phase 3 Admin UI 新增

| 頁面 | 路由 | 說明 |
|------|------|------|
| AI 內容優化 | `/dashboard/content-optimizer` | 選擇實體 → AI 分析內容表現 + 改善建議 |
| ML 意圖評分 | `/dashboard/ml-scoring` | 模型管理、單一訪客評分、批次更新 |
| RFQ 詳情頁 AI 面板 | `/dashboard/rfqs/[id]` | AI 分析 + 草稿回覆整合面板 |

