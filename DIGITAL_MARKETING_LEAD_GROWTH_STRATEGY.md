# ForgeBase 數位行銷導向 Leads 成長診斷與產品調整建議

確認日期：2026-06-19  
修訂：2026-08-03（CF／FB **兩產品獨立**；可選 API 串接為長期架構）

## 相關文件（內部連結）

| 文件 | 說明 |
|------|------|
| [FORGEBASE_MASTER_ROADMAP.md](./FORGEBASE_MASTER_ROADMAP.md) | **執行總表**（五線五階段；所有計畫從這裡追蹤進度） |
| [CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md) | **CF↔ForgeBase 完整串接清單計畫**（執行主文件） |
| [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md) | 發佈 API 契約（認證／欄位／idempotency／錯誤碼） |
| [SEO_CAPTURE_INTEGRATION_EVALUATION.md](./SEO_CAPTURE_INTEGRATION_EVALUATION.md) | ContentFlow／ExposureFlow 評估（歷史＋修訂說明） |
| [FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md](./FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md) | ForgeBase P0／P1 工程修復（與串接並行） |
| [FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md](./FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md) | **Leads 實效強化計畫**（Intent／Conversion／成交漏斗／Ops，含國際貿易設計前提） |

本文件以數位行銷專家視角，重新評估 ForgeBase 以及本地兩個 Capture 相關專案：

- `C:\Users\User\Desktop\ContentFlow`
- `C:\Users\User\Desktop\Exposureflow`

評估前提：

- ForgeBase 的目標客群是「以外銷訂單為主的製造商」。
- 最終績效不是流量、排名或內容數量，而是 **Leads**，更精確地說是 **合格詢價 / Qualified RFQ / 可跟進商機**。
- 產品漏斗以 ForgeBase 既有定位：**Capture → Intent → Conversion** 為主。
- Capture、Intent、Conversion 的實際操作將由我方顧問 / Growth Ops 團隊負責，不交給製造商客戶自行操作。
- 製造商客戶取得的是動態儀表板、Leads/RFQ、跟進狀態與類 CRM 的追蹤介面。
- **ContentFlow 與 ForgeBase 是兩個獨立產品**，各自發展租戶；需要同時使用時以**可選 API 串接**連接（長期能力，非過渡合併）。
- **2026-08-03：** 對「FB 租戶需要完整 SEO Ops」的案件，正式串接 ContentFlow（見 [CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md)、[CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md)）。未串接的 FB／CF 租戶各自獨立營運。ExposureFlow 仍不整套接入。
- （原 2026-06「改 native、禁止長期 API」與後續「終將收斂進 FB」敘述均已廢止；以兩產品獨立＋可選串接為準。）

## 1. 核心結論

若完全站在數位行銷與 Leads 成長角度，ForgeBase 不應被定位成「幫製造商做官網」或「AI 內容生成工具」，而應定位成：

> **外銷製造商的 B2B Leads Growth OS：從被海外買家找到，到辨識採購意圖，再推進詢價與業務跟進。**

ForgeBase 目前的產品方向是對的，因為它已經不是單純 CMS，而是把 Capture、Intent、Conversion 串起來。但若目標是最大化 Leads，還需要做三個重點調整：

1. **Capture 不只做 SEO 內容，而要做「買家搜尋意圖覆蓋」**
   - 產品頁、應用頁、認證頁、比較頁、問題解決頁、採購指南、國家/產業 landing page 都要系統化。
   - ContentFlow 適合補「SEO 文章與長尾內容運營」。
   - ExposureFlow 適合補「GSC/SERP 機會與 indexability 健康診斷」。

2. **Intent 不只追蹤事件，而要辨識「採購階段與需求明確度」**
   - 製造業 B2B 買家常見訊號不是單純 page view，而是規格、MOQ、材料、認證、產能、OEM/ODM、交期、下載、比較、回訪。
   - ForgeBase 的 tracking/intent scoring 應更貼近「外銷採購意圖」。

