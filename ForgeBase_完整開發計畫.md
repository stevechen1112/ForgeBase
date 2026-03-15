# ForgeBase — 外銷製造商官網成長系統 完整開發計畫

## 1. 文件目的

本文件將前述討論收斂為可供產品、設計、工程、營運與商務團隊共同使用的開發計畫。

本產品不是單純網站建置服務，也不是泛用型 AI 內容工具，而是一套專為中小型外銷製造商打造的官網型成長系統，目標是讓官網具備以下三項核心能力：

1. Capture：讓產品、應用、FAQ、比較與規格頁有機會被搜尋到、被理解、被引用。
2. Intent：讓所有頁面行為都能被辨識為意圖訊號，而不只是停留在 GA 流量數字。
3. Conversion：讓詢價、RFQ、再行銷、nurture 與業務跟進直接接在網站裡。

---

## 2. 產品定位

### 2.1 一句話定位

這是一套專為中小型外銷製造商打造的官網成長系統，透過 Capture、Intent、Conversion 三層架構，讓官網不再只是產品型錄，而是能持續帶來搜尋曝光、辨識高意圖買家並推進詢價與業務跟進的商務前台。

### 2.2 核心主張

我們不是幫製造商做漂亮官網，而是把官網變成能捕捉需求、辨識意圖、推進詢價與業務跟進的實用型成長系統。

### 2.3 目標客群

1. 台灣或亞洲中小型外銷製造商
2. 官網結構簡單但數位成長機制薄弱的企業
3. 主要依賴展會、業務、既有客戶、代理商接單的企業
4. 產品與出口能力成熟，但網站無法有效承接搜尋與詢盤的企業
5. 需要多語產品內容、應用頁與詢價流程優化的企業

### 2.4 不做什麼

本產品不以以下需求為核心：

1. 純品牌形象官網設計
2. 高度客製視覺網站專案
3. 泛用型 AI 文案工具
4. ERP、MES、PLM 等企業內部系統
5. 複雜會員中心或經銷商後台
6. 單純流量報表或代理操作服務

---

## 3. 問題定義

### 3.1 市場現況

中小型外銷製造商的網站通常只包含：

1. 首頁
2. 產品分類頁
3. 產品詳頁
4. 應用頁
5. FAQ、比較、規格頁
6. 認證與能力頁
7. RFQ 或詢價頁
8. Contact 與必要 About

這類網站規模不大，但往往存在以下問題：

1. 內容與頁面多為靜態型錄，無法有效承接搜尋需求
2. 缺乏以 buyer intent 為導向的內容規劃
3. 無法辨識哪些訪客、哪些內容、哪些產品真正有商業意圖
4. 詢價流程缺乏分流、追蹤與業務交接機制
5. 業務與行銷間沒有以頁面行為為基礎的共同語言

### 3.2 要解決的核心斷裂

1. Search 到內容之間的斷裂：頁面無法穩定被搜尋到與理解
2. 內容到意圖之間的斷裂：有流量但無法判斷誰值得跟進
3. 意圖到詢價之間的斷裂：有興趣但無法被有效推進到 RFQ 與業務接手

### 3.3 導入彈性說明

本產品的完整產品邊界是商業核心全站，但導入時可以分階段：

1. 標準導入：直接交付商業核心站點，適合網站老舊或準備重建的客戶。
2. 過渡導入：先用子網域或局部頁面接管最接近詢盤的頁面，再逐步擴展。適合短期不想大改、但願意先驗證成效的客戶。
3. 嵌入式導入：先在現有網站上插入表單、CTA、追蹤元件，驗證效果後再決定擴大。

產品設計以標準導入為主幹，但過渡與嵌入式導入能降低客戶第一次採用門檻。

---

## 4. 產品原則

1. 官網是三層系統的主體承載介面。對中小製造商而言，官網即商業核心前台，三層能力原生建在官網之上，網站不是附加品。
2. 頁面必須同時服務 Capture、Intent 或 Conversion 中至少一項，不做純裝飾性頁面。
3. 每一頁內容都必須先定義目的，才允許被 AI 生成。
4. 實用型體驗優先於品牌型美學。
5. 所有關鍵行為都應轉化為 first-party event，而不是只依賴 GA。
6. 系統必須支援 account-centric/B2B 思維，而不只以單一 lead 或 cookie 為中心。
7. 第一階段就必須形成從頁面到 inquiry 的最小閉環。
8. AI 是加速器，不是策略替代者。

