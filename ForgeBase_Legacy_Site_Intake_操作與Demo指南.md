# ForgeBase Legacy Site Intake 操作與 Demo 指南

本文件提供 Legacy Site Intake 的實際操作流程，適用於內部 demo、客戶導入試跑，以及正式導入前的審核作業。

---

## 1. 功能定位

Legacy Site Intake 的目的不是直接複製舊網站，而是把既有官網、型錄站或 PDF 規格資料，轉成 ForgeBase 可審核、可提交、可延伸成正式內容的結構化輸入。

目前 commit 完成後可寫入：

- ProductCategory
- Product
- Application
- Certification
- FAQItem
- Redirect
- PageBrief

同時會補上以下關聯：

- Product -> Application
- Product -> Certification
- Product -> FAQ
- Application -> FAQ

---

## 2. 導入前準備

最低需要提供：

- 既有網站網址
- 目標語系，例如 `zh-TW` 或 `en`
- 可登入 admin 的帳號

建議另外準備：

- 產品主分類邏輯
- 是否有既有 slug / SEO 路徑要保留
- 哪些內容不應導入，例如招募頁、法務頁、純新聞頁
- 是否允許直接 publish 到正式前台

---

## 3. 標準操作流程

### Step 1. 建立 intake project

在 admin 後台建立 project，填入：

- `project_name`
- `source_url`
- `locale`

建議 `locale` 直接填前台正式用值，例如：

- `zh-TW`
- `en`

系統會在正式 commit 時自動正規化 locale，避免 staging 值與正式內容值不一致。

### Step 2. 執行 discover

`discover` 會做兩件事：

- 爬取站內 HTML / PDF
- 建立 URL candidates 並分類頁型

審核重點：

- `product` 是否真的為產品 / 型號頁
- `category` 是否為分類頁或產品集合頁
- `application` 是否為應用情境頁
- `faq` 是否為問答頁
- `resource` 是否其實只是 PDF 或資源頁

### Step 3. 執行 extract

`extract` 會從已接受或待審 URL 中抽出：

- entity candidates
- redirect candidates
- PageBrief drafts

此階段產物仍屬 staging，尚未進正式內容表。

### Step 4. 審核 URL / entity / redirect / brief

建議審核順序：

1. 先處理 URL candidates
2. 再處理 entity candidates
3. 最後確認 redirects 與 briefs

entity 審核建議：

- `product`: 必要欄位至少要有 `product_name`，若有穩定型號則保留 `model_number`
- `category`: 名稱應能代表正式分類，不要把整段首頁文案直接當分類名
- `application`: 應該描述應用場景，而不是產品名重複包裝
- `certification`: 需確認是否真的是認證，而不是產品規格段落
- `faq`: 確認 question / answer 配對是否完整且可公開

redirect 審核建議：

- 只接受有明確對應新內容的路徑
- 舊首頁 `/` 不建立 redirect candidate
- 若舊路徑只是追蹤、活動頁或暫時頁，可直接略過

brief 審核建議：

- 標題要貼近最終頁面意圖
- `primary_keyword` 不要只剩品牌名
- `target_slug` 應符合最終內容路徑

---

## 4. Commit 後實際會發生什麼

當 project 狀態為 `ready_for_review` 且審核完成後，執行 `commit` 會：

1. 把已接受 entity candidates 寫入正式內容表
2. 自動 publish 新建內容
3. 依內容關聯建立 product/application/certification/faq link
4. 把 accepted redirect candidates 寫入 `redirects`
5. 把 accepted brief candidates 寫入 `page_briefs`
6. 將 brief 綁回已提交的正式 entity

補充：

- 若 redirect `from_path` 已存在，系統會更新既有 redirect，而不是重複插入
- 若同名 / 同 slug / 同型號資料已存在，系統會盡量 merge，而不是盲目建立重複內容
- FAQ 一個 entity candidate 可能包含多個 QA pair，commit 時會拆成多筆 FAQItem

---

## 5. Demo 建議講法

向客戶 demo 時，建議不要把它說成「爬蟲工具」，而是說成：

`ForgeBase 可把既有網站轉成可審核、可編修、可導入的成長型內容資產。`

建議 demo 順序：

1. 建立 project
2. 執行 discover，展示 URL 自動分類
3. 執行 extract，展示產品 / FAQ / redirect / brief 自動生成
4. 在 admin 審核幾筆 entity
5. 執行 commit
6. 到內容後台或 API 驗證資料已進正式表
7. 說明後續可再用 AI 內容生成補全頁面

---

## 6. Demo 驗證清單

完成 commit 後，至少驗證以下項目：

- category 已出現在正式 categories 列表
- product 已出現在正式 products 列表
- application / certification / faq 可在正式 API 查到
- redirect resolve 能找到新路徑
- PageBrief 已帶有 `related_entity_type` 與 `related_entity_id`
- 前台若讀取 published content，可查到新內容

建議驗證 API：

```bash
GET /api/v1/content/categories?status=published&locale=zh-TW
GET /api/v1/content/products?status=published&locale=zh-TW
GET /api/v1/content/applications?status=published&locale=zh-TW
GET /api/v1/content/certifications?status=published&locale=zh-TW
GET /api/v1/content/faqs?status=published&locale=zh-TW
GET /api/v1/content/redirects/resolve?path=/old/path
```

---

## 7. 已知限制

- 目前關聯建立以名稱 / 型號比對為主，不是完整語意對齊
- 單一 FAQ entity 可能拆成多筆 FAQItem，但 `committed_entity_id` 只會記第一筆
- 若原站結構極亂，仍需要人工審核 URL 與 entity 才適合 commit
- image / asset 尚未完整寫入正式 content asset 體系

---

## 8. 建議正式導入策略

建議分兩輪：

### 第一輪

- 匯入 category / product / application / faq / certification
- 建立 redirect
- 建立 briefs

### 第二輪

- 補寫 AI 生成頁面
- 補齊 SEO title / meta description
- 補整理產品圖片與資產
- 補人工優化分類與關聯

這樣能先把舊站資料安全落地，再做內容品質提升，而不是一次把所有事情混在同一輪處理。