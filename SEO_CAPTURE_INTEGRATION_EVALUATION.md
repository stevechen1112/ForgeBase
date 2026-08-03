# ForgeBase Capture SEO 候選專案整合評估

確認日期：2026-06-19  
**2026-08-03 修訂：** ContentFlow 與 ForgeBase 為**兩個獨立產品**（各自租戶）；需要協作時採**可選、長期 API 串接**（非 native 合併、亦非過渡跳板）。執行與契約見下方連結；本文其餘章節保留為歷史評估與能力對照。

## 相關文件（內部連結）

| 文件 | 說明 |
|------|------|
| [DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md](./DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md) | **主策略**（Leads 北極星與產品方向） |
| [CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md) | CF↔ForgeBase **串接執行計畫** |
| [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md) | 發佈 **API 契約** |
| [FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md](./FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md) | ForgeBase 工程 P0／P1 |

評估對象：

- `C:\Users\User\Desktop\ContentFlow`
- `C:\Users\User\Desktop\Exposureflow`

評估目的：判斷兩個 SEO 相關專案哪一個更適合補強 ForgeBase 的 Capture 階段，以及若要整合進 ForgeBase 應採取什麼路線。

## 0. 重要修訂：產品操作模式與架構決策

2026-06-19 補充決策：

- ForgeBase、ContentFlow、ExposureFlow 類能力都不會直接交給製造商客戶操作。
- 我方會作為顧問 / Growth Ops 團隊操作 Capture、Intent、Conversion 漏斗，確保 SEO、內容、意圖追蹤、RFQ 轉換與業務跟進持續最佳化。
- 製造商客戶取得的是動態儀表板、Leads/RFQ 資訊、跟進狀態與近似 CRM 的銷售追蹤介面。

**2026-08-03 覆蓋決策（現行）：**

- **CF 與 FB 兩產品獨立**，各自發展租戶。
- 需要同時使用時，以**可選 API 串接**為**長期**整合方式（CF 視 FB 為一等 publisher）。
- 不做「把 CF 核心重寫進 FB」或「租戶變多就合併產品」的預設路線。
- 執行：[CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md)
- 契約：[CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md)
- ExposureFlow 仍不整套接入。
- 下列 2026-06「全面 native／禁止長期 API」敘述**僅作歷史紀錄**。

（歷史）2026-06 曾傾向參考後原生化、避免長期 runtime。該路線已由「兩產品獨立＋可選串接」取代。

因此，**現行**架構判斷是：

```text
ContentFlow（獨立產品，自有租戶）
  = SEO Content Ops；可發 WP / Generic / ForgeBase / …

ForgeBase（獨立產品，自有租戶）
  = RFQ Growth OS；站點、Intent、RFQ／CRM

可選串接
  = 稀疏對照 CF project ↔ FB tenant
  = 隨「同時使用兩邊的客戶」成長
```

## 1. 結論摘要

> **現行結論（2026-08-03）：** 兩產品獨立；按需串接為長期架構。細節見 [CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md)。以下保留 2026-06 原文供對照。


> **注意：** 自本段以下至文末多數章節為 **2026-06 歷史原文**（含「應 native、不建議長期 API」）。現行決策以文首 2026-08-03 為準：**兩產品獨立＋可選串接**。請勿單獨引用歷史段落作為執行依據。

如果目標是「近期補強 ForgeBase Capture 階段，讓 ForgeBase 可以持續產出 SEO 文章、接入 GSC 回饋、做內容 refresh 與 indexing」，我會優先參考 **ContentFlow** 的內容閉環設計，但不建議把 ContentFlow 當成長期外部 API 依賴。

原因很直接：

1. ContentFlow 的產品核心就是 SEO 內容閉環，與 ForgeBase Capture 的「AI 內容生成、SEO、上線後持續內容運營」最接近。
2. ContentFlow 已經有 `ForgeBasePublisher`，證明它的內容產出可映射到 ForgeBase `PageBrief` / `Page` / `publish` 工作流。
3. 但正式產品應把這些能力重寫成 ForgeBase 原生模組，讓內容任務、審核、發布、歸因、RFQ 轉換全部留在 ForgeBase 的資料與權限邊界內。