---

## 5. 三層產品架構

### 5.1 Capture Layer

目標：讓產品、應用、FAQ、比較與規格頁有機會被搜尋到、被理解、被引用。

主要能力：

1. 內容策略地圖（Content Strategy Map）
2. 頁型模板系統
3. 內容定義與頁面 brief
4. AI 協助內容生成
5. SEO 與 GEO 基本配置
6. Information Architecture 與 taxonomy 管理
7. Entity 與 Structured Data 輸出
8. 站內連結與 CTA 佈局
9. 多語頁面輸出
10. 技術 SEO 基礎設施

內容策略地圖說明：

在建立個別頁面之前，必須先完成全局性的內容策略地圖。這張地圖定義：

1. 目標市場與優先序（國家、區域、產業）
2. 目標客群與 buyer persona（OEM 採購、工程師、代理商、維修端等）
3. 意圖分層（教育型、比較型、替代型、規格型、採購型）
4. 產品與應用優先序（高單價、高頻、高差異化產品先做）
5. 頁面規劃矩陣（哪些頁型 × 哪些產品 × 哪些意圖 × 哪些市場先上線）
6. CTA 與轉換路徑規劃（每類頁面對應不同 CTA，不是全部都叫聯絡我們）

個別頁面的 page brief 由這張策略地圖展開，確保每一頁都有明確的商業目的，而不是先產內容再期待流量。

核心頁型：

1. 首頁
2. 產品分類頁
3. 產品詳頁
4. 應用頁
5. FAQ/比較/規格頁
6. 認證/能力頁

### 5.2 Intent Layer

目標：讓所有頁面行為都能被辨識成意圖訊號，而不是只有 GA 流量數字。

主要能力：

1. first-party event tracking
2. 訪客與 session 管理
3. 匿名與已知身份關聯
4. 公司識別與帳戶關聯
5. audience tagging
6. rule-based intent scoring

### 5.3 Conversion Layer

目標：讓詢價、RFQ、再行銷、nurture 與業務跟進直接接在網站裡。

再行銷是本層最重要的轉換驅動力之一。工業 B2B 買家極少在第一次造訪就轉換，因此系統必須原生支援兩種再行銷路徑：

1. 匿名高意圖訪客再行銷：透過 Intent Layer 辨識出的高意圖匿名訪客，依其瀏覽產品類型、應用場景與意圖強度，自動建立再行銷受眾並同步至 Google Ads、Meta、LinkedIn 等平台，投放與其意圖高度相關的廣告。
2. 已留資料訪客跟進：透過表單、RFQ、下載等行為留下資料的訪客，依其 persona、產品興趣與意圖階段，進入對應的 email nurture 流程或直接觸發業務主動跟進。

主要能力：

1. CTA 與表單策略
2. RFQ 流程與分流
3. 匿名訪客再行銷受眾建立與平台同步
4. 已知訪客 email/nurture 自動化
5. sales alert 與業務跟進任務
6. CRM 同步
7. conversion insight 與歸因追蹤

---

## 6. RD 可開發模組規劃

以下模組是產品模組，不是前端頁面分類。

### 6.1 Experience Module

目的：管理前台頁面體驗與標準化頁型。

子功能：

1. 頁型模板系統
2. 頁面區塊組裝器
3. 多語切換與輸出
4. SEO metadata 配置
5. CTA 元件系統
6. 響應式與效能優化
7. 技術 SEO 基礎設施

技術 SEO 基礎設施（Phase 1 必做）：

1. URL 結構規則（依分類/產品/應用層級自動生成）
2. canonical 自動管理
3. XML sitemap 自動生成與更新
4. robots.txt 與 noindex 基本策略
5. breadcrumb 自動生成
6. 圖片 SEO（alt text、檔名規則、lazy loading）
7. Core Web Vitals 基準確保
8. 基礎 structured data 輸出（Product、FAQPage、BreadcrumbList）

