# ForgeBase — 外銷製造商官網成長系統 產品規格文件

本文件對應《完整開發計畫》Section 12，涵蓋 RD 開發前必須確認的 10 份規格。

---

## 12.1 頁型規格

### 通用規範

所有頁型共享以下基礎設施：

| 項目 | 規則 |
|------|------|
| URL 結構 | 由 taxonomy + entity slug 自動生成，不允許手動隨意建立 |
| canonical | 每頁自動產生，重複內容由系統判定 canonical 指向 |
| breadcrumb | 依 taxonomy 層級自動生成，輸出 BreadcrumbList schema |
| metadata | title / description / og:title / og:description / og:image 為必填 |
| hreflang | Phase 2，多語頁面自動互指 |
| sitemap | 自動收錄，依頁型分檔 |
| robots | 預設 index,follow，特定條件可設 noindex |

所有頁型的 CTA 分為兩類：

1. **Primary CTA**：頁面主要轉換目標（如 RFQ、索取報價）
2. **Secondary CTA**：輔助互動（如下載規格書、查看應用案例、訂閱）

---

### 12.1.1 首頁（Homepage）

**目的**：建立第一印象，引導訪客進入產品分類或應用場景。

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| Hero | 主標題 + 副標題 + Primary CTA | ✓ |
| 產品分類導覽 | 產品分類卡片，連結到分類頁 | ✓ |
| 應用場景摘要 | 2-4 個主要應用場景，連結到應用頁 | ✓ |
| 認證/能力展示 | 認證 logo 與能力亮點 | ✓ |
| 公司簡介 | 1-2 段公司定位說明 | ✓ |

**可配置欄位**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| hero_title | string(80) | 主標題 |
| hero_subtitle | string(160) | 副標題 |
| hero_cta_text | string(30) | CTA 按鈕文字 |
| hero_cta_link | url | CTA 目標連結 |
| hero_image | image | 主視覺圖片 |
| featured_categories | relation[] | 精選產品分類（2-6 個） |
| featured_applications | relation[] | 精選應用場景（2-4 個） |
| certifications_display | relation[] | 展示認證項目 |
| company_summary | richtext | 公司簡介 |

**CTA 位置**：

1. Hero 區塊：Primary CTA（索取報價 / 聯絡我們）
2. 產品分類區塊底部：Secondary CTA（查看所有產品）
3. 頁面底部：Primary CTA（立即詢價）

**SEO 欄位**：

| 欄位 | 規則 |
|------|------|
| title | `{公司名} - {核心產品關鍵字} Manufacturer` |
| description | 含公司定位、主要產品類型、認證亮點，150-160 字元 |
| og:image | hero_image |
| schema | Organization + WebSite |

**可追蹤事件**：

| 事件 | 觸發條件 |
|------|----------|
| page_view | 頁面載入 |
| cta_click | 點擊任何 CTA |
| category_view | 點擊產品分類卡片 |
| application_view | 點擊應用場景卡片 |

---

### 12.1.2 產品分類頁（Product Category Page）

**目的**：讓訪客在特定分類中找到目標產品，展示該分類的完整產品線。

**URL 結構**：`/products/{category-slug}/`

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 分類標題與說明 | 分類名稱 + 簡述 | ✓ |
| 產品列表 | 該分類下所有產品卡片 | ✓ |
| 篩選/排序 | 依規格屬性篩選（Phase 2 進階） | 選填 |
| 相關應用 | 此分類適用的應用場景 | ✓ |
| 分類 FAQ | 該分類常見問題 | 選填 |

**可配置欄位**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| category_name | string(60) | 分類名稱 |
| category_slug | string(60) | URL slug，系統自動生成 |
| category_description | richtext | 分類說明（含技術概述） |
| category_image | image | 分類代表圖 |
| parent_category | relation | 上層分類（支援兩層） |
| sort_order | integer | 顯示排序 |
| filter_attributes | attribute[] | 可篩選的規格屬性（Phase 2） |
| related_applications | relation[] | 相關應用，自動由 entity 關聯帶入 |
| related_faqs | relation[] | 相關 FAQ，自動由 entity 關聯帶入 |

**CTA 位置**：

1. 每張產品卡片：Secondary CTA（查看詳情）
2. 頁面側邊或底部：Primary CTA（詢問此分類產品）
3. 相關應用區塊：Secondary CTA（了解應用）

**SEO 欄位**：

| 欄位 | 規則 |
|------|------|
| title | `{category_name} - {公司名}` |
| description | 含分類名、產品數量、主要規格範圍，150-160 字元 |
| schema | BreadcrumbList + CollectionPage |
| canonical | 自動，篩選參數不改變 canonical |

**可追蹤事件**：

| 事件 | 觸發條件 |
|------|----------|
| page_view | 頁面載入 |
| category_view | 進入分類頁 |
| product_view | 點擊產品卡片 |
| cta_click | 點擊詢價 CTA |
| filter_use | 使用篩選（Phase 2） |

---

### 12.1.3 產品詳頁（Product Detail Page）

**目的**：展示單一產品的完整規格、應用、認證與相關資源，推進詢價行為。

**URL 結構**：`/products/{category-slug}/{product-slug}/`

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 產品標題與摘要 | 產品名 + 型號 + 一句話說明 | ✓ |
| 產品圖片 | 主圖 + 圖片集 | ✓ |
| 規格表 | 結構化規格數據 | ✓ |
| 產品說明 | 技術說明文案 | ✓ |
| 適用應用 | 此產品適用的應用場景 | ✓ |
| 認證 | 此產品具備的認證 | 選填 |
| 相關產品 | 同分類其他產品或替代料號 | ✓ |
| FAQ | 此產品常見問題 | 選填 |
| 下載資源 | 規格書 PDF、CAD 圖等 | 選填 |

**可配置欄位**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| product_name | string(100) | 產品名稱 |
| product_slug | string(100) | URL slug |
| model_number | string(50) | 型號 |
| short_description | string(200) | 一句話說明 |
| full_description | richtext | 產品技術說明 |
| images | image[] | 產品圖片集 |
| specifications | key_value[] | 規格鍵值對（名稱：值：單位） |
| category | relation | 所屬分類 |
| applications | relation[] | 適用應用 |
| certifications | relation[] | 具備認證 |
| related_products | relation[] | 相關產品（自動 + 手動） |
| alternative_parts | relation[] | 替代料號 |
| faqs | relation[] | 相關 FAQ |
| downloads | file[] | 可下載文件 |
| status | enum | draft / published / archived |

**CTA 位置**：

1. 規格表旁：Primary CTA（索取報價 / 詢問此產品）
2. 頁面底部：Primary CTA（立即詢價）
3. 下載資源旁：Secondary CTA（下載規格書）申請表單
4. 相關產品區塊：Secondary CTA（查看詳情 / 比較）

**SEO 欄位**：

| 欄位 | 規則 |
|------|------|
| title | `{product_name} {model_number} - {category_name} \| {公司名}` |
| description | 含產品名、型號、核心規格亮點、應用場景，150-160 字元 |
| schema | Product（含 name, description, image, brand, sku, manufacturer） + BreadcrumbList |
| canonical | 自動 |

**可追蹤事件**：

| 事件 | 觸發條件 |
|------|----------|
| page_view | 頁面載入 |
| product_view | 進入產品詳頁（帶 product_id） |
| spec_download | 點擊下載規格書 |
| cta_click | 點擊詢價 CTA |
| rfq_start | 開始填寫 RFQ |
| faq_expand | 展開 FAQ 項目 |
| image_view | 瀏覽產品圖片集 |

---

### 12.1.4 應用頁（Application Page）

**目的**：以買家的使用場景為入口，說明產品如何解決特定應用需求，建立搜尋可發現性。