3. **Conversion 不只放表單，而要降低詢價摩擦、提高詢價品質、縮短業務反應時間**
   - RFQ 表單、AI Product Advisor、Dynamic CTA、Spec Download Gate、Quote Readiness Score、SLA follow-up 都應圍繞「讓買家更容易留下可行需求」。

最推薦的產品調整方向（2026-08-03 修訂）：

```text
ForgeBase（獨立產品）
  = B2B 製造業 RFQ Growth OS
  = 自有租戶：站點、Intent、RFQ／CRM、客戶儀表板

ContentFlow（獨立產品）
  = SEO Content Ops control-plane
  = 自有租戶：可發 WordPress / Generic API / ForgeBase / …

可選串接（長期能力）
  = 僅當客戶同時需要兩邊時建立 CF project ↔ FB tenant
  = 契約見 CF_FB_PUBLISH_CONTRACT.md；執行見 CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md

ExposureFlow
  = 暫不整套串接；intelligence 概念中後期再評估
```

短期：對有需求的案件打通 CF↔FB 發佈／前台／驗證。中期：歸因＋多組串接開通自動化。長期：兩產品各自擴租戶；串接數隨「同時使用兩邊的客戶」成長，不做產品合併。

## 2. 北極星指標與 KPI 重定義

### 2.1 不建議用流量當最終指標

對外銷製造商來說，流量常常是虛榮指標。真正有價值的是：

- 海外採購商留下詢價。
- 經銷商 / 代理商 / OEM 客戶留下合作需求。
- 既有買家因搜尋特定規格而回訪並提交需求。
- 高意圖訪客被業務即時接住。

因此 ForgeBase 的北極星指標建議是：

> **每月合格 RFQ 數量（Qualified RFQs per Month）**

### 2.2 建議 KPI 層級

#### 北極星 KPI

- Qualified RFQs / month
- Sales-qualified leads / month
- RFQ to quote rate
- RFQ to deal rate
- Average RFQ response time

#### Capture KPI

- Non-brand organic impressions
- Non-brand organic clicks
- Indexed product/application/blog pages
- Ranking keywords in position 4-20
- Pages with impressions but low CTR
- Topic coverage by product category / application / buyer problem

#### Intent KPI

- High-intent visitor count
- Returning visitor rate
- Product depth per session
- Spec download rate
- Certification / capability views
- Chat engagement rate
- RFQ start rate

#### Conversion KPI

- RFQ submit rate
- Chat to RFQ handoff rate
- Form abandonment rate
- Spec download to RFQ rate
- CTA click to RFQ rate
- First response within SLA

### 2.3 建議產品內建 Lead Quality Score

ForgeBase 目前已有 intent score，但從數位行銷角度，建議拆成兩個分數：

1. **Visitor Intent Score**
   - 衡量匿名訪客行為意圖。

2. **Lead Quality Score**
   - 衡量已提交 RFQ/contact 的商機品質。

Lead Quality Score 建議考慮：

- 國家 / 市場是否為目標市場。
- 公司名稱是否完整。
- 是否有公司 email，而不是免費信箱。
- 是否提供產品、數量、規格、交期。
- 是否查看過多個產品或應用頁。
- 是否下載規格書或看認證頁。
- 是否回訪。
- 是否來自 high-intent keyword / page。

## 3. 外銷製造商的真實買家旅程

### 3.1 買家不是在找「文章」，而是在降低採購風險

外銷製造業 B2B 買家通常關心：

- 你是不是實際製造商，不是貿易商。
- 產品規格是否符合需求。
- 是否可 OEM / ODM。
- MOQ、產能、交期、付款條件。
- 是否有 ISO、CE、RoHS、UL、FDA、IATF 等認證。
- 是否有出口經驗。
- 是否服務過我的產業或國家。
- 是否能穩定供貨。
- 是否能快速回覆詢價。

因此 ForgeBase 的 Capture 內容不能只追求文章量，而要建立「採購信任資產」。

### 3.2 建議內容資產分類

#### A. Product Capture Pages

