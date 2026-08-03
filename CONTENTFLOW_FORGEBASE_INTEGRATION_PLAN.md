# ContentFlow ↔ ForgeBase 完整串接清單計畫

確認日期：2026-08-03  
修訂：2026-08-03（兩產品獨立＋可選串接為**長期**架構；補齊契約／租戶／媒體／快取／治理／KPI）  
狀態：待執行  
完備度聲明：本文件為**可開工的營運＋工程計畫**；API 欄位與錯誤碼以 [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md) 為準。

### 前提決策（現行）

1. **ContentFlow 與 ForgeBase 是兩個獨立產品**，各自發展、各自擁有租戶；互不合併 monorepo，也不互相「吃掉」對方核心。
2. 兩邊租戶集合**重疊但不必相等**：不是每個 CF 租戶都要掛 FB；不是每個 FB 租戶都要掛 CF。
3. 當客戶／案件需要「CF 做 SEO Ops ＋ FB 做站點／Intent／RFQ」時，以**可選、正式的 API 串接**連接（CF 視 FB 為一等 publisher，與 WP／Generic API 並列）。
4. 串接是**長期產品能力**，不是過渡到 ForgeBase-native 重寫 CF 的跳板。
5. 我方顧問可同時操作兩產品；製造商客戶在 FB 場景只看儀表板／Leads／CRM，不操作 CF Admin。

## 相關文件（內部連結）

| 文件 | 說明 |
|------|------|
| [DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md](./DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md) | **主策略**（Leads／產品方向） |
| [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md) | **發佈 API 契約**（本計畫 §3.1 定稿稿） |
| [SEO_CAPTURE_INTEGRATION_EVALUATION.md](./SEO_CAPTURE_INTEGRATION_EVALUATION.md) | CF／EF 評估與決策沿革 |
| [FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md](./FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md) | FB P0／P1 工程修復 |

---

## 0. 目標與邊界

### 0.1 串接完成的定義（Done）

對**有啟用串接**的那一組（CF project ↔ FB tenant）同時滿足：

1. ContentFlow 可穩定：選題 → 產文 → 審核 → 發佈／更新到該 ForgeBase 租戶。
2. 文章在該租戶 ForgeBase **前台可開、可被 sitemap 收錄、URL 正確**（官網網域，不是 API 網域）。
3. ContentFlow 線上驗證能抓到真實前台頁；低風險修復（重送 meta、請求索引）對該 FB connector 生效。
4. 顧問有明確作業：對照表／開通向導說明哪個 CF project 對哪個 FB tenant／站。
5. 至少能追到：CF 文章 → ForgeBase page →（理想）訪客／RFQ 來源歸因的最小閉環。

未串接的純 CF 租戶、純 FB 租戶**不受本 Done 約束**，各自獨立營運。

### 0.2 產品定位與職責

| 產品 | 定位 | 租戶 | 本串接中的角色 |
|------|------|------|----------------|
| **ContentFlow** | 獨立 SEO 內容營運／control-plane 產品 | 自有多租戶（可接 WP／Generic／FB／其他） | 生產與優化內容；經 `ForgeBasePublisher` 推出 |
| **ForgeBase** | 獨立 B2B RFQ Growth OS／製造業站＋Leads | 自有多租戶 | 接收／呈現文章；Intent、RFQ、客戶成果面 |
| **串接本身** | 跨產品整合能力（可選 SKU／開通項） | 僅「需要兩邊」的客戶才建立對照 | 契約＋開通＋健康檢查＋歸因 |

| 系統 | 負責 | 不負責 |
|------|------|--------|
| **ContentFlow** | 經營詞、Opportunity、產文／refresh、SEO QA、排程、GSC／GA4、健檢、低風險修復、（對已串接站）發佈 | FB 的 RFQ／CRM；未串接站的 FB 行為 |
| **ForgeBase** | 多租戶官網、Page、sitemap／schema、Intent、RFQ／Leads、客戶儀表板、（對已串接）接收 CF 內容 | 重做整台 CF；替未購 CF 的租戶提供完整 SEO 工廠 |
| **顧問／Growth Ops** | 按客戶組合操作：純 CF／純 FB／CF+FB | 把 CF Admin 交給製造商客戶（FB 場景） |