**URL 結構**：`/applications/{application-slug}/`

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 應用標題與摘要 | 應用場景名 + 問題描述 | ✓ |
| 應用說明 | 場景描述 + 技術挑戰 + 解決方案 | ✓ |
| 適用產品 | 適用此場景的產品列表 | ✓ |
| 產業標籤 | 適用產業 | ✓ |
| 證據素材 | 案例數據、測試結果、客戶引述 | 選填 |
| 相關應用 | 其他相似或互補的應用場景 | 選填 |
| FAQ | 此應用常見問題 | 選填 |

**可配置欄位**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| application_name | string(80) | 應用名稱 |
| application_slug | string(80) | URL slug |
| problem_statement | string(200) | 問題描述 |
| full_description | richtext | 場景說明 + 技術說明 + 解決方案 |
| application_image | image | 應用場景圖 |
| industries | tag[] | 適用產業標籤 |
| applicable_products | relation[] | 適用產品，自動由 entity 關聯帶入 |
| evidence | richtext | 證據素材 |
| related_applications | relation[] | 相關應用 |
| faqs | relation[] | 相關 FAQ |

**CTA 位置**：

1. 適用產品區塊：Secondary CTA（查看產品規格）
2. 頁面底部：Primary CTA（諮詢此應用方案 / 索取報價）
3. 證據素材旁：Secondary CTA（下載應用說明）

**SEO 欄位**：

| 欄位 | 規則 |
|------|------|
| title | `{application_name} Solutions - {公司名}` |
| description | 含應用場景、解決的問題、適用產品類型，150-160 字元 |
| schema | BreadcrumbList + Article（type: TechArticle） |

**可追蹤事件**：

| 事件 | 觸發條件 |
|------|----------|
| page_view | 頁面載入 |
| application_view | 進入應用頁（帶 application_id） |
| product_view | 從應用頁點擊產品 |
| cta_click | 點擊詢價 CTA |
| faq_expand | 展開 FAQ 項目 |

---

### 12.1.5 FAQ / 比較 / 規格頁

此類頁面依用途分為三個子頁型，共享相同的 URL 層級。

#### 12.1.5a FAQ 頁

**目的**：回答特定產品或分類的常見技術問題，捕捉長尾搜尋需求。

**URL 結構**：`/faq/{faq-topic-slug}/` 或掛在產品/分類頁內

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| FAQ 主題標題 | 主題名稱 | ✓ |
| FAQ 問答列表 | 可展開式 Q&A | ✓ |
| 相關產品 | 此 FAQ 涉及的產品 | ✓ |
| 相關應用 | 此 FAQ 涉及的應用 | 選填 |

**可配置欄位**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| faq_topic | string(80) | FAQ 主題名稱 |
| faq_slug | string(80) | URL slug |
| faq_items | faq_item[] | 問答項目（question + answer） |
| related_products | relation[] | 相關產品 |
| related_applications | relation[] | 相關應用 |

**SEO**：FAQPage schema 自動輸出。

**事件**：`faq_expand`（展開特定問答，帶 faq_id）。

#### 12.1.5b 比較頁

**目的**：將兩個或多個產品 / 材料 / 規格做並列比較，捕捉比較型搜尋意圖。

**URL 結構**：`/compare/{comparison-slug}/`

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 比較標題 | 比較主題名稱 | ✓ |
| 比較表格 | 並列規格/特性比較表 | ✓ |
| 比較說明 | 差異解讀與選用建議 | ✓ |
| 相關產品 | 被比較的產品 | ✓ |

**可配置欄位**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| comparison_title | string(100) | 比較主題 |
| comparison_slug | string(100) | URL slug |
| compared_items | relation[] | 被比較的產品（2+） |
| comparison_dimensions | key_value[] | 比較面向（面向名：產品 A 值：產品 B 值） |
| analysis | richtext | 差異解讀 |
| recommendation | richtext | 選用建議 |

**SEO**：schema 無專用型態，使用 Article + BreadcrumbList。

**事件**：`comparison_view`（帶 comparison_id + compared_product_ids）。

#### 12.1.5c 規格總覽頁

**目的**：提供某類產品的完整規格對照表，供工程師快速比對。

**URL 結構**：`/specifications/{spec-topic-slug}/`

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 規格主題 | 主題名稱 | ✓ |
| 規格對照表 | 多產品多維規格表 | ✓ |
| 下載連結 | PDF 規格表下載 | 選填 |

**事件**：`spec_download`（帶 file_id + product_ids）。

---

### 12.1.6 認證 / 能力頁（Certification / Capability Page）

**目的**：展示公司的認證資格與製造能力，建立信任，捕捉「{認證} + manufacturer」搜尋需求。

**URL 結構**：`/certifications/{cert-slug}/` 或 `/capabilities/{capability-slug}/`

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 認證/能力標題 | 名稱 + 簡述 | ✓ |
| 詳細說明 | 認證範圍、取得時間、適用標準 | ✓ |
| 適用產品 | 此認證涵蓋的產品 | ✓ |
| 適用市場 | 此認證適用的國家/區域 | 選填 |
| 證書圖片 | 認證證書掃描或圖片 | 選填 |

**可配置欄位**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| cert_name | string(80) | 認證/能力名稱 |
| cert_slug | string(80) | URL slug |
| cert_type | enum | certification / capability |
| description | richtext | 詳細說明 |
| standard | string(100) | 適用標準編號 |
| valid_from | date | 取得日期 |
| valid_until | date | 有效期限（選填） |
| applicable_products | relation[] | 涵蓋產品 |
| applicable_markets | tag[] | 適用市場/國家 |
| cert_image | image | 證書圖片 |

**SEO**：BreadcrumbList。title 含認證名稱與標準編號。

**事件**：`certification_view`（帶 cert_id）。

---

### 12.1.7 RFQ / 詢價頁（RFQ Page）

**目的**：將高意圖訪客轉化為具名詢價，是 Conversion Layer 的核心頁面。

**URL 結構**：`/rfq/` 或 `/request-quote/`

**固定區塊**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 詢價表單 | 結構化 RFQ 表單 | ✓ |
| 信任元素 | 認證、回覆時間承諾、客戶數量 | ✓ |
| 聯絡替代方式 | 電話、email、即時通訊 | ✓ |

**表單欄位**：詳見 12.7 表單與 RFQ 流程規格。

**CTA**：Submit 按鈕為唯一 Primary CTA，文案可配置。

**SEO**：noindex（詢價頁不參與搜尋排名），但保留 title/description 供內部導航。

**事件**：

| 事件 | 觸發條件 |
|------|----------|
| page_view | 頁面載入 |
| rfq_start | 開始填寫（第一個欄位 focus） |
| form_start | 同 rfq_start |
| rfq_submit | 成功送出 |
| form_submit | 同 rfq_submit |

---

### 12.1.8 Contact / About 頁

**目的**：提供基本公司資訊與聯絡方式。

**URL 結構**：`/contact/` 與 `/about/`

**固定區塊（Contact）**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 聯絡表單 | 一般聯絡表單 | ✓ |
| 聯絡資訊 | 地址、電話、email | ✓ |
| 營業時間 | 服務時間與時區 | 選填 |

**固定區塊（About）**：

| 區塊 | 內容 | 必填 |
|------|------|------|
| 公司介紹 | 歷史、定位、願景 | ✓ |
| 數據亮點 | 年資、員工數、出口國家數 | 選填 |
| 認證摘要 | 主要認證列表 | 選填 |

**SEO**：About 頁使用 Organization schema。Contact 頁使用 ContactPage type。

**事件**：`form_start`、`form_submit`（聯絡表單互動）。

---

## 12.2 內容模型規格