如果目標是「長期把 ForgeBase 從建站/RFQ OS 擴展成顧問式 SEO/曝光營運平台」，ExposureFlow 的戰略價值更高，但也不應整套接入或整套重搬，而應萃取其 GSC/SERP opportunity、indexability、topic graph、decision/roadmap 概念，重寫成 ForgeBase-native Capture Intelligence。

ExposureFlow 更像一套完整的 SEO 顧問作業系統：GSC/SERP、Topic Graph、Exposure Opportunity、Decision Plane、Indexability、Consultant Inbox、Celery job 全都很完整。這些非常適合我方顧問操作模式，但它的租戶模型、內容模型、後台與運維 stack 都不應直接進入 ForgeBase。

因此我的建議是：

- **短期：以 ContentFlow 為藍本，在 ForgeBase 內原生實作 SEO Content Ops 最小能力。**
- **中期：以 ExposureFlow 為藍本，在 ForgeBase 內原生實作 GSC/SERP/indexability/topic graph intelligence。**
- **長期：ForgeBase 成為我方顧問團隊的 Growth Ops cockpit，客戶端只看到 Leads dashboard / RFQ CRM / 跟進狀態。**

## 2. ForgeBase Capture 階段目前缺什麼

ForgeBase 現有 Capture 能力偏向「建站、內容實體、舊站匯入與前台 SEO 基礎設施」：

- Product、Application、Category、FAQ、Capability 等 B2B 製造業實體模型。
- Legacy Site Intake：舊站爬取、候選內容抽取、review、commit。
- PageBrief 與 AI 內容生成。
- sitemap、robots、canonical、structured data、redirect 管理。
- GSC 基礎查詢與單頁 SEO 優化建議。

它目前相對不足的是：

1. 上線後的 SEO 內容營運節奏。
2. 從 GSC/SERP 自動產生內容機會。
3. 舊文 refresh 與排名下滑修復。
4. Indexability 監控，例如 sitemap health、published noindex、coverage gap。
5. 顧問式 SEO 決策工作流，例如 opportunity → decision → roadmap → content execution。

ContentFlow 比較補第 1、2、3 項；ExposureFlow 比較補第 2、4、5 項。

## 3. ContentFlow 評估

### 3.1 專案定位

ContentFlow 是一套全自動 SEO 內容閉環系統，核心流程是：

```text
GSC/GA4/SERP 數據
  → Strategic Agent 選題
  → Research
  → Strategy
  → Writing
  → SEO Check / SEO QA
  → FactCheck
  → Publish
  → GSC / Indexing / Refresh 回饋
```

它比較像「SEO 內容工廠 + 自動更新系統」，不是顧問 CRM，也不是舊站 intake 工具。

### 3.2 技術棧

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy + Alembic
- PostgreSQL / SQLite
- APScheduler
- Gemini 為主力 LLM，OpenAI/Anthropic 可作 failover
- ChromaDB 作知識庫
- Cloudflare R2 作圖片儲存
- Admin 以 FastAPI/Jinja2 提供

### 3.3 對 ForgeBase 最有價值的能力

1. **SEO 長文與知識型內容生成**
   - 適合補 ForgeBase 目前較弱的 blog/news/knowledge center 類內容。
   - 不應取代 ForgeBase 原本的 Product/Application/FAQ 實體生成。

2. **發布安全閘**
   - ContentFlow 有 `publish_safety` 概念，能避免未審核或品質不足內容直接發布。

3. **GSC/GA4/SERP 回饋**
   - 可用來持續選題、refresh 舊文、檢查排名變化。