技術 SEO 進階（Phase 2）：

1. hreflang 多語架構
2. faceted navigation control
3. PDF 與文件索引策略
4. pagination / parameter handling
5. 完整 entity-level schema mapping

第一階段頁型：

1. 首頁
2. 產品分類頁
3. 產品詳頁
4. 應用頁
5. FAQ/比較/規格頁
6. 認證/能力頁
7. RFQ/詢價頁
8. Contact/About

### 6.2 Content Definition Module

目的：定義每一頁存在的商業目的與內容任務。

每個 page brief 至少包含：

1. 頁面類型
2. 目標市場
3. 目標客群
4. 搜尋意圖類型
5. 主要主題與關鍵字群
6. 對應產品或應用
7. 證據素材
8. 主要 CTA
9. 次要 CTA
10. 語言與語氣
11. 頁面目標 KPI

這個模組是 AI 生成前的必要前置。

### 6.3 AI Content Assist Module

目的：依據頁面 brief 與結構化資料產出內容初稿，加速 Capture Layer 上線。

功能邊界：

1. 根據頁型模板生成初稿
2. 根據產品規格與應用資料補全文案
3. 生成 SEO title、meta description、段落骨架
4. 生成 FAQ 建議與比較面向
5. 生成 CTA 文案建議
6. 支援英文優先，多語為後續擴展
7. 保留人工審核與修訂流程

不做：

1. 自由 prompt 型無約束創作
2. 一鍵全站自動發布
3. 無資料來源支撐的技術文案生成

### 6.4 Structured Content Module

目的：作為頁面與 AI 生成的結構化資料底座。

核心資料物件：

1. Product
2. Product Category
3. Application
4. FAQ
5. Comparison Topic
6. Certification
7. Capability
8. CTA
9. Page Brief
10. Content Asset

Entity 關聯模型：

每個 entity 不是孤立存在，而是透過關聯形成知識網絡，這是 SEO 與 AI 搜尋引用的關鍵：

1. Product → 屬於哪個 Product Category
2. Product → 適用哪些 Application
3. Product → 有哪些 Certification
4. Product → 有哪些 FAQ
5. Product → 可與哪些產品比較（Comparison Topic）
6. Product → 有哪些替代料號關係
7. Application → 適用哪些產業
8. Application → 對應哪些 FAQ
9. Certification → 適用哪些市場/國家

這些關聯會直接影響：

1. 內連自動化規則
2. structured data 輸出
3. 相關頁推薦
4. AI 內容生成時的上下文補充
5. GEO/AI 搜尋引用時的知識可抽取性

### 6.5 Tracking & Event Module

目的：建立產品自有的 first-party event model。

核心事件：

1. page_view
2. category_view
3. product_view
4. application_view
5. faq_expand
6. comparison_view
7. spec_download
8. certification_view
9. cta_click
10. form_start
11. form_submit
12. rfq_start
13. rfq_submit
14. return_visit
15. session_depth_reached

事件屬性建議：

1. page_type
2. page_id
3. product_id
4. application_id
5. audience_tag
6. intent_category
7. session_id
8. visitor_id
9. account_id
10. locale
11. traffic_source
12. campaign_id

### 6.6 Identity & Audience Module

目的：將匿名訪客與已知名單逐步整合為可操作受眾。

Phase 1 功能：

1. visitor ID 與 session 管理
2. cookie/first-party identity 關聯
3. 表單後身份合併
4. contact 建立與更新
5. audience tag 管理
6. remarketing audience 建立

Phase 2 才加入：

1. 第三方公司識別資料源介接
2. account 建立與關聯
3. account enrichment

### 6.7 Intent Scoring Module

目的：以規則引擎建立初版商業意圖判斷。

MVP 採用 rule-based scoring：

1. 看產品頁：+3
2. 看應用頁：+4
3. FAQ/比較頁互動：+6
4. 規格下載：+8
5. RFQ 開始：+15
6. RFQ 送出：+30
7. 7 天內回訪：+6
8. 同 session 多頁深度瀏覽：+5

功能：

1. 分數規則設定
2. 分數累積與衰減
3. intent stage 判定
4. audience classification
5. trigger 條件輸出