目標：捕捉明確產品搜尋。

頁面型態：

- 產品分類頁
- 產品詳情頁
- 型號頁
- 材料/規格頁
- OEM/ODM 版本頁

必要元素：

- 規格表
- 材料
- 應用場景
- MOQ / 客製能力
- 認證
- 可下載規格書
- RFQ CTA

#### B. Application Capture Pages

目標：捕捉「用途 / 場景 / 產業」搜尋。

頁面型態：

- For automotive applications
- For marine use
- For food processing equipment
- For industrial maintenance
- For OEM assembly

必要元素：

- 問題場景
- 推薦產品
- 規格需求
- 成功案例 / 使用理由
- 相關認證
- 詢價 CTA

#### C. Trust Capture Pages

目標：降低採購風險。

頁面型態：

- Certifications
- Quality control
- Factory capability
- Export experience
- Packaging and logistics
- OEM/ODM process

必要元素：

- 認證證明
- 品檢流程
- 產能
- 包裝
- 出口市場
- QA/QC 圖片
- 聯絡業務 CTA

#### D. Comparison / Alternative Pages

目標：捕捉評估中的買家。

頁面型態：

- Product A vs Product B
- Material A vs Material B
- OEM vs standard model
- Supplier comparison guide
- Taiwan manufacturer vs China supplier

必要元素：

- 客觀比較
- 選型建議
- 適用情境
- 詢價或選型協助 CTA

#### E. Buying Guide / SEO Article

目標：捕捉早期研究與長尾問題。

這是 ContentFlow 最適合負責的部分。

頁面型態：

- How to choose ...
- What is ...
- Specification guide
- Common buyer mistakes
- Import / sourcing checklist
- Certification guide

必要元素：

- FAQ schema
- Article schema
- 內鏈到產品/應用/詢價
- soft CTA
- downloadable checklist

## 4. Capture 層診斷與建議

### 4.1 ForgeBase 目前 Capture 的優勢

ForgeBase 已經有一些很好的基礎：

- 多租戶白標網站。
- Product / Category / Application / Certification / Capability / FAQ 模型。
- PageBrief 與 AI 生成。
- Legacy Site Intake。
- sitemap / robots / structured data。
- SEO redirect 管理。
- R2 資產管理。

這些剛好符合外銷製造商需要的「產品型內容底座」。

### 4.2 Capture 最大缺口

目前缺口不是「沒有 SEO」，而是：

1. SEO 內容策略尚未完全以「買家搜尋意圖矩陣」管理。
2. Blog/news/knowledge center 尚未成為可持續運營的流量資產。
3. sitemap 尚未收錄 `Page.page_type == blog_post` 這類外部產生內容。
4. GSC 資料目前偏查詢，不是完整 opportunity engine。
5. Indexability 健康沒有變成產品內的 action item。

### 4.3 Capture 產品調整建議

#### 建議 1：新增 Capture Coverage Map

ForgeBase Admin 應該有一個 Capture Coverage Map，讓製造商或顧問知道目前內容覆蓋度。

維度：

- Product category
- Application
- Certification
- Capability
- Buyer problem
- Target country
- Buyer stage
- Keyword cluster

每個格子顯示：

- 是否已有頁面。
- 是否 published。
- 是否 indexed。
- 是否有 impressions。
- 是否有 leads。
- 是否需要 ContentFlow 產文。
- 是否需要 ExposureFlow 診斷。

#### 建議 2：Content Strategy 不只管理內容，而要管理 Lead Intent

ForgeBase 目前有 ContentStrategy / PageBrief 類概念。建議調整為：

```text
Content Opportunity
  - target buyer
  - target market
  - product category
  - application
  - primary intent
  - funnel stage
  - expected CTA
  - expected lead type
```

例如：

- Keyword: stainless steel hose clamp manufacturer
- Intent: supplier sourcing
- Funnel stage: high Capture / mid Intent
- Page type: product category
- CTA: Request quote
- Lead type: OEM buyer / distributor