4. **ForgeBase Publisher 已存在**
   - `src/contentflow/publishers/forgebase.py` 已實作：
     - `POST /api/v1/content/briefs`
     - `POST /api/v1/content/pages`
     - `POST /api/v1/content/pages/{id}/publish`
   - 認證使用 `X-API-Key`，可對應 ForgeBase 的 service account token。

5. **ProjectIntegration 已支援 ForgeBase**
   - `project_integrations.py` 有 `FORGEBASE` integration type，可 per project 設定 base URL 與 secret。

### 3.4 主要整合缺口

ContentFlow 不是完全即插即用，仍需調整：

1. **locale hardcode**
   - `ForgeBasePublisher` 目前寫死 `locale: "zh-tw"`。
   - ForgeBase 使用 `zh-TW` 與 `en` 的慣例時需統一。

2. **URL 組裝可能不符合 ForgeBase 前台路由**
   - `publish_page()` 用 `{base}/{slug}` 組 URL。
   - ForgeBase 若要走 `/news/{slug}`、`/{locale}/{slug}` 或 `/blog/{slug}`，需調整。

3. **ForgeBase Web 尚未完整支援 blog_post**
   - `Page` model 有 `page_type: "blog_post"`。
   - 但 sitemap 目前只收 categories/products/applications/capabilities/certifications/comparisons/FAQ，沒有 pages/blog_post。
   - `/news` 目前仍偏靜態頁，還沒成為動態 blog index。

4. **ContentFlow 目標網站串接規範與實作不同**
   - 規範寫的是 `/api/contentflow/publish` 等通用 API。
   - 實際 ForgeBase publisher 使用現有 `/api/v1/content/*` 三步 API。
   - 文件需要同步，避免未來整合時混亂。

5. **ContentFlow 自身多租戶還有已知缺口**
   - `B1_MULTI_TENANT_AUDIT_2026-06-07.md` 指出 `chat_agent.py` 仍有 `Project.first()` 單租戶假設。
   - 部分 Admin dashboard 是全 instance count。
   - 若只是單一 ForgeBase tenant pilot，可先避開；若要多租戶正式營運，必修。

### 3.5 ContentFlow 適合的採用方式

修訂後不建議把 ContentFlow 作為長期 sidecar。更適合的做法是把它當成產品與工程藍本，重寫成 ForgeBase 原生的 SEO Content Ops：

```text
ForgeBase
  - 保留 B2B 實體 CMS、Legacy Intake、RFQ、前台渲染

ForgeBase-native SEO Content Ops
  - 參考 ContentFlow 的選題、生成、審查、refresh、GSC 回饋
  - 直接寫入 ForgeBase PageBrief / Page / ContentOpportunity / AuditLog
  - 直接歸因到 ForgeBase Leads / RFQ / Visitor Journey
```

短期原生實作的最小範圍：

1. ForgeBase 新增動態 blog/news 路由與列表頁。
2. ForgeBase sitemap 加入 published `Page.page_type == "blog_post"`。
3. 新增 ForgeBase-native `ContentOpportunity` / `SeoContentTask`，承接 ContentFlow 的選題與 production queue 概念。
4. 新增 ForgeBase-native content generation pipeline，先支援 `blog_post` / buying guide / comparison article。
5. 內容預設進草稿，不自動發布；由我方顧問在 ForgeBase Growth Ops 後台審核。
6. 每篇內容必須綁定 target product/application/CTA/lead goal，避免只產生流量。

## 4. ExposureFlow 評估

### 4.1 專案定位

ExposureFlow 是以自然曝光最大化為核心的顧問作業系統，不是單純的產文工具。它的核心流程是：

```text
GSC / SERP / Sitemap / Indexability
  → ExposureAsset
  → ExposureOpportunity
  → ActionCandidate
  → ActionDecision
  → Roadmap
  → ContentBrief / Technical Fix
  → Content Pipeline / Publish
  → Indexability verify / Topic Graph rebuild
```

它更像「SEO 顧問後台 + 曝光決策引擎」，適合代理商或顧問代操多個客戶站點。