### 6.8 Conversion Orchestration Module

目的：將高意圖流量推進為可跟進商機。

功能：

1. CTA 規則
2. 表單引擎
3. RFQ workflow
4. routing 規則
5. sales alert
6. nurture trigger
7. remarketing audience sync
8. conversion status tracking

### 6.9 Integration Module

目的：與外部系統同步關鍵資料。

Phase 1 建議整合：

1. GA4
2. HubSpot 或通用 webhook
3. Google Ads Audience
4. Meta Audience
5. LinkedIn Audience

Phase 2 之後可擴展：

1. Salesforce
2. Email service provider
3. CRM 雙向同步
4. 公司識別資料源

### 6.10 Admin & Insight Module

目的：提供營運後台與決策儀表板。

功能：

1. 頁面管理
2. content brief 管理
3. AI 生成與審核流程
4. intent dashboard
5. high-intent page dashboard
6. product/application performance dashboard
7. conversion dashboard
8. integration status monitor

---

## 7. 系統架構原則

### 7.1 Phase 1 採單體應用架構

MVP 階段不採微服務，以前後端分離的單體應用為主。原因：

1. 早期基礎設施成本不應壓佔開發時間
2. 模組間邊界尚未穩定，強拆服務會增加不必要的複雜度
3. 先讓功能跑通，再依真實負載與延展需求決定拆分時機

### 7.2 Phase 2 以後可考慮服務化拆分

當產品穩定且客戶量成長後，可依以下 bounded contexts 拆分：

1. Experience Service：頁面 rendering、頁型模板、SEO、CTA、多語
2. Content Service：結構化內容、page brief、內容版本、AI 生成資料
3. Data Service：事件收集、訪客身份、audience、intent scoring
4. Flow Service：表單/RFQ、routing、sales alert、nurture、workflow
5. Integration Service：CRM、ad platform、analytics、webhook/API

---

## 8. 核心資料模型

### 8.1 Business Entities

1. Account：公司帳戶
2. Contact：聯絡人
3. Visitor：匿名或已知訪客
4. Session：單次造訪會話

### 8.2 Content Entities

1. Product
2. ProductCategory
3. Application
4. FAQItem
5. ComparisonTopic
6. Certification
7. Capability
8. Page
9. PageBrief
10. ContentAsset
11. CTA

### 8.3 Signal & Workflow Entities

1. Event
2. IntentSignal
3. IntentScore
4. Audience
5. ConversionObject
6. RFQRequest
7. Workflow
8. Notification
9. IntegrationJob

---

## 9. 使用者角色

### 9.1 Phase 1 角色

#### Admin

管理系統設定、權限、整合、主要規則。

#### Marketing Manager

管理內容策略地圖、頁面 brief、CTA、受眾與再行銷規則。同時可兼內容編輯與審核。

#### Sales User

查看高意圖名單、RFQ、提醒與跟進資訊。

### 9.2 Phase 2 以後可擴展角色

1. Content Editor：專職編修 AI 內容、管理頁面文案、發佈內容
2. Operator / Agency User：協助客戶營運頁面、內容與廣告受眾同步

---

## 10. MVP 定義

### 10.1 MVP 目標

建立從頁面上線到 inquiry/詢價形成的最小閉環，並驗證以下假設：

1. 標準化頁型可以快速構建中小製造業官網
2. AI 協助內容生成可以有效降低上站成本
3. first-party event + rule-based scoring 能有效找出高意圖訪客
4. 表單/RFQ/受眾同步可以形成商業可用的 conversion loop

### 10.2 MVP 必做功能

1. 標準化頁型系統
2. 結構化內容模型（含 entity 關聯）
3. page brief 定義流程
4. AI 協助內容生成
5. 技術 SEO 基礎設施（URL 結構、canonical、sitemap、robots、breadcrumb、基礎 structured data）
6. SEO metadata 管理
7. 內連自動化規則
8. first-party event tracking
9. visitor/session 基礎識別
10. rule-based intent scoring
11. RFQ/詢價表單與分流
12. Google Ads 或 HubSpot 的至少一種同步
13. 基本 dashboard（含內容成效回饋）