#### 建議 3：優先打造「可詢價頁」而不是只打造「可排名頁」

每個 Capture page 應該具備：

- 明確下一步 CTA。
- 產品/規格/應用資訊。
- 風險降低元素。
- 表單或 chat entry。
- 追蹤事件。

如果文章能排名但不能把訪客導向產品或 RFQ，它對 ForgeBase 的價值有限。

#### 建議 4：參考 ContentFlow，原生實作 SEO Content Ops

> **2026-08-03 讀法：** 下列「原生實作」為歷史產品構想。現行決策為 **CF／FB 兩產品獨立＋可選 API 串接**（見 [CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md)）。未串接的 FB 租戶若需 SEO 長文，優先評估串接 CF，而非在 FB 重做整套 Content Ops。ExposureFlow 概念仍可作中後期 FB 補強參考，但不整套接入。

ForgeBase 應參考 ContentFlow 的設計，原生實作：

- Buying guides
- Comparison articles
- FAQ-rich articles
- Long-tail SEO pages
- Refresh underperforming pages
- GSC-driven topic expansion

不應負責：

- Product entity canonical data
- Application entity canonical data
- Certification truth
- Capability truth
- RFQ workflow

#### 建議 5：參考 ExposureFlow，原生實作 Capture Intelligence

ForgeBase 應參考 ExposureFlow 的設計，原生實作：

- GSC query-page opportunity
- SERP slot analysis
- Topic gap
- Sitemap health
- Published noindex audit
- Index discovery gap
- Technical SEO issue → Admin action

這些訊號應直接回流到 ForgeBase 的 `CaptureOpportunity`、`SeoHealthIssue`、`ContentTask` 與 Leads/RFQ 歸因。

## 5. Intent 層診斷與建議

### 5.1 Intent 的核心問題

Intent 層要回答：

> 哪些訪客只是看資料，哪些訪客已經接近詢價？

外銷製造業的高意圖行為通常包括：

- 查看多個產品詳情。
- 查看規格表。
- 下載型錄或 spec sheet。
- 查看 MOQ / OEM / ODM / packaging。
- 查看認證頁。
- 查看 factory capability。
- 回訪同一產品頁。
- 從 comparison page 點到 RFQ。
- 開啟 chat 詢問規格、價格、交期。
- 查看 contact / request quote 頁。

### 5.2 ForgeBase 目前 Intent 的優勢

ForgeBase 已有：

- tracking events。
- visitor/session。
- intent score。
- intent stage。
- Dynamic CTA。
- AI Product Advisor。
- chat handoff。
- visitor dashboard。

這是很好的底座。

### 5.3 Intent 需要更製造業化

建議新增或強化以下事件：

#### Product Intent Events

- `spec_table_view`
- `spec_download`
- `model_compare`
- `variant_select`
- `moq_view`
- `oem_odm_view`
- `material_filter`
- `certification_related_click`

#### Trust Intent Events

- `certification_view`
- `quality_process_view`
- `factory_capability_view`
- `export_market_view`
- `case_study_view`

#### Buying Intent Events

- `rfq_start`
- `rfq_field_completed`
- `rfq_abandon`
- `rfq_submit`
- `chat_price_question`
- `chat_lead_time_question`
- `chat_moq_question`
- `catalog_download`

### 5.4 Intent Score 建議分層

建議不要只有總分，應拆成 intent facets：

```text
VisitorIntent
  - product_interest_score
  - sourcing_readiness_score
  - trust_validation_score
  - urgency_score
  - conversion_likelihood_score
```

這樣 Admin 能看懂「為什麼這個訪客值得追」。

例如：

- A 訪客：產品興趣高，但信任驗證低 → 推 certification / quality CTA。
- B 訪客：信任驗證高，且看 RFQ 頁 → 推 sales-ready CTA。
- C 訪客：看多篇 buying guide，但沒看產品 → 推 product finder。

### 5.5 Dynamic CTA 應更像銷售助理