### 12.2.1 Product

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | 系統生成 | 主鍵 |
| product_name | string(100) | ✓ | 不可空、不可重複 | 產品名稱 |
| slug | string(100) | auto | 由 product_name 自動生成，可手動覆寫 | URL slug |
| model_number | string(50) | ✓ | 不可重複 | 產品型號 |
| short_description | string(200) | ✓ | | 摘要說明 |
| full_description | richtext | ✓ | | 完整技術描述 |
| images | image[] | ✓ | 至少 1 張 | 產品圖片集 |
| specifications | json | | key-value 鍵值對陣列 | 結構化規格 |
| category_id | fk → ProductCategory | ✓ | 必須存在 | 所屬分類 |
| applications | m2m → Application | | | 適用應用 |
| certifications | m2m → Certification | | | 具備認證 |
| faqs | m2m → FAQItem | | | 相關 FAQ |
| comparison_topics | m2m → ComparisonTopic | | | 可比較主題 |
| alternative_parts | m2m → Product (self) | | | 替代料號 |
| downloads | file[] | | | 可下載文件 |
| seo_title | string(70) | | 自動生成，可覆寫 | SEO title |
| seo_description | string(160) | | 自動生成，可覆寫 | Meta description |
| status | enum | ✓ | draft / published / archived | 發布狀態 |
| locale | string(5) | ✓ | ISO 語言碼 | 語言版本 |
| created_at | datetime | auto | | 建立時間 |
| updated_at | datetime | auto | | 更新時間 |
| published_at | datetime | | | 發布時間 |

### 12.2.2 ProductCategory

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| category_name | string(60) | ✓ | 不可空 | 分類名稱 |
| slug | string(60) | auto | 自動生成 | URL slug |
| description | richtext | | | 分類描述 |
| image | image | | | 分類代表圖 |
| parent_id | fk → ProductCategory (self) | | 最多兩層 | 上層分類 |
| sort_order | integer | | 預設 0 | 顯示排序 |
| seo_title | string(70) | | 自動生成 | SEO title |
| seo_description | string(160) | | 自動生成 | Meta description |
| status | enum | ✓ | draft / published | 狀態 |
| locale | string(5) | ✓ | | 語言版本 |

### 12.2.3 Application

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| application_name | string(80) | ✓ | | 應用名稱 |
| slug | string(80) | auto | | URL slug |
| problem_statement | string(200) | ✓ | | 解決什麼問題 |
| full_description | richtext | ✓ | | 完整說明 |
| image | image | | | 應用場景圖 |
| industries | tag[] | ✓ | 至少 1 個 | 適用產業 |
| products | m2m → Product | | 反向自動帶入 | 適用產品 |
| faqs | m2m → FAQItem | | | 相關 FAQ |
| related_applications | m2m → Application (self) | | | 相關應用 |
| evidence | richtext | | | 證據素材 |
| seo_title | string(70) | | | SEO title |
| seo_description | string(160) | | | Meta description |
| status | enum | ✓ | | 狀態 |
| locale | string(5) | ✓ | | 語言版本 |

### 12.2.4 FAQItem

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| question | string(200) | ✓ | | 問題 |
| answer | richtext | ✓ | | 回答 |
| topic | string(80) | | | FAQ 主題分群 |
| slug | string(80) | auto | | URL slug（獨立頁時使用） |
| products | m2m → Product | | | 相關產品 |
| applications | m2m → Application | | | 相關應用 |
| sort_order | integer | | | 顯示排序 |
| status | enum | ✓ | | 狀態 |
| locale | string(5) | ✓ | | 語言版本 |

### 12.2.5 ComparisonTopic

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| title | string(100) | ✓ | | 比較主題 |
| slug | string(100) | auto | | URL slug |
| compared_products | m2m → Product | ✓ | 至少 2 個 | 被比較產品 |
| dimensions | json | ✓ | 至少 1 個面向 | 比較面向 |
| analysis | richtext | | | 差異解讀 |
| recommendation | richtext | | | 選用建議 |
| seo_title | string(70) | | | SEO title |
| seo_description | string(160) | | | Meta description |
| status | enum | ✓ | | 狀態 |
| locale | string(5) | ✓ | | 語言版本 |

### 12.2.6 Certification

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| cert_name | string(80) | ✓ | | 認證名稱 |
| slug | string(80) | auto | | URL slug |
| cert_type | enum | ✓ | certification / capability | 類型 |
| description | richtext | | | 說明 |
| standard | string(100) | | | 標準編號 |
| valid_from | date | | | 取得日期 |
| valid_until | date | | 須晚於 valid_from | 有效期限 |
| products | m2m → Product | | | 涵蓋產品 |
| applicable_markets | tag[] | | | 適用市場 |
| cert_image | image | | | 證書圖片 |
| status | enum | ✓ | | 狀態 |
| locale | string(5) | ✓ | | 語言版本 |

### 12.2.7 Capability

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| capability_name | string(80) | ✓ | | 能力名稱 |
| slug | string(80) | auto | | URL slug |
| description | richtext | ✓ | | 詳細說明 |
| highlights | string[] | | | 數據亮點 |
| image | image | | | 說明圖片 |
| status | enum | ✓ | | 狀態 |
| locale | string(5) | ✓ | | 語言版本 |

### 12.2.8 CTA

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| cta_name | string(50) | ✓ | 內部辨識用 | CTA 名稱 |
| cta_type | enum | ✓ | primary / secondary | CTA 層級 |
| display_text | string(30) | ✓ | | 按鈕文字 |
| action_type | enum | ✓ | link / form / rfq / download / scroll | 行為類型 |
| target_url | string | | action_type=link 時必填 | 目標連結 |
| target_form_id | fk | | action_type=form/rfq 時必填 | 目標表單 |
| target_file_id | fk | | action_type=download 時必填 | 目標文件 |
| placement_rules | json | | | 出現條件規則 |
| locale | string(5) | ✓ | | 語言版本 |

### 12.2.9 Page

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| page_type | enum | ✓ | homepage / category / product / application / faq / comparison / specification / certification / capability / rfq / contact / about | 頁型 |
| slug | string(150) | auto | 由 page_type + entity slug 組合 | URL path |
| title | string(70) | ✓ | | 頁面 title |
| entity_id | uuid | | 對應的 content entity | 關聯實體 |
| entity_type | string | | 對應的 entity 類型 | 關聯實體類型 |
| brief_id | fk → PageBrief | | | 對應 page brief |
| status | enum | ✓ | draft / published / archived | 狀態 |
| locale | string(5) | ✓ | | 語言版本 |
| canonical_url | string | auto | 自動生成 | canonical |
| noindex | boolean | | 預設 false | 搜尋引擎索引控制 |
| published_at | datetime | | | 發布時間 |
| created_at | datetime | auto | | 建立時間 |
| updated_at | datetime | auto | | 更新時間 |

### 12.2.10 PageBrief

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| page_type | enum | ✓ | | 頁面類型 |
| target_market | tag[] | ✓ | 至少 1 個 | 目標市場 |
| target_persona | tag[] | ✓ | 至少 1 個 | 目標客群 |
| search_intent | enum | ✓ | educational / comparison / alternative / specification / purchasing | 搜尋意圖類型 |
| primary_topic | string(100) | ✓ | | 主要主題 |
| keywords | string[] | ✓ | 至少 1 個 | 關鍵字群 |
| related_entity_id | uuid | | | 對應產品/應用 |
| related_entity_type | string | | | entity 類型 |
| evidence_notes | text | | | 證據素材指引 |
| primary_cta_id | fk → CTA | ✓ | | 主要 CTA |
| secondary_cta_ids | fk[] → CTA | | | 次要 CTA |
| tone | enum | | technical / consultative / educational | 語氣 |
| target_kpi | string(100) | | | 頁面目標 KPI |
| status | enum | ✓ | draft / approved / in_progress / completed / published | 狀態 |
| created_by | fk → User | auto | | 建立者 |
| approved_by | fk → User | | | 審核者 |
| locale | string(5) | ✓ | | 語言版本 |

