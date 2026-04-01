# ForgeBase Legacy Site Intake 產品規格草案

## 1. 文件目的

本文件定義一個可附著在 ForgeBase 之上的新產品模組，目標是協助傳統型錄官網快速轉換為可導入 ForgeBase 的結構化網站資產，而不是直接複製舊網站。

此模組暫定名稱：Legacy Site Intake。

建議對外說法：

ForgeBase Launchpad：將舊網站快速轉為可上線、可導入、可持續優化的新站基礎。

---

## 2. 問題定義

ForgeBase 已具備以下能力：

1. 結構化內容實體管理：categories、products、applications、faq、certifications、capabilities、pages、assets。
2. PageBrief 工作流與 AI 內容生成。
3. 前台頁型模板、SEO 結構、RFQ、CTA、redirect 與後台管理能力。

目前缺口不在輸出端，而在輸入端。

對大多數傳統製造業或代理商官網而言，現況通常是：

1. 網站存在，但只是型錄式展示。
2. 內容分散在 HTML、圖片、PDF、表格與長段落中。
3. 網站資訊架構混亂，無法直接對應 ForgeBase 的內容模型。
4. 即使能爬到內容，也無法直接變成可發布、可追蹤、可轉換的新站。

因此需要一個 Intake 模組，先把舊站轉成可審核的結構化候選資料，再交給 ForgeBase 既有內容、SEO、AI 與發布流程處理。

---

## 3. 產品定位

### 3.1 一句話定位

Legacy Site Intake 是 ForgeBase 的舊站導入引擎，負責把舊時代型錄官網轉成 ForgeBase 可用的結構化內容、PageBrief 草稿與遷移資料。

### 3.2 不是什麼

本模組不是：

1. 萬用爬蟲平台。
2. 自動複製整站的網站下載器。
3. 泛用 AI 建站工具。
4. 通用 CMS 匯入器。

### 3.3 是什麼

本模組是：

1. 一個舊站探索與分類系統。
2. 一個多來源內容抽取與結構映射系統。
3. 一個導入審核台，讓營運人員快速決定哪些內容可導入、哪些需要重寫、哪些應捨棄。
4. 一個將舊站導入既有 ForgeBase 內容模型的前置層。

---

## 4. 核心商業價值

### 4.1 對 ForgeBase 的價值

1. 降低導入門檻，不再要求客戶先整理完整內容包才能啟動。
2. 明顯縮短從發現潛在客戶到啟動 Pilot 的時間。
3. 讓 ForgeBase 更適合處理典型的舊式型錄官網。
4. 讓導入流程可複製，而不依賴人工逐頁整理。

### 4.2 對客戶的價值

1. 不需要先重做全站，先用既有網站當資料來源即可啟動。
2. 可快速看見新站草圖、分類樹與 Pilot 範圍。
3. 可保留舊站的原始商業資料，但不必保留舊站的差結構與差體驗。

---

## 5. 使用情境

### 5.1 主要情境

1. 製造商有舊網站，但網站只是產品型錄，想快速升級。
2. 代理商或多品牌商想先選一條產品線做 Pilot。
3. ForgeBase 團隊要在提案前快速盤點網站，產出導入範圍與工時估算。

### 5.2 不建議情境

1. 客戶網站需要高度客製視覺設計專案。
2. 客戶網站內容大量依賴登入後資料，無法合法抓取。
3. 客戶沒有明確主打產品線，且拒絕提供任何補充資料。

---

## 6. 產品邊界與原則

1. 輸入以企業網址為起點，但網址不是唯一資料來源。
2. 所有抽取結果都必須以候選資料形式呈現，不可直接自動發布。
3. 任何 AI 內容生成仍必須服從既有 PageBrief 規則。
4. 模組必須輸出 redirect 建議，以保留舊站 SEO 資產。
5. 模組必須支援「只導入一條產品線」而不是預設全站導入。
6. 模組不應把舊網站的 URL 結構、前端樣式或舊 CMS 結構視為新站真相。

---

## 7. MVP 目標

### 7.1 輸入

MVP 允許以下輸入來源：

1. 公司官網網址。
2. sitemap.xml 或站內導覽頁。
3. PDF 型錄、規格書、能力簡報。
4. 選填：產品 Excel 或型號清單。
5. 人工補充：主打產品線、主打市場、主 CTA。

### 7.2 輸出

MVP 必須能輸出：

1. 網站頁型盤點。
2. 產品線與分類候選樹。
3. 產品、應用、FAQ、認證、資產候選資料。
4. 建議導入範圍與 Pilot 頁面清單。
5. redirect 建議表。
6. 可轉入既有 ForgeBase seed/import 流程的結構化 JSON。
7. PageBrief draft 建議。

### 7.3 不在 MVP 內

1. 登入後網站抓取。
2. 視覺版型自動擬真重建。
3. 完整多語自動翻譯工作流。
4. 完全無人工審核的自動發布。

---

## 8. 使用流程

### 8.1 Step 1：建立 Intake Project

營運或顧問建立導入專案，填寫：