### 0.3 長期架構（兩產品獨立）

```text
ContentFlow 租戶池                    ForgeBase 租戶池
┌─────────────────────┐              ┌─────────────────────┐
│ CF-only 客戶        │              │ FB-only 客戶        │
│ CF→WordPress        │              │ 手動／自有內容      │
│ CF→Generic API      │              │                     │
│ CF→ForgeBase  ←—————│—— 可選串接 ——│→ 被選定的 FB tenant │
└─────────────────────┘              └─────────────────────┘
         ↑ 稀疏對照：只有「同時使用兩邊」才建連線
         ↑ 隨「串接客戶數」線性成長，不是 |CF|×|FB| 全連接
```

**長期優化方向（在獨立產品前提下）：**

1. 把 ForgeBase 做成 CF 的**一等 publisher**（能力對齊 Generic API 合理子集）。  
2. 把「開通串接」做成**可規模化流程**（對照、token、health、site_url），降低每多一個串接客戶的人肉成本。  
3. 契約穩定版本化（[CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md)），兩邊可各自發版。  
4. **明確不做：** 把 CF 核心抄進 FB、或把 FB 核心抄進 CF，作為「消滅雙產品」的路線。

### 0.4 非目標

- 不合併兩個 monorepo／兩個產品線。  
- 不以「租戶變多 → 收斂成單一 native 產品」為預設演進。  
- 不要求全部 CF 租戶或全部 FB 租戶啟用串接。  
- 不把 CF Admin 暴露給製造商客戶（在 FB 交付場景）。  
- 不把 ExposureFlow 納入本串接範圍（可另開）。  
- 不宣稱「Phase 2 做完＝CF 每一項能力在 FB 上等價」（見 §0.5）。

### 0.5 「完整串接」vs「CF 全功能開通」

| 層級 | 含義 | 本計畫覆蓋 |
|------|------|------------|
| A. 發佈閉環 | 產文→審核→該 FB 租戶前台可開→sitemap | Phase 0–1 |
| B. 站方能力對齊 | meta 重送、驗證、refresh、unpublish、redirect | Phase 2 |
| C. CF 控制面 | 經營詞、排程、GSC、健檢等 | 在 **CF 產品內**；與是否 FB 無關 |
| D. 進階站方動作 | 內鏈 bulk、merge/301 | 可選；FB 不支援則降級 |
| E. 規模化開通 | 多組 CF↔FB 對照的自動化／範本 | Phase 4 強化 |

**結論：** 串接完善 = 對「有連線的客戶」做到 A＋B＋（按需）D，並用 E 支撐租戶成長；C 永遠屬於獨立產品 CF。

---

## 1. 現況盤點（2026-08-03）

### 1.1 已有

| 項目 | 位置 | 說明 |
|------|------|------|
| CF `ForgeBasePublisher` | `ContentFlow/.../publishers/forgebase.py` | brief → page → publish 三步 |
| CF project connector | `project_integrations.resolve_forgebase_settings` | 專案級 URL／token／health |
| CF 發佈路徑 | Strategic Agent／API `platform=forgebase` | 可選平台 |
| FB content API | `/api/v1/content/briefs`、`/pages`、`/pages/{id}/publish` | CRUD＋發佈 |
| FB service account | `X-API-Key` + `SERVICE_ACCOUNT_TOKENS` | 機制存在 |
| FB Page `blog_post` | `Page.page_type` | 模型支援 |
| FB 動態頁渲染 | `/[locale]/[slug]` + `FlexiblePageRenderer` | 僅 locale 路徑較完整 |

### 1.2 缺口（阻斷完整串接）