### 10.3 MVP 不做功能

1. 自由 prompt 型 AI writer
2. 複雜 CRM 雙向同步
3. 預測型 AI intent scoring
4. 高度個人化 CTA 引擎
5. 多國複雜權限與 enterprise workflow
6. ERP 或後台系統整合
7. 大量自訂頁型

---

## 11. 開發階段規劃

### Phase 1a：頁面與內容底座

目標：先讓網站能上線、內容能生成、頁面能被搜尋。

範圍：

1. Experience Module 基本頁型
2. Structured Content Module（含 entity 關聯模型）
3. Content Definition Module（含內容策略地圖工具）
4. AI Content Assist Module
5. 技術 SEO 基礎設施（URL 結構、canonical、sitemap、robots、breadcrumb、基礎 structured data）
6. 內連自動化規則
7. 發佈機制

交付標準：

1. 頁型模板可用
2. 內容模型可建資料，entity 關聯可設定
3. Page Brief 建立流程可運作
4. AI 可依 brief 生成初稿
5. 頁面可發佈上線
6. URL 結構、canonical、sitemap、robots 自動運作
7. 基礎 structured data 可輸出（Product、FAQPage、BreadcrumbList）
8. 內連依 entity 關聯自動生成

### Phase 1b：事件、意圖與轉換閉環

目標：讓網站不只是靜態頁面，而是能追蹤行為、辨識意圖、收詢盤、做再行銷。

範圍：

1. Tracking & Event Module
2. Identity & Audience Module（Phase 1 範圍）
3. 基礎 Intent Scoring Module
4. RFQ/詢價表單與分流
5. 基礎再行銷受眾同步
6. 基礎整合（GA4 + HubSpot 或 webhook）
7. 基礎 dashboard（含內容成效回饋）

交付標準：

1. 事件可收集且可查詢
2. 訪客意圖可評分
3. RFQ 可提交且可分流通知
4. 再行銷受眾可同步至廣告平台
5. dashboard 可看到哪些頁帶來流量、哪些頁有高意圖互動、哪些頁帶來 RFQ

### Phase 1 關鍵驗證

1. 客戶官網是否能在合理時間內上線（頁面上線而非完整系統交付）
2. AI 協助內容生成是否能有效降低內容建置成本
3. first-party event + rule-based scoring 能否找出高意圖訪客
4. 表單/RFQ/受眾同步能否形成商業可用的詢盤閉環
5. 內容成效回饋能否驗證內容策略是否正確

### Phase 2：Growth Operations

目標：擴展 intent、audience 與 conversion orchestration 的能力。

範圍：

1. audience segmentation 強化
2. 第三方公司識別與 account enrichment
3. email/nurture trigger
4. 進階 remarketing sync
5. 更完整 CRM integration
6. 多語內容管理
7. 進階內容成效回饋與優化建議
8. 進階 SEO 架構（hreflang、faceted navigation、PDF 索引、完整 entity-level schema）
9. SEO 診斷儀表板（indexation、CTR、cannibalization、模板層級排名分析）

### Phase 3：Intelligence Layer

目標：導入 AI 與模型化能力，提高自動化與決策品質。

範圍：

1. AI RFQ 分析與回覆草稿
2. 智慧內容優化建議
3. 預測型 intent scoring
4. CTA 與 workflow 推薦
5. account-level insight

---

## 12. 需先完成的產品規格文件

在 RD 正式開發前，PM 必須先補齊以下規格。

### 12.1 頁型規格

每種頁面需要定義：

1. 固定區塊
2. 可配置欄位
3. CTA 位置
4. SEO 欄位
5. 可追蹤事件點

### 12.2 內容模型規格

每個 entity 的欄位、驗證規則、關聯關係。

### 12.3 內容任務定義規格

Page Brief 的欄位、必填條件、審核流程。

### 12.4 AI 生成規格

1. 輸入欄位
2. 輸出格式
3. 支援頁型
4. 編修與覆寫方式
5. 人工審核狀態

### 12.5 事件字典

1. 事件名稱
2. 觸發條件
3. 屬性欄位
4. 事件來源
5. 儲存格式

### 12.6 意圖規則規格