1. 客戶名稱。
2. 主網址。
3. 公司類型：製造商 / 代理商 / 混合。
4. 目標語系。
5. 導入模式：Pilot / 部分導入 / 全站導入。

### 8.2 Step 2：網站探索

系統執行探索：

1. 抓首頁與主導覽。
2. 抓 sitemap、robots、代表頁。
3. 建立 URL inventory。
4. 標記頁型：company、category、product、application、faq、contact、resource、other。

### 8.3 Step 3：內容抽取

對候選頁與檔案執行抽取：

1. 產品名稱、型號、規格、品牌。
2. 應用場景、痛點、解法片段。
3. FAQ 與常見問答段落。
4. 認證、能力、資產下載連結。
5. 聯絡資訊與現有 CTA 路徑。

### 8.4 Step 4：結構映射

系統將候選內容映射到 ForgeBase 既有模型：

1. ProductCategory。
2. Product。
3. Application。
4. FAQItem。
5. Certification。
6. Capability。
7. ContentAsset。
8. Redirect。

### 8.5 Step 5：審核與聚焦

營運人員在審核台決定：

1. 哪些頁面與產品線應納入 Pilot。
2. 哪些候選實體要保留、合併、捨棄。
3. 哪些欄位可信、哪些需要人工補強。
4. 哪些舊 URL 要保留 redirect。

### 8.6 Step 6：建立 PageBrief Draft

系統依審核結果生成 draft briefs：

1. category briefs。
2. product briefs。
3. application briefs。
4. faq briefs。
5. certification briefs。

### 8.7 Step 7：匯入 ForgeBase

審核後匯出為結構化 seed，走既有匯入與內容發布流程。

---

## 9. 功能模組拆解

### 9.1 Site Discovery

功能：

1. 網站首頁抓取。
2. sitemap 發現。
3. 導覽解析。
4. URL 去重與規模估算。
5. 頁型分類。

MVP 成功標準：

1. 可在 10 分鐘內產出完整 URL inventory。
2. 至少 80% 頁面能被分到合理頁型。

### 9.2 Content Extraction

功能：

1. HTML 主要內容抽取。
2. 表格規格抽取。
3. 圖片 alt、標題、下載連結抽取。
4. PDF 檔案 metadata 與文字抽取。

MVP 成功標準：

1. 能從典型型錄頁抽出產品名稱、型號與至少一組規格。
2. 能識別 contact 頁與下載型資產。

### 9.3 Entity Mapping

功能：

1. category 候選聚類。
2. product 候選實體建立。
3. FAQ、application、certification 候選生成。
4. asset 與 entity 關聯建議。

MVP 成功標準：

1. 輸出格式能對齊既有 import plan。
2. 實體可被人工快速確認與修正。

### 9.4 Review Console

功能：

1. 顯示候選實體與來源證據。
2. 標示置信度與缺漏欄位。
3. 可一鍵接受、合併、忽略、改寫。
4. 可設定 Pilot 導入範圍。

MVP 成功標準：

1. 一位營運可在 1 小時內完成小型網站的第一輪審核。

### 9.5 Brief Draft Generator

功能：

1. 依已確認的 entity 與導入策略自動建立 PageBrief 草稿。
2. 自動帶入 related_entity_type / related_entity_id。
3. 自動建議 primary keyword、buyer stage、notes 與 CTA key。

MVP 成功標準：

1. 每個已選定 Pilot 頁面都能長出一份可編修的 brief 草稿。

### 9.6 Redirect Planner

功能：

1. 舊 URL 對新 URL 建議。
2. 偵測明顯的 redirect 風險或衝突。
3. 匯入既有 redirects API。

MVP 成功標準：

1. 可對 80% 以上舊站核心頁給出合理 redirect 建議。

---

## 10. 建議資料模型

### 10.1 新增模型

建議新增以下資料模型：

#### IntakeProject

用途：一個客戶網站導入專案。

核心欄位：

1. id
2. account_id
3. name
4. root_url
5. company_type
6. intake_mode
7. target_locales
8. status
9. created_by
10. created_at
11. updated_at

#### IntakeSource

用途：記錄每個輸入來源。

核心欄位：

1. id
2. intake_project_id
3. source_type: url / sitemap / pdf / spreadsheet / note
4. source_value
5. upload_asset_id
6. status

#### IntakeUrlCandidate

用途：網站探索後的 URL 候選清單。

核心欄位：

1. id
2. intake_project_id
3. url
4. page_type_guess
5. title
6. parent_url
7. http_status
8. selected_for_extraction
9. confidence_score

#### IntakeEntityCandidate

用途：抽取出的候選內容實體。

核心欄位：

1. id
2. intake_project_id
3. source_url_id
4. entity_type
5. raw_payload
6. normalized_payload
7. confidence_score
8. review_status
9. mapped_entity_id

#### IntakeRedirectCandidate

用途：舊站 URL 到新站 URL 的建議對應。

核心欄位：

1. id
2. intake_project_id
3. from_path
4. suggested_to_path
5. reasoning
6. review_status
7. redirect_id

#### IntakeBriefCandidate

用途：由確認過的 entity 生成的 brief 草稿。

核心欄位：