| ID | 缺口 | 影響 | 優先 |
|----|------|------|------|
| G1 | `/news` 靜態假資料；無文章列表 | 找不到文 | P0 |
| G2 | `sitemap.ts` 未收 `blog_post`／Page | Google 難發現 | P0 |
| G3 | 預設英文站無 `/blog/{slug}` | 外銷 en 路徑不通 | P0 |
| G4 | CF publisher 硬編 `zh-tw`；URL 用 API base | 語系／公開 URL 錯 | P0 |
| G5 | FB publisher 無 `update_meta`／redirect／unpublish 能力宣告 | 驗證自修空轉 | P1 |
| G6 | 無 CF project ↔ FB tenant 對照與 smoke | 不能正式營運 | P0 |
| G7 | 內容 → RFQ 歸因未建 | 難證 Leads 功效 | P1 |
| G8 | secrets／service account 營運文件不足 | 配錯或外洩 | P0 |
| G9 | API Contract **草稿已有、待簽核並與程式對齊**（idempotency／brief／關聯 ID） | 未對齊則重發仍可能髒資料 | P0 |
| G10 | **租戶綁定矩陣未寫死**（token→tenant→domain→SiteProfile） | 跨租戶寫入風險 | P0 |
| G11 | Publisher **未傳 hero／og**；圖床／R2 未約定 | 破圖、驗證 fail、社群預覽差 | P0 |
| G12 | HTML **消毒／XSS** 與 ISR **revalidate** 未列必做 | 安全與「發了看不到」 | P0 |
| G13 | 文章→Product／Application **內鏈與 CTA 規格**不足 | 製造業轉換弱 | P1 |
| G14 | FB Admin PageBrief／AI 產文與 CF **雙軌衝突**未治理 | 搶 slug、兩套真相 | P1 |
| G15 | 無 staging／rollback／跨系統 request_id | 出事難回滾、難追 | P1 |
| G16 | Go-Live 缺 **30／60 日業務 KPI** | 「能通」≠「有效」 | P1 |

---

## 2. 架構示意

```text
[顧問] ContentFlow Admin
          │
          │ 經營詞 / Opportunity / 產文 / 審核
          ▼
   ContentFlow Scheduler + Agents
          │
          │ ForgeBasePublisher (X-API-Key)
          ▼
   ForgeBase API  (tenant-scoped service user)
          │
          ├── Page (blog_post) draft → published
          ▼
   ForgeBase Web  /blog/{slug}  + sitemap + schema
          │
          ├── Tracking events (page_view, cta, rfq_*)
          ▼
   ForgeBase RFQ / Leads / 客戶儀表板
          ▲
          │ 回寫觀測（可選 Phase 3）
   ContentFlow Live Verification / GSC
          │ 抓前台 URL、meta、索引、CWV
          └── update_meta / indexing request → ForgeBase API
```

跨系統關聯建議：每次發佈帶 `X-Request-Id`（或 body／notes `cf:article:{id}`），兩邊 log 可對帳。  
本圖僅描述**已啟用串接**的路徑；純 CF／純 FB 租戶不走此圖。

---

## 3. 缺口補丁（完善必備，併入各 Phase）

### 3.1 API Contract（P0，開工前先定稿一頁）

正式實作前產出並維護 [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md)（本節摘要；細節以契約全文為準），至少包含：

| 主題 | 定案要求 |
|------|----------|
| 認證 | `X-API-Key`；token 綁定單一 FB user → 單一 `tenant_id` |
| 建立 | `POST /content/briefs` → `POST /content/pages`（status=draft） |
| 發佈 | `POST /content/pages/{id}/publish` |
| 更新全文 | `PATCH /content/pages/{id}`（refresh） |
| 更新 meta | `PATCH` 或專用 endpoint；**允許只送 seo_*** 欄位 |
| 下架 | `POST .../unpublish` |
| Redirect | 既有 redirects API；CF service account 可寫 |
| Idempotency | 同 `(tenant_id, locale, slug)`：**更新既有 page**，不新建第二筆；brief 策略見下 |
| Brief 策略 | 首發可建 brief；refresh **重用** `page.brief_id` 或跳過新建，禁止每發一篇堆一個孤兒 brief |
| 錯誤碼 | `401` 認證、`403` 租戶、`409` slug 衝突、`422` 欄位、`429` 限流、`5xx` 可重試 |
| 重試 | 僅對 429／5xx；409／422 不重試；CF 需指數退避 |
| 公開 URL | 回傳必須是 `{site_url}/blog/{slug}`，禁止 API host |
| 關聯 ID | **試點定案：Brief `notes` 前綴 `cf:article:{id}`**；正式欄位列為後續可選增強 |