### 12.2.11 ContentAsset

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| id | uuid | auto | | 主鍵 |
| asset_type | enum | ✓ | image / pdf / cad / video / document | 資產類型 |
| file_name | string(200) | ✓ | | 檔案名稱 |
| file_url | string | ✓ | | 檔案路徑 |
| file_size | integer | auto | bytes | 檔案大小 |
| alt_text | string(200) | | 圖片必填 | 替代文字 |
| mime_type | string(50) | auto | | MIME 類型 |
| related_entity_id | uuid | | | 關聯實體 |
| related_entity_type | string | | | 實體類型 |
| locale | string(5) | | | 語言版本 |

---

## 12.3 內容任務定義規格（Page Brief 流程）

### 12.3.1 Page Brief 生命週期

```
Draft → Approved → In Progress → Completed → Published
                                      ↓
                                  Revision
```

| 狀態 | 說明 | 可執行動作 |
|------|------|------------|
| Draft | Marketing Manager 建立初稿 | 編輯、刪除、送審 |
| Approved | 審核通過，可開始內容生成 | 開始生成、退回 |
| In Progress | AI 正在生成或人工編修中 | 標記完成、退回 |
| Completed | 內容已就緒，等待發布 | 發布、退回修改 |
| Published | 已發布上線 | 下架、建立修訂版 |
| Revision | 已發布內容需要修改 | 編輯、重新發布 |

### 12.3.2 必填條件

Page Brief 送審前必須滿足以下條件：

1. page_type 已選定
2. target_market 至少選擇 1 個
3. target_persona 至少選擇 1 個
4. search_intent 已選定
5. primary_topic 已填寫
6. keywords 至少填 1 個
7. primary_cta_id 已指定

### 12.3.3 審核流程

| 步驟 | 角色 | 動作 |
|------|------|------|
| 1 | Marketing Manager | 建立 Page Brief，填寫所有必填欄位 |
| 2 | Marketing Manager | 自行審核或指派其他人審核 |
| 3 | 審核者 | 確認 brief 內容合理，審核通過或退回 |
| 4 | 系統 | 狀態改為 Approved，可觸發 AI 生成 |

Phase 1 簡化：Marketing Manager 可直接自審自批，不強制跨角色審核。

### 12.3.4 與內容策略地圖的關係

Page Brief 不應獨立存在，必須對應到內容策略地圖中的某個位置：

1. 內容策略地圖定義「做哪些頁」→ Page Brief 定義「這一頁怎麼做」
2. 系統應提供從策略地圖直接展開 Page Brief 的入口
3. 未在策略地圖中的 Page Brief 應被標記為「未規劃」

---

## 12.4 AI 生成規格

### 12.4.1 生成觸發條件

AI 生成只能在以下條件下觸發：

1. 對應 Page Brief 狀態為 Approved
2. 必要的結構化資料已存在（產品規格、應用描述等）
3. 使用者明確點擊「生成初稿」按鈕

不允許：自動觸發、排程批次生成、無 brief 生成。

### 12.4.2 輸入欄位

AI 生成時的輸入來源：

| 輸入來源 | 內容 | 必要性 |
|----------|------|--------|
| PageBrief | 頁型、意圖、主題、關鍵字、CTA、語氣 | 必要 |
| Entity 資料 | 產品規格、應用描述、FAQ、認證資訊 | 必要（依頁型） |
| Entity 關聯 | 相關產品、應用、認證、FAQ 的關聯 | 自動帶入 |
| 頁型模板 | 該頁型的區塊結構與欄位定義 | 必要 |
| 公司基本資料 | 公司名、定位、核心用語 | 必要 |

### 12.4.3 輸出格式

AI 依頁型模板產出結構化內容，而非自由文章：

**產品詳頁生成輸出範例**：

```json
{
  "seo_title": "...",
  "seo_description": "...",
  "short_description": "...",
  "full_description": "...(richtext)...",
  "specification_summary": "...",
  "application_summary": "...",
  "faq_suggestions": [
    {"question": "...", "answer": "..."},
    {"question": "...", "answer": "..."}
  ],
  "cta_text_suggestion": "..."
}
```

**應用頁生成輸出範例**：

```json
{
  "seo_title": "...",
  "seo_description": "...",
  "problem_statement": "...",
  "full_description": "...(richtext)...",
  "product_relevance_summary": "...",
  "faq_suggestions": [
    {"question": "...", "answer": "..."}
  ],
  "cta_text_suggestion": "..."
}
```

### 12.4.4 支援頁型（Phase 1）

| 頁型 | 支援程度 | 說明 |
|------|----------|------|
| 產品詳頁 | 完整支援 | 依規格資料生成所有文案欄位 |
| 應用頁 | 完整支援 | 依應用資料與關聯產品生成 |
| FAQ 頁 | 完整支援 | 依產品/應用資料生成 Q&A |
| 比較頁 | 完整支援 | 依被比較產品規格生成比較分析 |
| 產品分類頁 | 部分支援 | 生成分類描述與摘要 |
| 認證/能力頁 | 部分支援 | 生成說明文案 |
| 首頁 | 不支援 | 首頁文案需人工定義 |
| RFQ/Contact/About | 不支援 | 表單頁不需要 AI 內容 |

### 12.4.5 編修與覆寫方式

| 操作 | 說明 |
|------|------|
| 接受 | 直接採用 AI 生成內容 |
| 逐欄修改 | 在 AI 產出基礎上逐欄位編輯 |
| 重新生成 | 使用相同輸入重新生成（不保留前次） |
| 手動覆寫 | 完全跳過 AI，人工填寫 |

### 12.4.6 人工審核狀態

每段 AI 生成內容都有以下狀態標記：

| 狀態 | 說明 |
|------|------|
| ai_generated | AI 剛生成，未經人工審核 |
| human_reviewed | 已經人工確認或修改 |
| human_written | 完全由人工撰寫，未使用 AI |

此狀態會記錄在每個 content field 層級，不只在 page 層級。

### 12.4.7 AI 可追溯性

每次 AI 生成都記錄：

1. 生成時間
2. 使用的 model 版本
3. 輸入的 PageBrief ID
4. 輸入的 Entity IDs
5. 生成的完整輸出
6. 誰觸發的生成
7. 後續的人工修改紀錄

---

## 12.5 事件字典

### 12.5.1 事件總表

| # | 事件名稱 | 觸發條件 | 事件來源 | Phase |
|---|----------|----------|----------|-------|
| 1 | page_view | 任何頁面載入完成 | 前端 SDK | 1a |
| 2 | category_view | 產品分類頁載入 | 前端 SDK | 1a |
| 3 | product_view | 產品詳頁載入 | 前端 SDK | 1a |
| 4 | application_view | 應用頁載入 | 前端 SDK | 1a |
| 5 | faq_expand | 展開任一 FAQ 問答 | 前端 SDK | 1b |
| 6 | comparison_view | 比較頁載入 | 前端 SDK | 1b |
| 7 | spec_download | 點擊下載規格書/文件 | 前端 SDK | 1b |
| 8 | certification_view | 認證/能力頁載入 | 前端 SDK | 1b |
| 9 | cta_click | 點擊任何 CTA 元件 | 前端 SDK | 1b |
| 10 | form_start | 表單第一個欄位獲得焦點 | 前端 SDK | 1b |
| 11 | form_submit | 表單成功送出 | 後端 API | 1b |
| 12 | rfq_start | RFQ 表單第一個欄位獲得焦點 | 前端 SDK | 1b |
| 13 | rfq_submit | RFQ 表單成功送出 | 後端 API | 1b |
| 14 | return_visit | 同一 visitor 在 24h+ 後再次造訪 | 後端計算 | 1b |
| 15 | session_depth_reached | 同一 session 瀏覽頁數 ≥ 閾值 | 後端計算 | 1b |