CTA 不應只是固定按鈕，而應依 intent stage 改變：

#### Cold

- View product catalog
- Explore applications
- Download buyer checklist

#### Warm

- Compare models
- Ask product advisor
- Download spec sheet

#### Hot

- Request quotation
- Send us your drawing/spec
- Ask MOQ and lead time

#### Sales-ready

- Get quote in 24h
- Talk to export sales
- Upload requirements

### 5.6 AI Product Advisor 應以「問出詢價需求」為目標

AI Product Advisor 不應只回答 FAQ，而應逐步補齊 RFQ 所需欄位：

- Product / model
- Application
- Quantity
- Material / specification
- Target market
- Timeline
- Certification requirement
- OEM/ODM need
- Contact info

最後生成 RFQ prefill。

建議導入：

```text
Chat Qualification Checklist
  - 是否知道產品類別
  - 是否知道數量
  - 是否知道用途
  - 是否知道交期
  - 是否需要認證
  - 是否可建立 RFQ
```

## 6. Conversion 層診斷與建議

### 6.1 Conversion 的核心問題

Conversion 層要回答：

> 如何讓高意圖訪客更容易留下有品質的詢價，並讓業務快速跟進？

對製造商來說，Lead 品質比 Lead 數量更重要。100 個模糊留言不如 10 個有產品、數量、規格、交期的 RFQ。

### 6.2 ForgeBase 目前 Conversion 的優勢

ForgeBase 已有：

- RFQ form。
- Contact form。
- Chat → RFQ handoff。
- RFQ event audit。
- notification。
- routing。
- Copilot。
- AgentOS integration。

這比一般官網表單強很多。

### 6.3 Conversion 需要優化的地方

#### 建議 1：RFQ 表單分成短版與長版

不是所有訪客都願意一開始填完整 RFQ。

建議：

```text
Quick RFQ
  - name
  - email
  - company
  - product interest
  - message

Structured RFQ
  - product
  - quantity
  - specification
  - application
  - timeline
  - certification
  - target market
  - attachment
```

Dynamic CTA 可依意圖決定推哪一種。

#### 建議 2：Spec Download Gate 不是硬擋，而是漸進式交換

規格書下載是很強的 intent signal。

建議三層：

1. 公開看 basic spec。
2. 留 email 下載 full datasheet。
3. 高價值資料如 CAD、完整型錄、認證文件需補公司資料。

#### 建議 3：RFQ Form 需要 Form Intelligence

追蹤：

- 哪個欄位造成 drop-off。
- 哪些頁帶來最高 RFQ submit。
- 哪些產品 RFQ quality 高。
- 哪些國家 RFQ quality 高。
- 哪些 CTA 帶來最多 qualified RFQ。

#### 建議 4：Lead Routing 應依產品與國家

外銷製造業常需要不同業務處理不同市場或產品線。

建議 routing rules：

- country / region
- product category
- language
- lead score
- existing contact
- distributor vs OEM

#### 建議 5：SLA 是 Conversion 的一部分

Leads 最大化不只在網站上發生。B2B RFQ 的回覆速度會直接影響成交率。

建議產品內建：

- first response SLA。
- 24h reminder。
- 48h escalation。
- quote sent tracking。
- lost reason。
- response quality template。

ForgeBase 已有部分 RFQ event / reminder 欄位，應把它產品化成「Lead Follow-up Performance」。

## 7. 產品定位建議

### 7.1 目前定位應更銳利

建議對外說法從：

> 外銷製造商官網成長系統

升級成：

> 外銷製造商的 RFQ Leads Growth OS

或：

> 把製造業網站變成海外詢價引擎

### 7.2 產品賣點不應只講 AI

製造商不一定在乎 AI，他們在乎：

- 能不能被海外買家找到。
- 能不能收到詢價。
- 詢價是不是有效。
- 業務能不能跟進。
- 網站是不是看起來可信。

建議行銷語言：

- Capture overseas buyers searching for your products.
- Identify visitors with sourcing intent.
- Turn product interest into structured RFQs.
- Help export sales respond faster.
- Know which pages generate real inquiries.