### 3.2 租戶綁定矩陣（P0）— 僅「有串接」的對

**原則：** CF 全量租戶、FB 全量租戶各自增長；矩陣只登錄**啟用跨產品連線**的列。禁止為無關租戶建空連線。

每條串接一列（不是每個產品租戶一列）：

| 欄位 | 例 |
|------|-----|
| 串接 ID／名稱 | `link-acme-2026` |
| CF `project_id` / 名稱 | |
| FB `tenant_id` / 名稱 | |
| `api_base_url` | `https://api...` |
| `site_url`（公開） | `https://www.client.com` |
| SiteProfile / 自訂網域 | |
| Service user id + token 別名（不寫明文） | `sa-acme` |
| 預設 `locale` | `en` |
| GSC property | `sc-domain:client.com` |
| 營運模式 | `reviewed_publish` |
| auto_remediation | meta 開／index 關（試點） |
| 狀態 | staging／production／disabled |

**驗收：** 用租戶 A 的 token 寫入租戶 B 的 slug → 必須 403／404。未出現在矩陣的 CF／FB 租戶營運不受影響。

### 3.3 媒體（Hero／OG）（P0）

| # | 工作項 | 驗收 |
|---|--------|------|
| M1 | CF `ForgeBasePublisher` 傳送 `hero_image_url`／`og_image_url`（對齊 Generic API） | FB Page 欄位有值 |
| M2 | 約定圖必須是 **公開 HTTPS URL**（CF R2／CDN 或 FB Assets） | 前台 `<img>` 200 |
| M3 | 無圖策略：允許發佈但 verification 標 `no_img`；或試點強制有 hero | 文件寫明 |
| M4 | 破圖／私有桶：verification 失敗 → 通知，不靜默 | 有告警 |

### 3.4 HTML 消毒與快取失效（P0）

| # | 工作項 | 驗收 |
|---|--------|------|
| S1 | FB 寫入或渲染前對 CF HTML **sanitize**（允許基本排版標籤，禁 script／on*） | XSS payload 被剝除 |
| S2 | 發佈／更新／meta／unpublish 後呼叫 **On-Demand Revalidation**（path=`/blog/{slug}`、`/blog`、sitemap） | 60 秒內前台非舊快取 |
| S3 | 若 Web 多實例／CDN：文件化 purge 責任 | staging 實測通過 |

### 3.5 製造業內鏈與 CTA（P1）

| # | 工作項 | 驗收 |
|---|--------|------|
| L1 | 寫作／發佈規範：每篇至少 1–3 條內鏈至 Product／Application／Certification（真實 FB 路徑） | 前台連結 200 |
| L2 | 文章頁固定 RFQ CTA 區塊＋可選 Dynamic CTA | 可進 RFQ |
| L3 | CF 選題避開與高價值產品頁 **意圖自蝕**（同主詞優先 refresh 產品頁而非另開 blog） | SOP 一條 |

### 3.6 雙軌內容治理（P1）— 僅已串接的 FB 租戶

| 規則 | 定案 |
|------|------|
| SEO 長文／buying guide／knowledge（已串接租戶） | **由 CF** 生產並經 publisher 進該 FB tenant |
| 產品／應用／認證／比較實體 | **僅 FB**（與是否串接無關） |
| 該 FB 租戶 Admin「AI 產 blog_post」 | 串接啟用期間 **停用或標實驗**，避免與 CF 搶 slug |
| 未串接的 FB 租戶 | 可繼續用 FB 既有內容工具，不受上列限制 |
| 未串接的 CF 租戶 | 繼續發 WP／Generic 等，與 FB 無關 |
| 單一真相（已串接 blog） | 內容修改以 CF refresh 為主；FB 手動改須登記 |