### 12.5.2 事件共用屬性

所有事件都攜帶以下共用屬性：

| 屬性 | 類型 | 說明 |
|------|------|------|
| event_id | uuid | 事件唯一識別 |
| event_name | string | 事件名稱 |
| timestamp | datetime | 事件時間（UTC） |
| session_id | uuid | 會話 ID |
| visitor_id | uuid | 訪客 ID（first-party cookie） |
| page_url | string | 當前頁面 URL |
| page_type | enum | 頁面類型 |
| page_id | uuid | 頁面 ID |
| locale | string | 語言版本 |
| referrer | string | 來源頁面 |
| traffic_source | string | 流量來源（organic / paid / direct / referral / social） |
| campaign_id | string | 行銷活動 ID（UTM） |
| user_agent | string | 瀏覽器標識 |
| device_type | enum | desktop / mobile / tablet |
| country | string | GeoIP 解析國家 |

### 12.5.3 事件專屬屬性

**page_view**：無額外屬性，僅共用屬性。

**category_view**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| category_id | uuid | 分類 ID |
| category_name | string | 分類名稱 |
| product_count | integer | 該分類產品數量 |

**product_view**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| product_id | uuid | 產品 ID |
| product_name | string | 產品名稱 |
| model_number | string | 型號 |
| category_id | uuid | 所屬分類 |

**application_view**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| application_id | uuid | 應用 ID |
| application_name | string | 應用名稱 |
| industries | string[] | 適用產業 |

**faq_expand**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| faq_id | uuid | FAQ 項目 ID |
| question_text | string | 問題文字（前 100 字） |
| context_entity_type | string | FAQ 所在頁面的 entity 類型 |
| context_entity_id | uuid | FAQ 所在頁面的 entity ID |

**comparison_view**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| comparison_id | uuid | 比較主題 ID |
| compared_product_ids | uuid[] | 被比較產品 ID 列表 |

**spec_download**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| file_id | uuid | 檔案 ID |
| file_name | string | 檔案名稱 |
| file_type | string | 檔案類型（pdf / cad / etc） |
| product_id | uuid | 關聯產品 ID |

**certification_view**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| cert_id | uuid | 認證 ID |
| cert_name | string | 認證名稱 |

**cta_click**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| cta_id | uuid | CTA ID |
| cta_name | string | CTA 名稱 |
| cta_type | enum | primary / secondary |
| action_type | enum | link / form / rfq / download / scroll |

**form_start / form_submit**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| form_id | uuid | 表單 ID |
| form_type | enum | contact / rfq / download_gate / subscribe |

**rfq_start / rfq_submit**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| rfq_id | uuid | RFQ ID（submit 時才有） |
| product_ids | uuid[] | 詢價產品列表 |
| application_id | uuid | 關聯應用（選填） |

**return_visit**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| days_since_last | integer | 距上次造訪天數 |
| total_visits | integer | 歷史總造訪次數 |
| previous_pages_viewed | string[] | 上次造訪的頁面類型 |

**session_depth_reached**：

| 屬性 | 類型 | 說明 |
|------|------|------|
| depth | integer | 本次 session 已瀏覽頁數 |
| threshold | integer | 觸發閾值（預設 5） |
| pages_viewed | uuid[] | 已瀏覽頁面列表 |

### 12.5.4 事件儲存格式

```json
{
  "event_id": "uuid",
  "event_name": "product_view",
  "timestamp": "2026-03-14T08:30:00Z",
  "session_id": "uuid",
  "visitor_id": "uuid",
  "page_url": "/products/hydraulic-seals/model-x100/",
  "page_type": "product",
  "page_id": "uuid",
  "locale": "en",
  "referrer": "https://www.google.com/",
  "traffic_source": "organic",
  "campaign_id": null,
  "device_type": "desktop",
  "country": "US",
  "properties": {
    "product_id": "uuid",
    "product_name": "Model X100 Hydraulic Seal",
    "model_number": "X100",
    "category_id": "uuid"
  }
}
```

儲存規則：

1. 所有事件寫入事件表（event log），不可刪除，僅可查詢
2. 事件資料保留至少 24 個月
3. 高頻事件（page_view）可依月份分區
4. 事件需支援批次查詢與聚合統計

---

## 12.6 意圖規則規格

### 12.6.1 評分規則

| 事件 | 基礎分數 | 加權條件 | 加權分數 |
|------|----------|----------|----------|
| page_view | +1 | — | — |
| category_view | +2 | — | — |
| product_view | +3 | 同產品重複瀏覽 | +2 |
| application_view | +4 | — | — |
| faq_expand | +6 | 展開 3 個以上 FAQ | +4 |
| comparison_view | +6 | — | — |
| spec_download | +8 | — | — |
| certification_view | +3 | — | — |
| cta_click (secondary) | +4 | — | — |
| cta_click (primary) | +8 | — | — |
| form_start | +5 | — | — |
| rfq_start | +15 | — | — |
| rfq_submit | +30 | — | — |
| return_visit | +6 | 7 天內回訪 | +4 |
| session_depth_reached | +5 | depth ≥ 8 | +3 |

### 12.6.2 分數衰減規則

| 條件 | 衰減方式 |
|------|----------|
| 7 天無活動 | 總分 × 0.8 |
| 14 天無活動 | 總分 × 0.5 |
| 30 天無活動 | 總分 × 0.2 |
| 60 天無活動 | 總分歸零 |

衰減以最後一次事件時間為基準，每日凌晨批次計算。

### 12.6.3 意圖階段（Intent Stage）

| 階段 | 分數門檻 | 說明 |
|------|----------|------|
| Cold | 0-9 | 低意圖，僅瀏覽 |
| Warm | 10-29 | 中等意圖，有互動行為 |
| Hot | 30-59 | 高意圖，有明確產品興趣 |
| Sales-Ready | 60+ | 可直接跟進，有 RFQ 或反覆高意圖行為 |

### 12.6.4 觸發動作條件

| 條件 | 觸發動作 | 目標 |
|------|----------|------|
| 訪客進入 Warm | 加入再行銷受眾 | Conversion Orchestration |
| 訪客進入 Hot | 建立 sales alert | Sales User |
| 訪客進入 Sales-Ready | 建立高優先 sales alert + email 通知 | Sales User |
| rfq_submit | 建立 RFQ 工單 + 分流 | Conversion Orchestration |
| 訪客從 Hot 衰退到 Warm | 加入 nurture 再行銷受眾 | Conversion Orchestration |

### 12.6.5 評分對象

評分以 visitor 為主要粒度：

1. **Visitor-level score**：個別訪客的累積分數（Phase 1）
2. **Account-level score**：同一公司多個訪客的分數彙總（Phase 2，需公司識別）

### 12.6.6 分數查詢

Dashboard 需支援以下查詢：

1. 依 intent stage 篩選訪客列表
2. 依分數排序的 Top N 訪客
3. 特定訪客的事件時間軸與分數變化
4. 依產品分類或應用篩選高意圖訪客
5. intent stage 轉換漏斗（Cold → Warm → Hot → Sales-Ready）

---

## 12.7 表單與 RFQ 流程規格

### 12.7.1 表單類型

| 表單類型 | 用途 | Phase |
|----------|------|-------|
| RFQ | 產品詢價 | 1b |
| Contact | 一般聯絡 | 1b |
| Download Gate | 下載文件前需留資 | 2 |
| Subscribe | 訂閱電子報 | 2 |

### 12.7.2 RFQ 表單欄位