### 7.3 方案包裝建議

#### Starter

定位：可被找到、可詢價的外銷網站。

重點：

- Product catalog
- SEO basics
- RFQ form
- Basic analytics
- 50 products

#### Professional

定位：持續產生與追蹤詢價的成長系統。

重點：

- Full tracking
- Intent scoring
- AI Advisor
- Dynamic CTA
- RFQ follow-up
- ContentFlow SEO article integration
- GSC opportunity

#### Growth / Managed SEO Add-on

定位：代操 Capture growth。

重點：

- Monthly SEO content plan
- ContentFlow 串接產文／refresh（若客戶同時購 CF）
- SEO health／opportunity 報告（CF 控制面或日後 FB 輕量訊號）
- Lead quality review
- Quarterly conversion optimization

這個 add-on 適合組合 **獨立產品 CF＋FB**（可選串接），由我方顧問操作；不把 CF／EF 複雜後台交給製造商，也不預設把 CF 核心抄進 FB。

## 8. SEO 產品導入建議

> **2026-08-03 讀法：** 本节原「以 CF／EF 為藍本、在 FB native 重寫」路線 **已廢止為預設架構**。現行：ContentFlow 為獨立產品；需要時以 publisher 串接 ForgeBase。下文保留作能力對照與靈感，執行以串接計畫為準。

### 8.1 ContentFlow 的角色

ContentFlow 應是：

> **獨立的 SEO Content Ops 產品**；對已串接的 FB 租戶，經 `ForgeBasePublisher` 發佈。其閉環設計亦可供未串接場景參考，但 **不預設重寫進 ForgeBase**。

串接後由 CF 負責（不必在 FB 重做）：

- 長尾文章。
- buying guide。
- FAQ article。
- comparison article。
- content refresh。
- ranking feedback。
- publish safety。

不要負責：

- 產品主資料。
- 認證真實性。
- 產能資料。
- RFQ。
- CRM。

### 8.2 ExposureFlow 的角色

ExposureFlow 應是：

> **能力參考來源**（暫不整套串接／合併）。若未來 FB 要補強 opportunity／indexability，可萃取概念，而非預設整倉接入。

可參考的能力方向：

- GSC/SERP opportunity。
- indexability health。
- topic gap。
- cannibalization。
- consultant roadmap。
- technical issue diagnosis。

不應直接照搬：

- ExposureFlow runtime。
- ExposureFlow 完整後台。
- ExposureFlow 租戶模型。
- ExposureFlow publish adapter。

### 8.3 建議資料流

```text
（已串接案件）ContentFlow Opportunity / SEO Ops
  → 選題、產文、審核
  → ForgeBasePublisher 發佈 blog_post

ForgeBase
  → 呈現文章、Intent、RFQ／Leads
  →（可選）內容來源歸因

（未串接／中後期可選）FB 自建 opportunity／health 訊號
  → 僅作補強，不取代獨立產品 CF

ForgeBase Intent / Conversion
  → 追蹤 visitor、RFQ、Lead Quality

回饋
  → 哪些內容帶來 qualified RFQ，反饋給 SEO strategy
```

### 8.4 SEO 不應停在排名，必須回到 Leads

每篇 ContentFlow 文章都應有目標：

- 目標產品類別。
- 目標買家問題。
- 目標 CTA。
- 目標 lead type。
- 內鏈到哪個產品/應用/RFQ。
- 預期轉換事件。

每個 ExposureFlow opportunity 也應回到：

- 如果處理這個 gap，可能帶來什麼 lead？
- 是產品詢價、代理合作、OEM 案，還是低價值資訊流量？

## 9. 建議產品 Roadmap

### Phase 1：Lead KPI 基礎化

目標：讓 ForgeBase 從「網站後台」變成「Leads 成效後台」。

工作：

1. 定義 Qualified RFQ。
2. 新增 Lead Quality Score。
3. Dashboard 顯示：
   - qualified RFQs
   - RFQ conversion rate
   - first response time
   - top lead-generating pages
   - top lead-generating products