### 3.7 Staging、Rollback、觀測（P1）

| # | 工作項 | 驗收 |
|---|--------|------|
| O1 | 強制 staging：CF staging project → FB staging tenant／站 | 生產前至少 3 篇走完 |
| O2 | Rollback：unpublish +（若換 slug）redirect 回舊 URL；Runbook 逐步 | 演練一次 |
| O3 | 兩邊 log 可依 `contentflow_article_id` / `page_id` 對帳 | 抽一筆可串起 |
| O4 | 發佈失敗／驗證高嚴重度 → Telegram／Slack | 15 分鐘內可知 |
| O5 | 分析真相：前台行為與 RFQ 以 **FB** 為準；排名／query 以 **CF←GSC** 為準 | SOP 寫明，避免雙 GA 互打 |

### 3.8 成功指標（技術 Go-Live ≠ 有效）

**技術 Go-Live（§6）通過後起算：**

| 窗口 | 指標（試點可調數字） |
|------|----------------------|
| 30 日 | ≥ 8 篇 reviewed 發佈；Live Verification 通過率 ≥ 80%；sitemap 全收錄 |
| 60 日 | ≥ 1 次「blog `source_page` → RFQ」；經營詞庫內機會有執行紀錄 |
| 持續 | 顧問週報：新發／refresh／驗證異常／內容來源 RFQ 數 |

未達 30 日門檻 → **不開下一條生產串接**，先修品質與驗證。

---

## 4. 分階段清單計畫

### Phase 0 — 對接契約與環境（約 3–5 人日）

目標：兩邊「講同一種話」，能對單一租戶打通認證與 health。**含 §3.1–3.2。**

| # | 工作項 | 負責端 | 驗收標準 |
|---|--------|--------|----------|
| 0.1 | 選定試點：1 個 ForgeBase tenant + 1 個 CF project | Ops | §3.2 矩陣填滿 |
| 0.2 | FB 建立 content_editor 級 service user，`SERVICE_ACCOUNT_TOKENS` | FB | `X-API-Key` 可 `GET /pages?limit=1` = 200 |
| 0.3 | CF 設定 forgebase integration（專案級優先於全域 env） | CF | diagnostic = `healthy` |
| 0.4 | Token 輪替 Runbook；禁止進 git；一租戶一 token | Ops | 文件一頁 |
| 0.5 | 公開 URL 規則定案 | 雙方 | `{site_url}/blog/{slug}` 等 |
| 0.6 | Locale 策略定案 | 雙方 | 外銷試點預設 `en` |
| 0.7 | 欄位對照＋**API Contract 簽核**（§3.1／契約全文） | 雙方 | 契約狀態改「已簽核」 |
| 0.7b | **實測** `GET /content/pages?slug=&locale=&page_type=blog_post` | FB | 回傳預期 page 或空列表；寫入契約「已驗證」 |
| 0.8 | 跨租戶否定測試 | 雙方 | A token 寫 B → 失敗 |
| 0.9 | Staging 環境對照列進矩陣 | Ops | staging 列存在 |

**Phase 0 Exit：** Contract 初稿簽核；CF health 綠；curl 可建 draft；跨租戶寫入失敗。

---

### Phase 1 — 發佈閉環最小可用（約 7–12 人日）

目標：CF 核准文章 → FB 前台可開、可進 sitemap。**含 §3.3–3.4。** 這是串接 MVP。

#### 1A. ForgeBase 前台與 SEO 基礎

| # | 工作項 | 驗收標準 |
|---|--------|----------|
| 1.1 | 公開路由：`/blog/[slug]` 與 `/[locale]/blog/[slug]` | published 200；draft 404 |
| 1.2 | `/blog` 列表；`/news`→`/blog` 301 | 列表吃 API |
| 1.3 | `sitemap.ts` 納入 published blog（含 locale） | 含文章 URL |
| 1.4 | metadata：title／description／canonical／og／JSON-LD | 與 Page 一致 |
| 1.5 | unpublish／noindex 與 sitemap 行為 | 下架不可被索引入口找到 |
| 1.6 | 文章 RFQ CTA（固定＋可選 dynamic） | 可進 RFQ 且帶 source |
| 1.6b | **HTML sanitize**（§3.4 S1） | XSS 測試通過 |
| 1.6c | **Revalidate API**（§3.4 S2） | 發佈後前台迅速更新 |