1. 分數規則
2. 分數衰減
3. stage 門檻
4. 觸發動作條件

### 12.7 表單與 RFQ 流程規格

1. 欄位定義
2. 驗證規則
3. 路由規則
4. 通知規則
5. CRM 映射

### 12.8 整合規格

1. GA4 事件映射
2. CRM 欄位映射
3. Ads audience sync 邏輯
4. Webhook payload

### 12.9 SEO 與 IA 規格

1. URL 結構規則（分類/產品/應用/FAQ 各層規則）
2. taxonomy 定義（產品分類、應用分類、產業分類、規格屬性、認證類型）
3. 內連規則（哪些 entity 關聯應自動產生內連）
4. canonical 規則（哪些情況自動加 canonical）
5. structured data mapping（哪些頁型輸出哪些 schema）
6. robots/noindex 規則（哪些頁不索引）
7. sitemap 分組規則（依頁型或語言分檔）
8. 圖片 SEO 規則（alt text 生成規則、檔名規則）

### 12.10 Entity 關聯規格

1. Product 與 Category/Application/Certification/FAQ/Comparison 的關聯定義
2. 替代料號關係定義
3. Application 與產業的關聯定義
4. 關聯對應的內連、schema、推薦邏輯

---

## 13. 關鍵 KPI

### 13.1 Capture KPI

1. 目標頁面上線數
2. 被索引頁數
3. 非品牌自然流量
4. 應用頁與產品頁曝光量
5. GEO/AI 搜尋引用情況
6. 有效索引率（已索引頁 / 總頁面）
7. 有 impressions 但 CTR 低的頁面數
8. 排名卡在 6-20 名的頁面數（潛力頁）
9. keyword cannibalization 偵測數
10. structured data 有效輸出率

### 13.2 Intent KPI

1. 高意圖訪客數
2. 高意圖帳戶數
3. 產品頁深度互動率
4. FAQ/比較頁互動率
5. 規格下載率
6. 回訪率

### 13.3 Conversion KPI

1. RFQ 提交數
2. 詢價數
3. 表單轉換率
4. 高意圖到 inquiry 轉換率
5. sales follow-up 速度
6. 再行銷受眾量

### 13.4 Product KPI

1. 官網建置時間
2. AI 生成採用率
3. 內容編修時間
4. 頁面上線效率
5. 系統月活使用者數

---

## 14. 主要風險與對策

### 14.1 內容資料品質差

風險：客戶提供的規格、型錄、命名不一致，導致 AI 與頁面品質不穩。

對策：

1. 在導入前設計資料清理流程
2. 建立最小必要欄位模型
3. AI 生成前強制完成 page brief 與資料驗證

### 14.2 系統做成一般 CMS

風險：RD 走向網站管理工具，而非成長系統。

對策：

1. 以 page brief、event、intent、workflow 為一級物件
2. 強調行為追蹤與轉換流程是 MVP 必做

### 14.3 系統做成一般 AI writer

風險：產品失去差異化，變成低價內容工具。

對策：

1. AI 必須依附頁型與 brief
2. 不提供自由型生成作為主要入口

### 14.4 整合過早過多

風險：Phase 1 被 CRM/Ads 整合拖慢。

對策：

1. Phase 1 僅做必要整合
2. 先以 webhook 與單一 CRM 為主

### 14.5 頁型過多導致導入複雜

風險：失去標準化與可複製性。

對策：

1. 先限定標準頁型
2. 以可配置區塊處理差異
3. 不支援大量自由布局

---

## 15. 商業化與市場進入策略

### 15.1 為什麼這個題目值得做

1. 台灣與亞洲大量中小製造商產品不差、供應能力不差，但數位前台薄弱，這是結構性落差。
2. 舊模式（業務、展會、代理商）仍能運作，但效率正在下降，這是最好的切入時機。
3. 市面有 HubSpot、6sense、PIM 等工具，但對中小製造商太貴、太複雜、不懂工業品脈絡。真正的缺口不是沒有工具，而是沒有為這個客群設計的整合解法。
4. 先做好的公司會拿到明顯優勢：更早進入買方 shortlist、更容易拿到高品質 inbound、降低對展會與單一業務的依賴。