### 4.2 技術棧

- pnpm + Turbo monorepo
- Next.js 15 + React 19
- FastAPI
- SQLAlchemy async + Alembic
- PostgreSQL 16 + pgvector
- Redis + Celery worker + Celery beat
- OpenAI SDK，預設 `gpt-4o-mini`
- packages/connectors、execution-adapters、shared-types、sdk、ui
- Production Docker Compose + Caddy

### 4.3 對 ForgeBase 最有價值的能力

1. **GSC/SERP 驅動的機會引擎**
   - 不是單純看頁面，而是將查詢、頁面、SERP slot、topic gap 轉成 `ExposureOpportunity`。

2. **Indexability 閉環**
   - sitemap health。
   - published noindex audit。
   - coverage gap。
   - live sitemap diagnosis。
   - URL allowlist / SSRF 防護。

3. **Topic Graph**
   - 從 GSC query/page 聚類，找出 coverage gap、cannibalization、內鏈機會。

4. **顧問工作流**
   - Consultant Inbox。
   - ActionCandidate / ActionDecision。
   - Roadmap。
   - Agency dashboard。

5. **packages/connectors 可作為重寫參考**
   - `connectors/google_search_console.py`
   - `connectors/tech_seo`
   - `connectors/indexability`
   - `connectors/serp`

### 4.4 主要整合缺口

ExposureFlow 比 ContentFlow 強在曝光營運，但短期整合成本高很多：

1. **ForgeBase adapter 未真正接線**
   - `packages/execution-adapters/src/execution_adapters/forgebase.py` 存在。
   - 但 `apps/api/exposureflow_api/content/service.py` 的 `PUBLISH_PROVIDERS` 目前只有 `contentflow`、`wordpress`。
   - `publish_generation_run()` 不支援 `forgebase`。

2. **adapter 假設的 ForgeBase API 不存在**
   - ExposureFlow adapter 預期：
     - `POST /api/v1/sites/{site_slug}/content`
     - `PATCH /api/v1/sites/{site_slug}/content/{content_id}`
   - ForgeBase 目前是 `/api/v1/content/briefs`、`/api/v1/content/pages`、`/api/v1/content/pages/{id}/publish`。

3. **租戶模型差異大**
   - ForgeBase：Tenant。
   - ExposureFlow：Account → Organization/Workspace → Site。
   - 需要 mapping layer，不宜硬合併。

4. **內容模型差異大**
   - ForgeBase：PageBrief、Page、Product、Application、FAQ。
   - ExposureFlow：ExposureOpportunity、ActionCandidate、ContentBrief、ContentGenerationRun、ExecutionJob。
   - 若合併，需要設計兩套 workflow 的邊界。

5. **運維 stack 更重**
   - ExposureFlow 需要 Postgres + pgvector、Redis、Celery worker、Celery beat、Next.js web、FastAPI API。
   - 對 ForgeBase 目前 Linode 部署來說，不適合直接塞進現有 API。

6. **商業模式不同**
   - ExposureFlow 明確採 Consultant-Led GTM。
   - ForgeBase 更像外銷製造商自有網站/RFQ OS。
   - 若讓終端製造商直接看到 ExposureFlow 後台，產品複雜度會過高。

### 4.5 ExposureFlow 適合的採用方式

ExposureFlow 不建議短期併入 ForgeBase，也不建議以完整外部產品形式串接給客戶使用。比較合理的是將其關鍵思想重寫成 ForgeBase 原生 Capture Intelligence。

#### 路線 A：ForgeBase-native Capture Intelligence

```text
ForgeBase
  - 連 GSC/SERP
  - 建 CaptureOpportunity / SeoHealthIssue / TopicGap
  - 顧問在 ForgeBase Growth Ops 後台核准 decision / roadmap
  - 客戶只看 leads dashboard、RFQ、跟進狀態
```

這最符合目前「我方操作、客戶看成果」的商業模式。