#### 1B. ContentFlow Publisher 修正

| # | 工作項 | 驗收標準 |
|---|--------|----------|
| 1.7 | locale 來自專案設定，禁止寫死 `zh-tw` | en 文進 en page |
| 1.8 | `publish_url`／`get_post_url` 用 **site_url** | 官網網域 |
| 1.9 | slug 規則＋衝突處理（409→改 slug） | 不靜默蓋他頁 |
| 1.10 | Markdown→HTML；前台渲染正常 | 標題／連結／列表 OK |
| 1.10b | 傳送 **hero／og**（§3.3） | 前台有圖或符合無圖策略 |
| 1.10c | Idempotent upsert＋brief 不重複堆（§3.1） | 同 slug 重發=更新 |
| 1.10d | 寫入 `contentflow_article_id` 關聯 | 兩邊可對帳 |
| 1.11 | 寫回 CF `forgebase_id` + `publish_url` | CF 可點前台 |
| 1.12 | E2E smoke（staging 先、再試點） | checklist 打勾 |

**Phase 1 Exit：** Staging 至少 3 篇、試點至少 1 篇前台可開且進 sitemap；sanitize／revalidate 實測通過。

---

### Phase 2 — 站方能力對齊（驗證／修復／refresh）（約 7–12 人日）

目標：讓 CF 驗證與低風險修復**打在已串接的 ForgeBase 租戶**上。對齊的是 §0.5 層級 B，不是把 CF 外圍 job 搬進 FB。

#### 2A. ForgeBase API

| # | 工作項 | 對應 CF | 驗收標準 |
|---|--------|---------|----------|
| 2.1 | Meta-only 更新契約／endpoint | `update_meta` | 不改 body 可改 meta |
| 2.2 | Unpublish 文件化給 CF | 降級／治理 | CF 可呼叫 |
| 2.3 | Redirect API 開給 service account | merge／換 slug | 可建 301 |
| 2.4 | Indexing：CF 直連或 FB 代打，文件定責 | auto remediate index | 職責清楚 |
| 2.5 | Health ping 穩定 | connector | diagnostic 綠 |

#### 2B. ContentFlow Publisher

| # | 工作項 | 驗收標準 |
|---|--------|----------|
| 2.6 | `update_meta()` | auto_remediate 不因 forgebase 跳過 |
| 2.7 | `capabilities` 誠實宣告 | 不支援的勿標 true |
| 2.8 | `update_post` + revalidate | refresh 後前台更新 |
| 2.9 | Verification 用 site_url+/blog/slug | 真實 HTTP／meta |
| 2.10 | 試點：meta 自修開、index 第二步、merge 執行器關 | log 可查 |

#### 2C. 營運（CF 控制面）

| # | 工作項 | 驗收標準 |
|---|--------|----------|
| 2.11 | `reviewed_publish` only | 無人值守亂發 |
| 2.12 | GSC sync + live verification；auto_pipeline 限量 | 無打爆 |
| 2.13 | 5–10 核准經營詞 | Opportunity 有建議 |
| 2.14 | GSC 綁定 FB 站網域 | 有資料 |
| 2.15 | §3.5 內鏈規範進寫作／審核 checklist | 抽樣達標 |
| 2.16 | §3.6 雙軌治理公告（FB blog AI 停用） | 團隊知悉 |

**Phase 2 Exit：** 產文＋發佈＋驗證＋meta 重送在試點跑通；capabilities 無虛報。

---

### Phase 3 — Leads 歸因與客戶成果面（約 5–8 人日）