| 欄位 | 類型 | 必填 | 驗證規則 | 說明 |
|------|------|------|----------|------|
| full_name | string(100) | ✓ | 不可空 | 姓名 |
| company_name | string(100) | ✓ | 不可空 | 公司名稱 |
| email | string(100) | ✓ | email 格式 | Email |
| phone | string(30) | | | 電話 |
| country | string(50) | ✓ | 國家選單 | 國家 |
| job_title | string(80) | | | 職稱 |
| products_of_interest | relation[] | ✓ | 至少選 1 個產品或分類 | 感興趣產品 |
| application | relation | | | 應用場景 |
| quantity | string(50) | | | 數量/用量 |
| specifications | text | | | 規格需求 |
| timeline | enum | | immediate / 1-3 months / 3-6 months / evaluating | 採購時程 |
| message | text | | | 附加說明 |
| how_did_you_find_us | enum | | google / exhibition / referral / other | 如何找到我們 |
| consent | boolean | ✓ | 必須勾選 | 同意隱私條款 |

**前端行為**：

1. 若訪客從產品頁點擊詢價 CTA，products_of_interest 自動帶入該產品
2. 若訪客從應用頁點擊，application 自動帶入
3. 表單應支援自動儲存草稿（localStorage）

### 12.7.3 Contact 表單欄位

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| full_name | string(100) | ✓ | 姓名 |
| email | string(100) | ✓ | Email |
| company_name | string(100) | | 公司名稱 |
| subject | string(100) | ✓ | 主旨 |
| message | text | ✓ | 訊息內容 |
| consent | boolean | ✓ | 同意隱私條款 |

### 12.7.4 RFQ 送出後流程

```
RFQ 送出 → 建立 RFQRequest → 路由分流 → 通知 → 跟進 → 關閉
```

**RFQRequest 資料模型**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | uuid | 主鍵 |
| rfq_number | string | 系統自動編號（RFQ-YYYYMMDD-NNN） |
| contact_id | fk → Contact | 關聯聯絡人 |
| visitor_id | fk → Visitor | 關聯訪客 |
| products | relation[] | 詢價產品 |
| application_id | fk | 關聯應用 |
| form_data | json | 完整表單資料 |
| intent_score | integer | 送出時的意圖分數 |
| status | enum | new / assigned / in_progress / quoted / won / lost / expired |
| assigned_to | fk → User | 指派業務 |
| priority | enum | normal / high / urgent |
| source_page | string | 送出頁面 URL |
| created_at | datetime | 建立時間 |
| updated_at | datetime | 更新時間 |
| closed_at | datetime | 關閉時間 |

### 12.7.5 路由分流規則

Phase 1 支援以下分流條件：

| 條件 | 分流邏輯 |
|------|----------|
| 產品分類 | 依產品分類指派不同業務 |
| 國家/區域 | 依國家指派不同業務或區域負責人 |
| 意圖分數 | High-intent（≥30）標記高優先 |
| 預設 | 未命中任何規則時的預設指派人 |

Phase 1 分流規則以設定檔管理，不需要視覺化規則編輯器。

### 12.7.6 通知規則

| 觸發條件 | 通知方式 | 接收者 |
|----------|----------|--------|
| 新 RFQ 建立 | Email + 系統內通知 | 被指派業務 |
| RFQ 高優先（intent ≥ 30） | Email（含高優先標記） | 被指派業務 + Admin |
| RFQ 未處理超過 24h | Email 提醒 | 被指派業務 |
| RFQ 未處理超過 48h | Email 升級 | Admin |
| RFQ 狀態變更 | 系統內通知 | 原指派業務 |

### 12.7.7 CRM 欄位映射（HubSpot 為例）

| RFQ 欄位 | HubSpot 欄位 | 說明 |
|----------|-------------|------|
| full_name | firstname + lastname | 拆分姓名 |
| company_name | company | 公司 |
| email | email | Email |
| phone | phone | 電話 |
| country | country | 國家 |
| job_title | jobtitle | 職稱 |
| products_of_interest | custom: products_of_interest | 自訂欄位 |
| timeline | custom: purchase_timeline | 自訂欄位 |
| intent_score | custom: intent_score | 自訂欄位 |
| rfq_number | custom: rfq_number | 自訂欄位 |
| source_page | custom: rfq_source_page | 自訂欄位 |

RFQ 送出時同步建立/更新 HubSpot Contact + Deal。

---

## 12.8 整合規格

### 12.8.1 GA4 事件映射

系統事件到 GA4 事件的映射：

| 系統事件 | GA4 事件名稱 | GA4 參數 |
|----------|-------------|----------|
| page_view | page_view | page_title, page_location |
| product_view | view_item | item_id, item_name, item_category |
| category_view | view_item_list | item_list_id, item_list_name |
| spec_download | file_download | file_name, file_extension, link_url |
| cta_click | select_content | content_type, item_id |
| rfq_start | begin_checkout | — |
| rfq_submit | purchase | transaction_id, value=0 |
| form_submit | generate_lead | — |

映射規則：

1. 系統事件是主要事件源，GA4 僅作輔助同步
2. 映射透過後端 server-side 或前端 gtag 並行發送
3. 不依賴 GA4 的事件做任何系統內邏輯決策

### 12.8.2 CRM 欄位映射

#### Contact 映射

| 系統欄位 | HubSpot 欄位 | 方向 | 說明 |
|----------|-------------|------|------|
| full_name | firstname + lastname | 系統→CRM | 建立/更新 |
| email | email | 雙向 | 去重識別鍵 |
| company_name | company | 系統→CRM | |
| phone | phone | 系統→CRM | |
| country | country | 系統→CRM | |
| job_title | jobtitle | 系統→CRM | |
| intent_score | custom: intent_score | 系統→CRM | 定期同步 |
| intent_stage | custom: intent_stage | 系統→CRM | 定期同步 |
| first_visit_date | custom: first_visit | 系統→CRM | |
| last_visit_date | custom: last_visit | 系統→CRM | |
| total_page_views | custom: total_page_views | 系統→CRM | |
| products_viewed | custom: products_viewed | 系統→CRM | 最近瀏覽的產品列表 |

#### Deal 映射（RFQ → Deal）

| 系統欄位 | HubSpot 欄位 | 說明 |
|----------|-------------|------|
| rfq_number | dealname | Deal 名稱 |
| status | dealstage | 狀態映射 |
| products_of_interest | custom: products | |
| intent_score | custom: intent_score | |
| source_page | custom: source_page | |
| created_at | createdate | |

Phase 1 同步方向：系統 → CRM（單向）。Phase 2 可考慮雙向。

### 12.8.3 Ads Audience Sync

#### Google Ads Customer Match

同步方式：透過 Google Ads API 的 Customer Match 功能。

| 受眾類型 | 同步條件 | 更新頻率 |
|----------|----------|----------|
| High-intent visitors | intent_stage = Hot 或 Sales-Ready + 有 email | 每日 |
| Product category interest | 瀏覽特定分類 ≥ 3 頁 + 有 email | 每日 |
| RFQ submitted | 已送出 RFQ | 即時 |
| Return visitors | return_visit 事件 + 有 email | 每日 |

#### Meta Custom Audiences

同步方式：透過 Meta Conversions API。

| 事件類型 | 對應 Meta 事件 | 說明 |
|----------|---------------|------|
| product_view | ViewContent | content_type=product |
| rfq_start | InitiateCheckout | — |
| rfq_submit | Lead | — |
| spec_download | AddToCart | content_type=document |

另外支援以 email hash 建立 Custom Audience。

#### LinkedIn Matched Audiences

Phase 2：透過 LinkedIn Marketing API 同步公司名單與 email 名單。

### 12.8.4 Webhook Payload

通用 webhook 格式，用於整合未直接支援的系統：