#### 路線 B：選擇性重寫 connectors / indexability

先不導入整個 ExposureFlow，而是挑出 ForgeBase 需要的底層能力重新實作：

- GSC sync connector。
- SERP snapshot connector。
- sitemap diagnosis。
- published noindex audit。
- coverage check。
- URL safety / allowlist。

這些可以補強 ForgeBase Capture 的「上線後能否被 Google 發現與持續收錄」。

## 5. 直接比較

| 面向 | ContentFlow | ExposureFlow | 判斷 |
|---|---|---|---|
| 主要定位 | SEO 內容閉環 / 文章工廠 | 顧問式自然曝光營運系統 | 不同層級 |
| 短期作為藍本重寫 | 較容易 | 較難 | ContentFlow 先行 |
| 可參考的 ForgeBase adapter | 已打現有 `/api/v1/content/*`，可作契約參考 | adapter 存在但未接線，且 API 假設不符 | ContentFlow 更接近 |
| Capture 內容生成 | 強 | 中強，但更偏 opportunity-driven | ContentFlow 先重寫 |
| GSC/SERP 機會判斷 | 有，但以選題/refresh 為主 | 很強，完整 Opportunity/Decision | ExposureFlow 應重寫進 ForgeBase |
| Indexability | 有監控能力 | 很強，sitemap/noindex/coverage/job 化 | ExposureFlow 應重寫進 ForgeBase |
| 顧問工作流 | 弱 | 很強 | ExposureFlow 概念值得吸收 |
| 運維複雜度 | 中 | 高 | 重寫可降低長期複雜度 |
| 與 ForgeBase 產品模型互補 | blog/knowledge center 互補 | SEO ops/顧問代操互補 | 兩者都只作設計來源 |
| 直接合併或長期 API 依賴 | 不建議 | 更不建議 | 都應 ForgeBase-native 化 |

## 6. 我的建議

### 6.1 不建議二選一後全部整合，也不建議長期 API 依賴

這兩個專案不是同一層的東西。

ContentFlow 是內容生產與 refresh 引擎。ExposureFlow 是曝光分析、顧問決策與營運工作台。若硬把其中一個整庫併入 ForgeBase，或讓 ForgeBase 長期依賴兩個外部 runtime，會帶來：

- 雙 ORM。
- 雙 migration。
- 雙租戶模型。
- 雙 Admin UI。
- 雙內容 pipeline。
- 雙排程系統。
- 更多 secrets 與部署維護面。

ForgeBase 目前最需要的是把 Capture、Intent、Conversion 做成單一 Leads Growth 作業系統，不是再引入另一個完整 SaaS 核心。

### 6.2 短期建議：先重寫 ContentFlow 的核心能力

短期最務實的路線是：

```text
ForgeBase-native SEO Content Ops
  → 生成 blog_post / knowledge article
  → 寫入 ForgeBase PageBrief + Page
  → 我方 Growth Ops 後台審核
  → ForgeBase Web 渲染 + sitemap 收錄
  → 歸因到 RFQ / Lead Quality / Sales follow-up
```

原因：

1. ContentFlow 的設計最能補上 blog/news/knowledge center 與 SEO 長文。
2. ContentFlow 的 ForgeBase publisher 可作為資料契約參考。
3. 重寫成 ForgeBase-native 後，內容、審核、sitemap、RFQ 歸因都在同一個系統內。
4. 不會干擾 ForgeBase 既有 Product/Application/FAQ/RFQ 主線。

短期應做的 ForgeBase 改造：

1. 建立動態 blog/news listing route。
2. 建立 blog_post detail route，渲染 `Page.body`、`structured_data`、SEO title/description。
3. sitemap 加入 published pages，尤其是 `page_type == "blog_post"`。
4. 確認 `Page.structured_data` 的 JSON-LD 在前台能安全渲染。
5. 建立 `content_source = "forgebase_native"` 與 generation/audit log。
6. 增加 ContentFlow-inspired publish gate，而非直接使用 ContentFlow runtime。
7. 建立 content-to-lead attribution：文章 → CTA → product/application → RFQ。