| # | 工作項 | 負責端 | 驗收標準 |
|---|--------|--------|----------|
| 3.1 | tracking：`page_type=blog_post`、`page_id` | FB | 可依文聚合 |
| 3.2 | RFQ `source_page` 含 blog URL | FB | 可回溯 |
| 3.3 | Admin 可篩 blog→轉換 | FB | 顧問可用 |
| 3.4 | （可選）CF outcome 僅 observational | 雙方 | 不宣稱因果 |
| 3.5 | 客戶儀表板：上線篇數、內容來源 RFQ（粗） | FB | 無 CF 入口 |
| 3.6 | 週營運 SOP＋RACI（誰核准發佈／誰跟 RFQ） | Ops | 一頁 |
| 3.7 | §3.8 30／60 日 KPI 看板或表 | Ops | 開始計時 |

**Phase 3 Exit：** 能回答「內容有沒有帶來詢價」的最小版本；KPI 開始追蹤。

---

### Phase 4 — 硬化與多組串接擴展（約 5–8 人日）

目標：在**兩產品租戶各自成長**下，讓「新增一條 CF↔FB 連線」可複製、低人肉；不是把兩產品合併。

| # | 工作項 | 驗收標準 |
|---|--------|----------|
| 4.1 | 每條串接獨立 token；否定測試進回歸 | 跨租戶失敗 |
| 4.2 | Rate limit／idempotency 自動化測試 | CI 或週 smoke |
| 4.3 | 失敗通知穩定（含標明哪條 link／project／tenant） | 演練通過 |
| 4.4 | Contract tests（staging） | 可重複跑 |
| 4.5 | **開通 Runbook／檢查清單範本**：複製矩陣列＋health＋首篇 smoke | 新開一條串接可跟表完成 |
| 4.6 | （目標）開通輔助：文件或腳本產生 token 對照、驗證 site_url | 人日下降可量測 |
| 4.7 | **僅當該串接 30 日 KPI 達標** 才複製下一條生產串接 | 品質門檻 |
| 4.8 | 安全複核＋FB P0 tenancy 知情採用／並行修復 | 簽核 |
| 4.9 | Rollback 演練；停用串接（disabled）不影響兩側其他租戶 | 紀錄 |
| 4.10 | 明確：CF-only／FB-only 租戶不進矩陣、不跑 FB publisher | 抽樣確認 |

---

## 5. 建議執行順序（總覽）

```text
Week 1       Phase 0：矩陣 + Contract + 認證 + 跨租戶否定測試
Week 1–3     Phase 1：/blog + sanitize + revalidate + hero + upsert + staging smoke
Week 3–5     Phase 2：update_meta + verification + 經營詞/GSC + 雙軌治理
Week 5–6     Phase 3：歸因 + 客戶成果 + KPI 起算
Week 6+      Phase 4：硬化；開通範本；30 日達標後才下一條生產串接
```

**最窄可上線（仍須含補丁）：**  
Phase 0 全做 + Phase 1 全做（含 sanitize／revalidate／hero／upsert）+ Phase 2 的 2.1／2.6／2.9。  
不可省略 staging 至少 1 篇成功。

工時已較初版上調；若並行 FB P0 migration／tenancy，再加緩衝。  
**擴張計量單位是「串接連線數」**，不是 CF 或 FB 的總租戶數。

---

## 6. 驗收總表（Go-Live Gate）

### 6.1 技術 Gate（試點生產發第一篇前）

- [ ] §3.2 租戶矩陣填滿且 staging 列存在  
- [ ] §3.1 API Contract 初稿已簽核  
- [ ] CF connector `forgebase` = healthy  
- [ ] 跨租戶寫入否定測試通過  
- [ ] Staging ≥ 3 篇 E2E 成功  
- [ ] 生產發佈 1 篇 → `/blog/{slug}` = 200  
- [ ] URL 在 sitemap；title／meta 與來源一致  
- [ ] Hero／OG 符合策略；HTML sanitize 抽測通過  
- [ ] 發佈後 revalidate：不需手動清 CDN 即可看到更新  
- [ ] 文章 CTA → RFQ，`source_page` 可辨識  
- [ ] CF Live Verification 命中正確網域至少 1 次  
- [ ] （建議）meta 重送路徑驗證一次  
- [ ] Rollback：unpublish 演練一次  
- [ ] Runbook + RACI；客戶無 CF 帳號  
- [ ] §3.6 雙軌規則已公告  