4. RFQ event 補齊 sales follow-up performance。

驗收：

- 使用者能看到本月哪些頁面帶來詢價。
- 使用者能知道哪些詢價品質最高。
- 使用者能知道業務是否有準時回覆。

### Phase 2：Capture Coverage Map

目標：讓製造商知道哪些內容缺口影響 leads。

工作：

1. 建產品/應用/認證/問題/國家 coverage map。
2. 接 GSC impression/click/position。
3. 標記：
   - missing page
   - unpublished page
   - indexed but no leads
   - high impression low CTR
   - high traffic no RFQ
4. 產生 Content Opportunity。

驗收：

- Admin 能看到哪些 product category 缺 SEO 頁。
- Admin 能看到哪些頁有曝光但沒有詢價。
- Admin 能一鍵建立 PageBrief 或 ContentFlow task。

### Phase 3：ContentFlow-inspired Native Content Ops

目標：（歷史）曾規劃在 ForgeBase 原生產生 SEO 文章草稿——**現行改為可選串接 ContentFlow 產生並發佈至 FB**。下列 checklist 若與串接重疊，以串接計畫為準；其餘屬未串接 FB 租戶的輕量補強，並導回 ForgeBase Leads。

工作：

1. ForgeBase 補 blog/news 動態路由。
2. sitemap 收錄 blog_post。
3. 原生 content pipeline 對齊 locale / route / tenant。
4. 每篇文章必須設定 CTA 與內鏈目標。
5. 追蹤 blog → product/application/RFQ path。

驗收：

- ForgeBase 原生 pipeline 可產生 SEO content draft。
- 發布文章能出現在 sitemap。
- 文章能追蹤 CTA、product click、RFQ start。

### Phase 4：Intent Scoring 2.0

目標：讓 intent scoring 更貼近採購行為。

工作：

1. 拆分 intent facets。
2. 新增製造業高意圖事件。
3. Dynamic CTA 依 facet 調整。
4. Chat qualification checklist。
5. Lead Quality Score 與 visitor intent 串接。

驗收：

- Admin 能知道訪客是產品興趣、信任驗證、還是採購準備高。
- Dynamic CTA 能依不同意圖推不同下一步。
- Chat 能產出更完整 RFQ prefill。

### Phase 5：ExposureFlow-inspired Native Intelligence

目標：補上 GSC/SERP/indexability 層。

工作：

1. 原生實作 sitemap health。
2. 原生實作 published noindex audit。
3. 原生實作 GSC query-page opportunity。
4. 原生實作 topic gap。
5. 將問題轉成 Capture Opportunity。

驗收：

- 系統能主動告訴使用者「哪些頁沒被收錄」。
- 系統能主動告訴使用者「哪些 query 值得做內容」。
- 系統能把 SEO issue 轉成具體 action。

### Phase 6：Managed Growth Add-on

目標：將 ForgeBase-native Content Ops + Capture Intelligence + Leads CRM 包成顧問服務。

工作：

1. 每月產生 Capture Growth Report。
2. 每月建議 5-10 個內容/轉換優化任務。
3. 顧問或內部團隊操作 ForgeBase Growth Ops。
4. ForgeBase 原生產生 opportunity / roadmap。
5. ForgeBase 回報 leads 與轉換結果。

驗收：

- 客戶能看到 SEO 工作與 RFQ 增長的關聯。
- 可作為 Professional 以上 add-on 收費。

## 10. 頁面與 CTA 調整建議

### 10.1 每個產品頁都應有三種 CTA

1. Low commitment
   - Download catalog
   - View specifications
   - Compare models

2. Medium commitment
   - Ask product advisor
   - Request product recommendation
   - Send us your application

3. High commitment
   - Request quote
   - Upload drawing/spec
   - Talk to export sales

### 10.2 每篇 SEO 文章都應導向商業頁

文章 CTA 應分層：