### 6.3 中期建議：重寫 ExposureFlow 的 indexability 與 opportunity 能力

ContentFlow 能補「內容生產」，但 ForgeBase 還是需要知道：

- 哪些頁沒有被 sitemap 收錄。
- 哪些 published page 被 noindex 擋住。
- 哪些 URL 在 GSC coverage 有問題。
- 哪些 query 有曝光但 CTR 低。
- 哪些 topic 有需求但 ForgeBase 尚未覆蓋。

這部分 ExposureFlow 更強。

中期可以有兩種做法：

1. **先重寫 connectors/indexability**
   - 把 ExposureFlow 的 indexability connector 與 diagnosis 思路重寫到 ForgeBase API。
   - 做成 ForgeBase Admin 的 SEO Health / Capture Health 頁。

2. **再重寫 opportunity / roadmap**
   - 在 ForgeBase 建 `CaptureOpportunity`、`SeoHealthIssue`、`TopicGap`、`GrowthRoadmapItem`。
   - 我方顧問在 ForgeBase Growth Ops 後台操作。
   - 客戶只看摘要、Leads、RFQ 與跟進狀態。

### 6.4 長期建議：分成兩條產品線

長期不要把 ForgeBase 變成 ExposureFlow，也不要把 ExposureFlow 變成 ForgeBase。

比較清楚的產品分工是：

```text
ForgeBase
  = 外銷製造商 RFQ Growth OS
  = 建站、產品內容、Capture、Intent、Conversion、RFQ

ContentFlow
  = SEO Content Ops 設計參考
  = 文章生產、refresh、publish safety、GSC 回饋的藍本

ExposureFlow
  = SEO / Exposure Consultant OS 設計參考
  = 顧問代操、opportunity、decision、roadmap、indexability 的藍本
```

ForgeBase 會成為單一 Growth Ops 系統；ContentFlow / ExposureFlow 保留為設計參考與原型來源，而不是正式 runtime。

## 7. 建議原生實作階段

### Phase 0：產品邊界與資料模型定義

目標：不要先寫 code，先定義 ForgeBase-native Growth Ops 的責任邊界與資料模型。

要定義：

- 哪些 content type 屬於 Growth Ops 管理。
- 內容生成一律進 draft 還是可進 publish-ready。
- 顧問操作權限與客戶可見權限如何切分。
- locale 如何映射。
- URL route 如何產生。
- sitemap 如何收錄。
- JSON-LD 如何渲染。
- 失敗與重試如何處理。
- SEO 任務如何歸因到 Leads / RFQ。

產出：

- `FORGEBASE_GROWTH_OPS_ARCHITECTURE.md`
- `FORGEBASE_BLOG_NEWS_ARCHITECTURE.md`
- `FORGEBASE_CAPTURE_INTELLIGENCE_SCHEMA.md`

### Phase 1：ContentFlow-inspired SEO Content Ops

目標：參考 ContentFlow，先在 ForgeBase 原生實作 SEO 文章與 refresh 的最小閉環。

工作：

1. ForgeBase 補 blog_post 前台路由與 sitemap。
2. 新增 `SeoContentTask` / `ContentOpportunity`。
3. 參考 ContentFlow pipeline 實作 topic → brief → draft → SEO check → publish gate。
4. 由我方顧問在 ForgeBase Growth Ops 後台審核。
5. 發布後確認 sitemap、canonical、JSON-LD、meta tags。
6. 追蹤文章 → CTA → product/application → RFQ 的路徑。

驗收：

- ForgeBase 原生任務可建立 PageBrief。
- ForgeBase 原生 pipeline 可建立 Page draft。
- 我方顧問可在 Growth Ops 後台審核。
- 發布後 Web 能渲染。
- sitemap 包含該 URL。
- Google rich result/schema 不報錯。
- 該頁的 CTA / RFQ 歸因可追蹤。