```json
{
  "event": "rfq.created",
  "timestamp": "2026-03-14T08:30:00Z",
  "data": {
    "rfq_id": "uuid",
    "rfq_number": "RFQ-20260314-001",
    "contact": {
      "full_name": "John Doe",
      "email": "john@example.com",
      "company": "Acme Corp",
      "country": "US"
    },
    "products": [
      {"product_id": "uuid", "product_name": "Model X100", "model_number": "X100"}
    ],
    "intent_score": 45,
    "intent_stage": "Hot",
    "source_page": "/products/hydraulic-seals/model-x100/"
  },
  "metadata": {
    "webhook_id": "uuid",
    "retry_count": 0
  }
}
```

支援的 webhook 事件：

| 事件名稱 | 觸發時機 |
|----------|----------|
| rfq.created | 新 RFQ 送出 |
| rfq.status_changed | RFQ 狀態變更 |
| contact.created | 新聯絡人建立 |
| contact.intent_stage_changed | 意圖階段改變 |
| visitor.became_hot | 訪客進入 Hot 階段 |

Webhook 規則：

1. 支援自訂 endpoint URL
2. 使用 HMAC-SHA256 簽章驗證
3. 失敗重試 3 次（間隔 1min / 5min / 30min）
4. 記錄所有 webhook 發送紀錄與回應

---

## 12.9 SEO 與 IA 規格

### 12.9.1 URL 結構規則

| 頁型 | URL 規則 | 範例 |
|------|----------|------|
| 首頁 | `/` | `/` |
| 產品分類 | `/products/{category-slug}/` | `/products/hydraulic-seals/` |
| 子分類 | `/products/{parent-slug}/{child-slug}/` | `/products/hydraulic-seals/piston-seals/` |
| 產品詳頁 | `/products/{category-slug}/{product-slug}/` | `/products/hydraulic-seals/model-x100/` |
| 應用頁 | `/applications/{application-slug}/` | `/applications/high-pressure-hydraulic-systems/` |
| FAQ | `/faq/{faq-topic-slug}/` | `/faq/hydraulic-seal-selection/` |
| 比較頁 | `/compare/{comparison-slug}/` | `/compare/nbr-vs-fkm-seals/` |
| 規格總覽 | `/specifications/{spec-slug}/` | `/specifications/hydraulic-seal-dimensions/` |
| 認證 | `/certifications/{cert-slug}/` | `/certifications/iso-9001/` |
| 能力 | `/capabilities/{capability-slug}/` | `/capabilities/custom-molding/` |
| RFQ | `/request-quote/` | `/request-quote/` |
| Contact | `/contact/` | `/contact/` |
| About | `/about/` | `/about/` |

URL 規則：

1. 全部小寫
2. 使用 `-` 分隔單詞，不使用 `_` 或空格
3. slug 由 entity 名稱自動生成，可手動覆寫
4. 不包含日期、ID 或無意義參數
5. 最深不超過 3 層
6. 多語頁面使用子目錄：`/zh/products/...`（Phase 2）

### 12.9.2 Taxonomy 定義

#### 產品分類 Taxonomy

- 最多兩層（大分類 → 子分類）
- 每個產品必須歸屬一個分類
- 一個產品只能屬於一個分類（避免重複索引）
- 分類名稱必須互斥且完整覆蓋產品線

#### 應用分類 Taxonomy

- 單層，不做巢狀
- 一個應用可對應多個產業
- 應用與產品為多對多關係

#### 產業標籤

- 標準化產業標籤集（預定義清單，可擴充）
- 範例：Automotive / Aerospace / Oil & Gas / Food & Beverage / Semiconductor / Construction / Marine / Mining / Medical

#### 規格屬性

- 依產品分類定義可用規格屬性
- 規格屬性包含：名稱、值、單位
- 用於產品篩選（Phase 2）與結構化規格表

#### 認證類型

- 預定義清單：ISO 9001 / IATF 16949 / AS9100 / FDA / CE / UL / RoHS / REACH / 其他
- 可擴充

### 12.9.3 內連規則

系統根據 entity 關聯自動生成內部連結：

| 來源頁 | 連結到 | 觸發條件 |
|--------|--------|----------|
| 產品詳頁 | 所屬分類頁 | 自動（breadcrumb + 文內連結） |
| 產品詳頁 | 適用應用頁 | 自動（關聯存在時） |
| 產品詳頁 | 相關 FAQ 頁 | 自動（關聯存在時） |
| 產品詳頁 | 相關比較頁 | 自動（關聯存在時） |
| 產品詳頁 | 替代料號產品 | 自動（關聯存在時） |
| 產品詳頁 | 認證頁 | 自動（關聯存在時） |
| 應用頁 | 適用產品詳頁 | 自動（關聯存在時） |
| 應用頁 | 相關 FAQ 頁 | 自動（關聯存在時） |
| 應用頁 | 相關應用頁 | 自動（關聯存在時） |
| 分類頁 | 子分類或產品 | 自動 |
| 分類頁 | 相關應用頁 | 自動（透過產品-應用關聯推導） |
| FAQ 頁 | 相關產品/應用 | 自動（關聯存在時） |
| 比較頁 | 被比較產品 | 自動 |
| 認證頁 | 涵蓋產品 | 自動（關聯存在時） |

內連展示方式：

1. **Breadcrumb**：所有頁面自動依 taxonomy 產生
2. **區塊式連結**：「相關產品」「適用應用」等區塊
3. **文內 anchor**：AI 生成內容時可在文案中嵌入（Phase 2）

### 12.9.4 Canonical 規則

| 情況 | canonical 指向 |
|------|---------------|
| 標準頁面 | 自身 URL |
| 帶篩選/排序參數的分類頁 | 去掉參數的原始分類頁 URL |
| 多語同內容頁 | 各語言版本指向自身（配合 hreflang） |
| 印刷版 / AMP 版 | 指向標準 HTML 版 |
| 產品出現在多個列表 | 產品詳頁為 canonical，列表頁為自身 |

### 12.9.5 Structured Data Mapping

| 頁型 | Schema 類型 | 主要欄位 |
|------|-------------|----------|
| 首頁 | Organization + WebSite | name, url, logo, contactPoint |
| 產品分類頁 | BreadcrumbList + CollectionPage | — |
| 產品詳頁 | Product + BreadcrumbList | name, description, image, brand, sku, manufacturer, offers（如有價格） |
| 應用頁 | TechArticle + BreadcrumbList | headline, description, author |
| FAQ 頁 | FAQPage + BreadcrumbList | mainEntity（Question + Answer） |
| 比較頁 | Article + BreadcrumbList | headline, description |
| 認證頁 | BreadcrumbList | — |
| Contact | ContactPage | — |
| About | Organization | name, description, foundingDate, numberOfEmployees |

Structured Data 規則：

1. 由內容模型自動輸出，不依賴手工標記
2. 使用 JSON-LD 格式，放在 `<head>` 中
3. 每次發布時自動驗證 schema 完整性
4. Product schema 的 `offers` 欄位依客戶是否揭露價格決定是否輸出

### 12.9.6 Robots / Noindex 規則

| 頁面 | robots 指令 | 說明 |
|------|-------------|------|
| 所有一般內容頁 | index, follow | 預設 |
| RFQ / 詢價頁 | noindex, follow | 不需搜尋收錄 |
| 搜尋結果頁 | noindex, follow | 站內搜尋（如有） |
| 篩選後的分類頁（帶參數） | noindex, follow | 避免重複索引 |
| Thank you / 確認頁 | noindex, nofollow | |
| 草稿 / 未發布頁 | noindex, nofollow | 系統自動處理 |
| Admin / Dashboard | noindex, nofollow | 後台頁面 |

robots.txt 規則：

```
User-agent: *
Disallow: /admin/
Disallow: /api/
Disallow: /thank-you/
Sitemap: /sitemap.xml
```

### 12.9.7 Sitemap 分組規則