### 6.2 有效 Gate（上線後，決定是否開下一條生產串接）

- [ ] 30 日：§3.8 篇數與驗證通過率達標  
- [ ] 60 日：至少 1 筆 blog→RFQ 可回溯（或書面解釋為何尚無並調整選題）  

---

## 7. 風險與緩解

| 風險 | 緩解 |
|------|------|
| 誤以為要合併兩產品 | §0 前提：獨立產品；串接可選且為長期能力 |
| 對所有租戶強行建連線 | 矩陣只含有需求的 link；CF-only／FB-only 不進 |
| 雙系統操作摩擦（已串接客戶） | SOP：SEO 在 CF、Leads 在 FB；客戶不碰 CF |
| 串接數上升導致人肉爆增 | Phase 4 開通範本／自動化；契約穩定 |
| 改 CF 影響非 FB 生產站 | publisher 分支隔離；禁全域 FORGEBASE env；專案級設定 |
| FB tenancy／Contact P0 | 試點單串接；並行修；知情簽核 |
| 快取舊頁 | Phase 1 必做 revalidate；Go-Live 實測 |
| XSS | sanitize 必做 |
| 孤兒 brief／重複 page | idempotent upsert + brief 策略 |
| 跨租戶寫入 | 矩陣 + 否定測試 |
| auto_publish／merge 誤傷 | reviewed_publish；merge executor 關 |
| URL／locale 錯 | Phase 0 鎖規則 |
| 雙軌搶 slug（已串接租戶） | §3.6 |
| 媒體破圖 | hero 契約 + verification |
| 「能通」當成功 | §3.8／§6.2 KPI |
| 工時低估 | 已上調；P0 並行再加 buffer |

---

## 8. 交付物清單

| 交付物 | 說明 |
|--------|------|
| 本計畫文件 | [CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md) |
| API Contract | [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md)（§3.1） |
| 主策略 | [DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md](./DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md) |
| 租戶綁定矩陣 | 含 staging／生產（§3.2） |
| 顧問週營運 Runbook + RACI | 選題、核准、驗證、Leads |
| 雙軌治理公告 | §3.6 |
| Smoke／Contract 測試清單 | Phase 1／2／跨租戶否定 |
| Rollback 演練紀錄 | |
| Go-Live 簽核 + 30／60 日 KPI 表 | §6 |

---

## 9. 與既有文件的關係

| 文件 | 關係 |
|------|------|
| [DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md](./DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md) | Leads 北極星；FB 產品方向；與本計畫交叉連結 |
| [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md) | 跨產品發佈契約全文 |
| [SEO_CAPTURE_INTEGRATION_EVALUATION.md](./SEO_CAPTURE_INTEGRATION_EVALUATION.md) | 歷史評估；現行以「兩產品獨立＋可選串接」為準 |
| [FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md](./FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md) | FB P0 並行；影響擴串接信心 |
| ContentFlow README §2.1–2.3 | CF 產品內經營詞／健檢／自修操作真相 |

---

## 10. 下一步（立即行動）

1. 填 §3.2 **第一條**試點＋staging 串接矩陣（不必動其他 CF／FB 租戶）。  
2. 確認 [CF_FB_PUBLISH_CONTRACT.md](./CF_FB_PUBLISH_CONTRACT.md) 與獨立產品前提一致。  
3. Phase 0.2–0.3＋0.8（token、health、跨租戶否定）。  
4. Phase 1：FB /blog＋sitemap＋sanitize＋revalidate；CF ForgeBasePublisher（locale／URL／hero／upsert）— **勿改現有 Generic／WP 生產專案設定**。  
5. Staging 3 篇通過 → 試點 1 篇 → Phase 2 update_meta／verification。  
6. 從該串接第一篇起算 §3.8 KPI；達標後用 Phase 4 範本開下一條連線。