- 文中內鏈到 product/application。
- 文末導向 buyer checklist 或 advisor。
- 高意圖段落導向 RFQ。
- FAQ block 導向 chat。

### 10.3 Trust page 要變成 conversion assist

Certification、quality、factory capability 不只是品牌頁，應追蹤：

- 訪客是否在 RFQ 前看過 trust page。
- 看過 trust page 的 RFQ conversion 是否更高。
- 哪些認證頁對哪些國家 leads 有幫助。

## 11. Admin 報表建議

ForgeBase Admin 應從「內容管理」升級為「Lead Growth Command Center」。

建議首頁 KPI：

- This month qualified RFQs
- RFQ conversion rate
- Top converting pages
- High-intent visitors
- RFQs awaiting response
- Average first response time
- Content opportunities
- SEO health issues

建議報表：

1. Lead Source Report
   - organic / direct / referral / paid / chat / content article

2. Content to Lead Report
   - page views → CTA → RFQ start → RFQ submit → qualified RFQ

3. Product Demand Report
   - 哪些產品帶來最多 RFQ
   - 哪些產品頁有流量但沒有 RFQ

4. Market Report
   - 國家/區域 leads
   - 國家/區域 conversion rate

5. Sales Follow-up Report
   - RFQ response time
   - quote sent rate
   - overdue RFQs

## 12. 最重要的產品邊界

### 12.1 ForgeBase 不應變成通用 SEO 平台

ForgeBase 的優勢是「外銷製造業 + RFQ」。

因此所有 SEO 功能都應回到：

- 能不能讓海外買家找到產品。
- 能不能提高詢價。
- 能不能提升商機品質。
- 能不能讓業務更快跟進。

不要做成泛用 SEO dashboard。

### 12.2 ContentFlow 不應取代 ForgeBase CMS

即使參考 ContentFlow 生產 SEO 文章，ForgeBase 仍應掌握：

- canonical product data。
- page status。
- tenant ownership。
- publishing workflow。
- lead tracking。

### 12.3 顧問操作複雜度不應直接暴露給製造商客戶

ExposureFlow 的顧問工作流很強，但對一般製造商太複雜。ForgeBase 應把這些能力原生化後，拆成兩層：

- 我方 Growth Ops / SEO 顧問 / 代理商夥伴使用的操作後台。
- 製造商客戶使用的 Leads dashboard / RFQ CRM。

製造商客戶只需要看到：

- 本月做了什麼。
- 帶來多少曝光。
- 帶來多少詢價。
- 下一步建議。

## 13. 最終建議

若目標是最大化 Leads，ForgeBase 接下來的產品重點應是：

1. **把所有 SEO 與內容工作都綁回 RFQ / Leads。**
2. **把 Capture 從內容管理升級成買家意圖覆蓋管理。**
3. **把 Intent 從事件分數升級成採購階段判斷。**
4. **把 Conversion 從表單升級成詢價品質與業務跟進系統。**
5. **對需要完整 SEO Ops 的 FB 案件：可選串接獨立產品 ContentFlow**（執行：[CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md)，契約：[CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md)）。
6. **中期：視需要再評估 ExposureFlow 概念**（不整套接入；見 [SEO_CAPTURE_INTEGRATION_EVALUATION.md](./SEO_CAPTURE_INTEGRATION_EVALUATION.md)）。
7. **長期：CF 與 FB 各自擴租戶**；把跨產品開通做成可規模化整合能力，**不合併產品**。
8. **並行修復 ForgeBase P0 地基**（[FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md](./FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md)）。
9. **長期包裝 Managed Growth Add-on**（可組合 CF＋FB 服務），客戶在 FB 場景仍只看成果面。

一句話總結：

> ForgeBase 要最大化外銷製造商 Leads，應建立從「海外買家搜尋」到「合格 RFQ 與業務跟進」的閉環。ContentFlow 與 ForgeBase 為獨立產品、各自長租戶；需要時以可選 API 串接協作，而非合併或互相重寫對方核心。