### Phase 2：ContentFlow-inspired refresh / GSC loop

目標：不只寫新文，也能更新舊文。

工作：

1. ForgeBase 原生讀取既有 `blog_post`、product、application 的 GSC 表現。
2. 偵測排名下滑、CTR 低、內容過期與 cannibalization。
3. 建立 slug/page id 對照。
4. refresh 後進 draft/review，不直接覆蓋 published content。
5. 加入 change diff 或 revision log。

驗收：

- 排名下滑文章能被 ForgeBase 標記。
- 產生 refresh draft / revision。
- ForgeBase Admin 可比較舊版/新版。
- 發布後保留 canonical 與 slug。

### Phase 3：ExposureFlow-inspired indexability / SEO health

目標：補 ForgeBase 上線後健康監控。

工作：

1. 參考 ExposureFlow `connectors/indexability` 重新實作 ForgeBase-native checks。
2. 建 ForgeBase SEO Health dashboard。
3. 加入 sitemap health、noindex audit、coverage gap。
4. 對每 tenant 儲存 GSC/SERP 設定。
5. 產生 `SeoHealthIssue` 或 `CaptureIssue`。

驗收：

- ForgeBase 能顯示 sitemap 是否包含所有 published content。
- 能偵測 published page 被 noindex 或 robots 擋住。
- 能列出 GSC coverage gap。
- 能把問題轉成 admin action item。

### Phase 4：ExposureFlow-inspired 顧問營運工作流

目標：參考 ExposureFlow 的顧問工作流，在 ForgeBase 原生實作我方 Growth Ops cockpit。

工作：

1. 定義 `CaptureOpportunity`、`ActionDecision`、`GrowthRoadmapItem`。
2. 建立顧問內部工作台：待辦、核准、排程、報告。
3. 建立客戶可見 dashboard：Leads、RFQ、跟進狀態、成效摘要。
4. 建立每月 Growth Report。
5. 將 SEO task、content task、conversion task 都回扣到 Leads KPI。

驗收：

- ForgeBase 可對 tenant/site 產生 opportunity。
- 我方顧問可核准 decision。
- 內容與技術問題可成為 roadmap item。
- 客戶 dashboard 可看到成果與跟進狀態，而不是操作複雜 SEO 工具。

## 8. 我會怎麼選

### 8.1 若只能選一個先參考重寫

先選 **ContentFlow**。

理由：

- 它補的是 ForgeBase Capture 最直接可見的缺口：SEO 內容產出與 refresh。
- 它已有 ForgeBase publisher，可證明資料模型映射方向。
- 它的核心能力較容易重寫成 ForgeBase-native 模組。
- 它不需要 ForgeBase 立刻採用新的租戶模型或顧問工作台。

### 8.2 若目標是打造 SEO 顧問服務

參考 **ExposureFlow** 的顧問工作流與 intelligence，但重寫在 ForgeBase。

理由：

- 它的顧問工作流、Opportunity、Decision、Roadmap、Indexability 比 ContentFlow 更完整。
- 它適合顧問或代理商團隊代操多個 ForgeBase 客戶。
- 但它的產品模型太重，不適合作為 ForgeBase 的外部 runtime 或客戶可見工具。

### 8.3 最推薦方案

我最推薦的不是單選，而是分層：

```text
第一層：ForgeBase 本體
  - B2B 製造業網站、產品模型、RFQ、Intent、Conversion

第二層：ContentFlow-inspired native module
  - SEO 文章、內容 refresh、GSC 回饋、publish safety

第三層：ExposureFlow-inspired native module
  - GSC/SERP opportunity、indexability、顧問決策、roadmap
```

短期先做第一層 + 第二層；中長期把第三層重寫成 ForgeBase Growth Ops，不再新增外部 runtime 依賴。

## 9. 風險與注意事項