| Sitemap 檔案 | 涵蓋頁型 |
|--------------|----------|
| sitemap-pages.xml | 首頁、About、Contact |
| sitemap-products.xml | 產品分類頁 + 產品詳頁 |
| sitemap-applications.xml | 應用頁 |
| sitemap-resources.xml | FAQ、比較、規格頁 |
| sitemap-certifications.xml | 認證 + 能力頁 |
| sitemap.xml | 主索引，指向以上所有子 sitemap |

Phase 2 多語：每個語言版本獨立子 sitemap（sitemap-products-en.xml、sitemap-products-zh.xml）。

Sitemap 規則：

1. 系統自動更新，頁面發布/下架時立即重新生成
2. 僅收錄 status=published 且非 noindex 的頁面
3. 包含 lastmod（使用 updated_at 或 published_at）
4. 單一 sitemap 檔案不超過 50,000 URL

### 12.9.8 圖片 SEO 規則

| 項目 | 規則 |
|------|------|
| alt text | 由系統依 entity 名稱自動生成：`{product_name} - {short_description}` |
| alt text 覆寫 | 可手動覆寫 |
| 檔名 | 上傳時自動重新命名為 `{entity-slug}-{序號}.{ext}` |
| 格式 | 支援 WebP 自動轉換（Phase 2），Phase 1 接受 JPG/PNG |
| lazy loading | 首屏以外圖片使用 native lazy loading |
| 尺寸 | 提供 srcset 多尺寸（Phase 2），Phase 1 限制最大寬度 |
| 壓縮 | 上傳時自動壓縮（品質 80-85%） |

---

## 12.10 Entity 關聯規格

### 12.10.1 關聯定義

| 關聯 | 類型 | 必要性 | 說明 |
|------|------|--------|------|
| Product → ProductCategory | 多對一 | 必要 | 每個產品必須屬於一個分類 |
| Product → Application | 多對多 | 建議 | 產品適用的應用場景 |
| Product → Certification | 多對多 | 選填 | 產品具備的認證 |
| Product → FAQItem | 多對多 | 選填 | 產品相關 FAQ |
| Product → ComparisonTopic | 多對多 | 選填 | 可比較主題 |
| Product → Product（替代料號） | 多對多(self) | 選填 | 替代料號關係（雙向） |
| Product → ContentAsset | 一對多 | 選填 | 下載資源 |
| Application → Product | 多對多 | 反向 | 適用產品（反向查詢） |
| Application → FAQItem | 多對多 | 選填 | 應用相關 FAQ |
| Application → Application（相關） | 多對多(self) | 選填 | 相關應用 |
| Application → Industry Tag | 多對多 | 必要 | 適用產業 |
| Certification → Product | 多對多 | 反向 | 涵蓋產品（反向查詢） |
| Certification → Market Tag | 多對多 | 選填 | 適用市場 |
| FAQItem → Product | 多對多 | 反向 | 相關產品（反向查詢） |
| FAQItem → Application | 多對多 | 反向 | 相關應用（反向查詢） |
| ComparisonTopic → Product | 多對多 | 必要 | 被比較產品（至少 2） |
| ProductCategory → ProductCategory（parent） | 多對一(self) | 選填 | 上下層分類 |

### 12.10.2 替代料號關係

替代料號是特殊的自關聯：

1. 雙向關係：A 是 B 的替代 = B 也是 A 的替代
2. 建立時自動建立反向關聯
3. 刪除時詢問是否同時刪除反向
4. 替代料號可帶備註（如：尺寸兼容但材質不同）

資料模型：

| 欄位 | 類型 | 說明 |
|------|------|------|
| product_a_id | fk → Product | 產品 A |
| product_b_id | fk → Product | 產品 B |
| relation_type | enum | exact_replacement / compatible / upgrade | 替代類型 |
| note | string(200) | 備註 |

### 12.10.3 關聯驅動的系統行為

每個 entity 關聯不只是資料關係，而是驅動以下系統行為：

#### 內連自動化

| 關聯 | 產出的內連 |
|------|-----------|
| Product → Category | breadcrumb + 「回到分類」連結 |
| Product → Application | 「適用應用」區塊連結 |
| Product → Certification | 「認證」區塊連結 |
| Product → FAQ | 「常見問題」區塊連結 |
| Product → Comparison | 「比較」區塊連結 |
| Product → 替代料號 | 「替代/相關產品」區塊連結 |
| Application → Product | 「適用產品」區塊連結 |
| Application → FAQ | 「常見問題」區塊連結 |
| Application → 相關應用 | 「相關應用」區塊連結 |
| Certification → Product | 「涵蓋產品」區塊連結 |
| Category → Application | 「相關應用」區塊連結（透過產品推導） |

#### Structured Data 輸出

| 關聯 | Schema 影響 |
|------|-------------|
| Product → Category | Product schema 的 category 欄位 |
| Product → FAQ | 產品頁輸出 FAQPage schema |
| Product → Certification | Product schema 的 additionalProperty |
| Product → 替代料號 | Product schema 的 isSimilarTo |

#### 推薦邏輯

| 關聯 | 推薦結果 |
|------|----------|
| Product → Category（同分類） | 「同分類其他產品」 |
| Product → Application（共享應用） | 「適用相同場景的其他產品」 |
| Product → 替代料號 | 「替代產品」 |
| Application → 相關應用 | 「您可能也感興趣的應用」 |

#### AI 內容上下文

AI 生成內容時，以下關聯資料作為上下文輸入：

| 生成目標 | 關聯上下文 |
|----------|-----------|
| 產品詳頁文案 | 分類描述 + 適用應用描述 + 認證資訊 + FAQ 問題 |
| 應用頁文案 | 適用產品的規格摘要 + 產業標籤 + 相關 FAQ |
| FAQ 生成 | 關聯產品規格 + 應用場景 + 比較面向 |
| 比較頁文案 | 被比較產品的完整規格 + 分類 + 應用 |

#### GEO / AI 搜尋可抽取性

Entity 關聯使內容形成知識網絡，提高 AI 搜尋引擎（如 Google SGE、ChatGPT Browse）的引用機率：

1. 產品 → 應用的關聯讓 AI 能回答「什麼產品適合 XX 應用」
2. 產品 → 認證的關聯讓 AI 能回答「哪些產品有 XX 認證」
3. 產品 → 比較的關聯讓 AI 能回答「A 和 B 產品有什麼差別」
4. 完整的 FAQ 關聯讓 AI 能直接抽取問答

### 12.10.4 關聯管理介面需求

Phase 1 的管理介面需支援：

1. 建立/刪除 entity 關聯
2. 批次關聯（如一次將多個產品關聯到某應用）
3. 關聯檢視：從任一 entity 查看所有關聯
4. 孤立 entity 檢測：找出沒有任何關聯的產品/應用
5. 關聯統計：每個 entity 有多少關聯

不需要（Phase 2）：

1. 關聯權重/排序
2. 條件式關聯（依市場或語言不同的關聯）
3. 關聯推薦（AI 建議可能的關聯）

---

## 附錄：規格與開發計畫對照表

| 規格文件 | 對應開發計畫模組 | 對應 Phase |
|----------|------------------|------------|
| 12.1 頁型規格 | Experience Module | 1a |
| 12.2 內容模型規格 | Structured Content Module | 1a |
| 12.3 內容任務定義規格 | Content Definition Module | 1a |
| 12.4 AI 生成規格 | AI Content Assist Module | 1a |
| 12.5 事件字典 | Tracking & Event Module | 1a（埋點）/ 1b（啟用） |
| 12.6 意圖規則規格 | Intent Scoring Module | 1b |
| 12.7 表單與 RFQ 流程規格 | Conversion Orchestration Module | 1b |
| 12.8 整合規格 | Integration Module | 1b |
| 12.9 SEO 與 IA 規格 | Experience + Structured Content | 1a |
| 12.10 Entity 關聯規格 | Structured Content Module | 1a |