### 15.2 競爭差異化

本產品不是與國際大平台正面競爭，而是補上最後一哩：

1. 專為外銷製造商設計，不是泛用 B2B MarTech
2. 官網原生內建 Capture/Intent/Conversion，不是外掛工具
3. AI 內容生成受內容定義約束，不是自由寫稿工具
4. 標準化頁型系統，不是客製網站專案
5. 導入門檻低，可配合政府補助降低第一次採用成本

### 15.3 目標客群細分

最優先的客群：

1. 年營收中型、行銷團隊 3 到 15 人的外銷製造商
2. 官網老舊或內容混亂，正在考慮重建的企業
3. 已有國際市場，但新客開發越來越難的企業
4. 高值設備、工控自動化、零組件、材料、機械零件類

### 15.4 建議包裝

1. Foundation Package
內容策略地圖、頁型系統、AI 內容生成、官網上線

2. Intent Package
事件追蹤、意圖分數、受眾分群、儀表板

3. Conversion Package
RFQ、再行銷同步、sales alert、CRM handoff

### 15.5 收費可能結構

1. 導入費：內容策略地圖建立、頁型建站、內容建置、資料整理
2. 訂閱費：系統使用、AI 生成、事件追蹤、dashboard
3. 成長服務費：內容優化、受眾營運、conversion 改善

### 15.6 Go-to-Market 策略

1. 先用顧問式導入收 5 到 10 家付費客戶，再萃取成產品
2. 將補助、顧問、導入、產品綁在一起，降低客戶第一次採用門檻
3. 不賊「網站升級」，而是賊「更多海外詢盤」「更高詢價品質」「更低業務前置溝通成本」
4. 先鎖定單一客群（台灣中小外銷製造商），不要一開始泛打所有 B2B
5. 用實際案例與數據證明效果，而不是用功能清單賊

### 15.7 早期不該做的事

1. 不做「台灣版 HubSpot」
2. 不做雙邊大市集，燒很大再等 network effect
3. 不做太通用的 AI 行銷工具，因為會失去產業差異化
4. 不把自己定位成純 SaaS，這個市場初期還是要靠顧問式導入

---

## 16. 推薦技術實作原則

1. 採 API-first 與模組化設計
2. Experience 與 Content 分離，避免內容被綁死在前端模板裡
3. 事件系統獨立於 GA4，GA 只作輔助同步
4. AI 生成要可追溯輸入來源與審核狀態
5. 所有 workflow 要有 audit trail
6. 整合要以 connector 或 webhook 隔離第三方依賴
7. URL 結構必須由 taxonomy 與 entity 關聯自動生成，不允許手動隨意建立
8. structured data 由內容模型自動輸出，不依賴手工標記
9. 內鏈由 entity 關聯規則自動建立，不依賴人工逐頁設定
10. 每個頁型模板必須預設 canonical、breadcrumb、metadata、schema 輸出點
11. sitemap 必須自動更新且依頁型或語言分檔

---

## 17. 最終結論

這套產品的本質不是網站專案，也不是單一行銷工具，而是一套以官網為主體承載介面的外銷製造商成長系統。

它的價值不在視覺客製，而在於：

1. 把產品與應用頁變成可被搜尋與理解的需求入口
2. 把網站行為變成可判讀的商業意圖訊號
3. 把詢價、RFQ、再行銷與業務交接變成可編排、可追蹤的成長流程

每一頁內容都必須先被定義目的，才允許被生成。內容策略地圖先於個別頁面，確保每篇內容都有對應的意圖、客群、產品與轉換目標。

再行銷是 Conversion Layer 的核心驅動力：匿名高意圖訪客透過廣告受眾同步持續觸達，已留資料訪客透過 email/nurture 或業務主動跟進推進轉換。

Phase 1 拆成兩階段：

1. Phase 1a：先讓頁面能上線、內容能生成、頁面能被搜尋
2. Phase 1b：再讓行為能追蹤、意圖能評分、詢盤能收取、再行銷能執行、內容成效能回饋

只要這個閉環跑通，後續的 intent intelligence、conversion orchestration 與 AI 強化能力就有機會逐步擴張成完整產品線。