### 9.1 不要讓兩套 AI 同時寫同一種內容

建議明確分工：

- ForgeBase AI：Product、Application、FAQ、Capability、PageBrief entity content。
- ContentFlow：blog_post、knowledge article、SEO guide、comparison article。
- ExposureFlow：opportunity、decision、roadmap、technical issue、topic gap。

### 9.2 所有生成內容都應預設 draft

無論能力參考自 ContentFlow 或 ExposureFlow，進 ForgeBase 都應先是 draft。正式發布應由：

- ForgeBase Admin 人工核准，或
- 明確通過 publish gate 並有 audit log。

### 9.3 顧問操作權限與客戶可見範圍必須先設計

即使不採用外部 runtime，ForgeBase-native Growth Ops 仍必須嚴格區分「我方顧問操作」與「客戶可見資訊」。建議：

- 我方顧問可建立 SEO task、content task、roadmap、publish review。
- 製造商客戶只看 dashboard、Leads、RFQ、跟進狀態與成效摘要。
- 所有 Growth Ops 資料都帶 `tenant_id`，不能用全域 project 或 URL 推斷租戶。
- 客戶可見內容需做權限裁切，避免看到內部策略、成本、AI prompt、未核准建議。

### 9.4 ForgeBase Web 必須先能承接內容

若前台沒有 blog route、sitemap、structured data 渲染，再好的內容系統也無法提升 Capture。

最低要求：

- `/news` 或 `/blog` listing。
- `/news/{slug}` 或 `/blog/{slug}` detail。
- sitemap 收錄。
- canonical。
- JSON-LD。
- locale route。
- noindex 狀態處理。

### 9.5 避免把顧問操作複雜度暴露給 ForgeBase 客戶

外銷製造商客戶的主需求是看見詢價、追蹤跟進、理解成效，不需要操作 SEO 顧問後台。因此 ForgeBase 應有兩層介面：

- **Growth Ops 介面**：我方顧問使用，包含 Capture opportunity、content task、SEO health、roadmap、publish review。
- **Client Dashboard / Leads CRM 介面**：客戶使用，只呈現 Leads、RFQ、跟進狀態、頁面成效與必要建議。

## 10. 建議新增文件與後續工作

建議後續在 ForgeBase 補三份文件：

1. `FORGEBASE_EXTERNAL_CONTENT_CONTRACT.md`
   - 修訂為 `FORGEBASE_NATIVE_GROWTH_OPS_ARCHITECTURE.md`，定義 ContentFlow/ExposureFlow 設計如何被原生化到 ForgeBase。

2. `FORGEBASE_BLOG_NEWS_ARCHITECTURE.md`
   - 定義 blog_post/page route、sitemap、JSON-LD、locale、canonical。

3. `FORGEBASE_SEO_OPERATIONS_ROADMAP.md`
   - 定義從 ContentFlow-inspired Content Ops 到 ExposureFlow-inspired Capture Intelligence 的原生實作路線。

## 11. 最終建議

目前最適合 ForgeBase Capture 階段的是 **先參考 ContentFlow，重寫 ForgeBase-native SEO Content Ops**。

它能最快把 ForgeBase 從「有 SEO 基礎設施與 B2B 實體內容」推進到「有持續 SEO 內容運營」。但正式產品能力應在 ForgeBase 內原生實作，而不是長期依賴 ContentFlow runtime。

ExposureFlow 則是更大的長期能力：它能讓 ForgeBase 未來提供顧問式 SEO/曝光營運，但短期不適合直接接入，應先重寫它的 indexability、GSC/SERP、Topic Graph、Opportunity/Decision/Roadmap 思路，形成 ForgeBase-native Capture Intelligence。

一句話：

**先參考 ContentFlow 重寫內容生產與 refresh；再參考 ExposureFlow 重寫曝光診斷與顧問決策；ForgeBase 成為我方操作的 RFQ Leads Growth Ops，而客戶只使用儀表板與 Leads CRM。**