1. id
2. intake_project_id
3. entity_type
4. entity_candidate_id
5. suggested_payload
6. review_status
7. page_brief_id

### 10.2 直接對接既有模型

本模組不應重做既有內容模型，而應在審核通過後直接寫入或呼叫既有流程：

1. ProductCategory
2. Product
3. Application
4. FAQItem
5. Certification
6. Capability
7. ContentAsset
8. PageBrief
9. Redirect

---

## 11. 與現有系統整合點

### 11.1 API 整合

可直接沿用既有內容 CRUD 與 redirects API。

建議新增 intake 專屬 API：

1. POST /api/v1/intake/projects
2. POST /api/v1/intake/projects/{id}/discover
3. POST /api/v1/intake/projects/{id}/extract
4. GET /api/v1/intake/projects/{id}/urls
5. GET /api/v1/intake/projects/{id}/entities
6. PATCH /api/v1/intake/entities/{id}
7. POST /api/v1/intake/projects/{id}/generate-briefs
8. POST /api/v1/intake/projects/{id}/export-seed
9. POST /api/v1/intake/projects/{id}/commit

### 11.2 Admin 整合

建議在 admin 新增一個 Intake 區塊：

1. Intake Projects 列表。
2. Site Inventory 檢視。
3. Entity Review Console。
4. Redirect Review。
5. Brief Draft Review。
6. Commit to ForgeBase 操作。

### 11.3 Web 整合

前台無需直接暴露 intake 功能。

前台唯一需要的間接整合為：

1. 新導入內容發布後能直接套用既有頁型。
2. redirect 規則能被既有 middleware resolve。

---

## 12. 與既有 import 流程的關係

此模組的輸出格式應直接兼容既有 demo seed/import 思路：

1. pages.json
2. categories.json
3. products.json
4. applications.json
5. certifications.json
6. capabilities.json
7. faq-items.json
8. comparison-topics.json
9. assets.json
10. relationships.json

也就是說，Legacy Site Intake 應該是既有 import pipeline 的前置產生器，而不是替代品。

---

## 13. king-a 試點判斷

### 13.1 為何適合作為 Pilot

https://king-a.com.tw/ 是典型舊式型錄站，特徵包含：

1. 內容主體為靜態頁、文章頁、產品卡片與聯絡頁。
2. CTA 主要集中在通用聯絡方式，轉換路徑單一。
3. 產品與品牌資訊存在，但結構仍偏展示式。
4. 網站規模不大，適合測試半自動導入流程。

### 13.2 對 Intake 模組的驗證價值

此案例可驗證：

1. 頁型分類是否能辨識 page 與 article 類內容。
2. 多品牌與代理商網站是否需要先做導入範圍收斂。
3. 抽取後是否能聚焦在單一產品線，例如 Panasonic 焊接方案。

### 13.3 建議 Pilot 範圍

只先導入單一主題線，不建議全站照搬：

1. Panasonic 焊接機械手臂與周邊。
2. 對應應用頁與常見問題。
3. 對應 RFQ/Contact 流程。

---

## 14. 成功指標

### 14.1 產品指標

1. 從輸入網址到產出第一版 site inventory，不超過 10 分鐘。
2. 從網址到可審核的 candidate entities，不超過 30 分鐘。
3. 小型網站第一輪審核完成時間低於 2 小時。
4. Pilot 導入前置工時比純人工整理降低 50% 以上。

### 14.2 商業指標

1. 可縮短提案前盤點時間。
2. 可提升 Pilot 啟動率。
3. 可降低客戶對「重建新網站很耗時」的抗拒。

---

## 15. 主要風險

1. 抽取正確率不足，造成營運審核負擔過高。
2. 對代理商或多品牌網站未先收斂範圍，導致導入失焦。
3. 圖片與 PDF 品質太差，造成規格抽取不完整。
4. 產品名稱、型號或品牌混用，導致 entity 去重困難。
5. 若產品邊界失守，容易把 ForgeBase 做成一般 CMS 匯入器。

---

## 16. 開發建議順序

### Phase A：內部導入工具

1. 網址探索。
2. URL inventory。
3. 基本頁型分類。
4. 候選 entity 抽取。
5. JSON 匯出。

### Phase B：Admin 審核台

1. Entity review。
2. Redirect review。
3. Brief draft review。
4. Commit 到既有內容實體。

### Phase C：半產品化

1. PDF 與 spreadsheet 匯入。
2. 更多頁型支援。
3. 置信度與差異提示。
4. 多語導入支援。

### Phase D：正式產品化

1. Onboarding wizard。
2. 客戶自助上傳與補件。
3. 導入狀態追蹤與估工面板。

---

## 17. 結論

ForgeBase 確實可以從目前討論中萃取出一個新的明確需求，而且這個需求是合理的產品延伸。

最適合的方向不是再做一套新建站系統，而是新增一個 Intake 模組，專門把舊站轉成 ForgeBase 可用的結構化資產與 brief 草稿。

這樣做有三個好處：

1. 不破壞 ForgeBase 作為成長系統的產品邊界。
2. 最大化利用既有內容模型、PageBrief、AI 與 redirect 能力。
3. 直接提升實際導入效率與商業可複製性。