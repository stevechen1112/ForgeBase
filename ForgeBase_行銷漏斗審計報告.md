# ForgeBase 行銷漏斗審計報告

> 審計角度：數位行銷與 RevOps 實務
> 
> 審計方法：本報告只依據系統實際程式碼、API 行為、資料流與已驗證執行結果判斷，不引用專案規格文件作為成立依據。
> 
> 審計時間：2026-03-15

---

## 一、結論摘要

### 簡短結論

**ForgeBase 可以為企業建立可運作的 B2B 行銷漏斗。**

但要精準定義，它目前最成熟的是：

- 匿名訪客行為追蹤
- 意圖分數與階段判定
- 名單識別與 RFQ 收斂
- 業務端接手與後台分析

它已經不是單純官網 CMS，也不是只有漂亮 dashboard 的展示系統。

**它本質上是一套「官網驅動的需求擷取與轉單前漏斗系統」。**

若從企業級 MarTech 標準來看，它已具備中下漏斗核心能力，但尚未完成完整的營收閉環、ABM 編排、進階自動化與跨平台回傳。

### 最終判定

| 評估面向 | 判定 |
|---|---|
| 是否能建立企業行銷漏斗 | 可以 |
| 是否能支撐 B2B 官網導向的 lead generation | 可以 |
| 是否具備從匿名訪客到 RFQ 的可執行流程 | 可以 |
| 是否已達完整 enterprise funnel / revenue engine | 尚未完全達成 |

### 建議對外定位

最適合的對外描述是：

> ForgeBase 能把企業官網從展示型網站，升級成可追蹤、可評分、可辨識高意圖買家、可推進詢價與業務跟進的漏斗系統。

不建議直接對外說成：

> 已完整取代 HubSpot + Marketo + Salesforce + CDP + ABM 平台。

---

## 二、審計依據

本次判斷主要依據以下實作路徑：

- 前端追蹤 SDK：[web/src/lib/analytics.ts](web/src/lib/analytics.ts)
- 事件接收與 visitor/session 寫入：[api/app/api/v1/endpoints/events.py](api/app/api/v1/endpoints/events.py)
- 意圖分數引擎：[api/app/services/intent_scoring.py](api/app/services/intent_scoring.py)
- RFQ 與 contact 建立流程：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py)
- 分群判斷：[api/app/api/v1/endpoints/segments.py](api/app/api/v1/endpoints/segments.py)
- Nurture 流程：[api/app/api/v1/endpoints/nurture.py](api/app/api/v1/endpoints/nurture.py)
- Email 發送層：[api/app/services/email_service.py](api/app/services/email_service.py)
- 分析 API：[api/app/api/v1/endpoints/analytics.py](api/app/api/v1/endpoints/analytics.py)
- 後台意圖與頁面分析頁：[admin/src/app/(dashboard)/dashboard/intent/page.tsx](admin/src/app/(dashboard)/dashboard/intent/page.tsx)、[admin/src/app/(dashboard)/dashboard/page-analytics/page.tsx](admin/src/app/(dashboard)/dashboard/page-analytics/page.tsx)
- HubSpot / Google Ads / LinkedIn / Meta 等外部整合服務：[api/app/services/hubspot.py](api/app/services/hubspot.py)、[api/app/services/google_ads.py](api/app/services/google_ads.py)、[api/app/services/linkedin_service.py](api/app/services/linkedin_service.py)、[api/app/services/meta_conversions.py](api/app/services/meta_conversions.py)

---

## 三、漏斗地圖總覽

從數位行銷與 B2B 需求開發角度，ForgeBase 目前可拆成以下 8 層漏斗：

| 漏斗層 | 目標 | 目前狀態 |
|---|---|---|
| 1. Traffic Capture | 接住官網流量與行為事件 | 已完成 |
| 2. Behavior Intelligence | 將行為轉成可判讀訊號 | 已完成 |
| 3. Lead Identification | 把匿名流量轉成名單 | 已完成 |
| 4. Intent Qualification | 判斷誰更值得業務跟進 | 已完成 |
| 5. Conversion Engine | 推動 RFQ / Contact 轉換 | 已完成 |
| 6. Sales Handoff | 把高意圖名單送入業務流程 | 已完成 |
| 7. Nurture / Segmentation | 持續培育與細分人群 | 部分完成 |
| 8. Revenue Loop / ABM | 回寫營收、帳戶層整合與自動編排 | 未完整完成 |

---

## 四、逐層審計

### 1. Traffic Capture

### 系統是否能接住流量與行為？

**可以。**

程式碼顯示前端具備第一方追蹤能力：

- 使用第一方 visitor cookie `fb_vid`：[web/src/lib/analytics.ts](web/src/lib/analytics.ts#L58)
- 使用 sessionStorage 維持 session id：[web/src/lib/analytics.ts](web/src/lib/analytics.ts#L59)
- 事件會送到 `/api/v1/tracking/events`：[web/src/lib/analytics.ts](web/src/lib/analytics.ts#L57)
- 若存在 `gtag` 會平行送 GA4：[web/src/lib/analytics.ts](web/src/lib/analytics.ts#L93)

後端也確實接收並寫入事件：

- 單筆事件入口：[api/app/api/v1/endpoints/events.py](api/app/api/v1/endpoints/events.py#L191)
- 批次事件入口：[api/app/api/v1/endpoints/events.py](api/app/api/v1/endpoints/events.py#L342)
- 合法事件種類已明確定義：[api/app/api/v1/endpoints/events.py](api/app/api/v1/endpoints/events.py#L41)

可追蹤事件包含：

- page_view
- category_view
- product_view
- application_view
- faq_expand
- comparison_view
- spec_download
- cta_click
- form_start
- form_submit
- rfq_start
- rfq_submit
- return_visit
- session_depth_reached

### 行銷判讀

這表示 ForgeBase 已經不只是網站分析工具，而是具備把官網使用行為轉成漏斗訊號的底層能力。

### 可銷售說法

> 系統可把官網上的瀏覽、點擊、規格下載與詢價行為，轉成第一方行為資料，作為後續意圖判定與轉換優化基礎。

### 不應過度承諾

- 它不是廣告投放平台本身
- 它能承接流量，但不代表自己創造流量

---

### 2. Behavior Intelligence

### 系統是否能把行為變成可判讀意圖？

**可以。**

意圖分數規則已明確寫在程式內：

- 事件分數表：[api/app/services/intent_scoring.py](api/app/services/intent_scoring.py#L11)
- 階段門檻表：[api/app/services/intent_scoring.py](api/app/services/intent_scoring.py#L31)
- 分數對應階段函式：[api/app/services/intent_scoring.py](api/app/services/intent_scoring.py#L80)
- 升階是否要 alert：[api/app/services/intent_scoring.py](api/app/services/intent_scoring.py#L88)

目前 intent stage 為：

- cold
- warm
- hot
- sales_ready

這不是單純 UI 標籤，而是每次事件進來都會更新 visitor 狀態。

### 行銷判讀

這代表系統已具備基本 Lead Scoring / Buyer Intent 能力。對 B2B 官網來說，這是漏斗中段非常關鍵的一層。

### 可銷售說法

> 系統能根據訪客的真實互動行為，自動判讀意圖強弱，幫企業分辨誰只是路過、誰已經進入評估與詢價階段。

### 不應過度承諾

- 目前主體仍是 rule-based scoring
- ML scoring 有實作，但不是目前主流程核心

---

### 3. Lead Identification

### 系統是否能把匿名流量轉成名單？

**可以。**

RFQ 提交流程會：

- 解析 visitor_id：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L108)
- 依 email 去重或補強 Contact：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L124)
- 建立 RFQRequest：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L184)
- 建立 RFQ 與產品關聯：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L200)

後台也有 contact 與 visitor 的獨立視圖可以回看漏斗結果：[admin/src/app/(dashboard)/dashboard/intent/page.tsx](admin/src/app/(dashboard)/dashboard/intent/page.tsx#L51)

### 行銷判讀

這代表 ForgeBase 已經具備將匿名訪客逐步收斂成 identifiable lead 的能力。對製造業與 B2B 網站來說，這是漏斗能否產生商業價值的核心分界線。

### 可銷售說法

> 系統不只看流量，而是能逐步把流量轉成可跟進的聯絡人與 RFQ 商機。

### 不應過度承諾

- 它不是完整 CDP
- 目前識別仍以表單、email、visitor_id 關聯為主

---

### 4. Intent Qualification

### 系統是否能把名單分出優先順序？

**可以。**

RFQ 建立時會直接依 visitor 當下 intent_score 決定 priority：

- `>= 60` → urgent：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L177)
- `>= 30` → high：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L179)

後台也會顯示高意圖訪客與已識別聯絡人：[admin/src/app/(dashboard)/dashboard/intent/page.tsx](admin/src/app/(dashboard)/dashboard/intent/page.tsx#L79)

### 行銷判讀

這一層很重要，因為它讓系統不只是收件匣，而是具備「哪些線索該先處理」的判斷力。

### 可銷售說法

> 系統能自動把高意圖買家浮出水面，讓業務優先處理更可能成交的詢盤，而不是平均分配注意力。

### 不應過度承諾

- 目前還沒有完整機器學習驅動的 lead scoring 運營閉環
- 也沒有複雜多維度買家委員會判定

---

### 5. Conversion Engine

### 系統是否真的能推動轉換？

**可以，但以 RFQ / Contact 為主。**

系統至少有三個直接轉換機制：

- RFQ 表單提交：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L98)
- CTA 個人化選擇：[api/app/services/dynamic_cta.py](api/app/services/dynamic_cta.py#L28)
- 頁面 / 產品 / 應用分析回看轉換結果：[api/app/api/v1/endpoints/analytics.py](api/app/api/v1/endpoints/analytics.py#L52)

CTA 引擎雖然不算高度智慧，但已經會根據 stage 選擇不同 action priority：

- 規則定義：[api/app/services/dynamic_cta.py](api/app/services/dynamic_cta.py#L20)
- 對不同 stage 輸出不同 headline / variant：[api/app/services/dynamic_cta.py](api/app/services/dynamic_cta.py#L81)

### 行銷判讀

這意味著它可以把高意圖流量導向詢價、把中意圖流量導向下載或比較、把低意圖流量導向聯絡或基本互動，這就是典型漏斗推進機制。

### 可銷售說法

> 系統不是讓每個人看到同一個 CTA，而是會依據意圖強度，把訪客往更適合的下一步推進。

### 不應過度承諾

- 目前 CTA 更像 rule-based personalization，不是完整 AI-driven CRO engine
- 尚未看到成熟的多頁旅程式個人化內容編排

---

### 6. Sales Handoff

### 系統是否把高意圖轉給業務？

**可以。**

RFQ 建立後會非同步觸發：

- 路由：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L231)
- 通知：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L232)
- HubSpot 同步：[api/app/api/v1/endpoints/rfqs.py](api/app/api/v1/endpoints/rfqs.py#L233)

此外，HubSpot 整合不是假介面，而是有真實 REST API 實作：[api/app/services/hubspot.py](api/app/services/hubspot.py)

### 行銷判讀

這表示 ForgeBase 已經不是停留在 marketing visibility，而是有 marketing-to-sales handoff 能力。

### 可銷售說法

> 當高意圖訪客送出詢價後，系統會自動標註優先級、通知業務並同步到 CRM，縮短從表單到跟進的時間差。

### 不應過度承諾

- CRM 回寫閉環還不完整
- 目前更接近單向同步，不是雙向 lifecycle orchestration

---

### 7. Segmentation 與 Nurture

### 系統是否能做人群分群與後續培育？

**部分可以。**

分群方面：

- Segment CRUD 已存在：[api/app/api/v1/endpoints/segments.py](api/app/api/v1/endpoints/segments.py)
- Segment evaluate 會實際算出符合人數與 sample visitor_ids：[api/app/api/v1/endpoints/segments.py](api/app/api/v1/endpoints/segments.py#L204)
- 支援 `intent_stage`、`intent_score`、`country`、`tag`、`event_count` 條件：[api/app/api/v1/endpoints/segments.py](api/app/api/v1/endpoints/segments.py#L254)

Nurture 方面：

- sequence / steps / enrollments API 已存在：[api/app/api/v1/endpoints/nurture.py](api/app/api/v1/endpoints/nurture.py)
- 支援手動 enroll：[api/app/api/v1/endpoints/nurture.py](api/app/api/v1/endpoints/nurture.py#L280)
- 支援 process due steps：[api/app/api/v1/endpoints/nurture.py](api/app/api/v1/endpoints/nurture.py#L343)
- 依 delay_days 進行排程判定：[api/app/api/v1/endpoints/nurture.py](api/app/api/v1/endpoints/nurture.py#L451)
- 寄信透過 Resend / SendGrid：[api/app/services/email_service.py](api/app/services/email_service.py#L103)

### 行銷判讀

這表示 ForgeBase 已具備基礎 marketing automation 形態，但成熟度仍偏「可用 MVP」而非「高度編排平台」。

### 可銷售說法

> 系統已可根據名單條件做基本分群，並透過 nurture sequence 做後續教育與持續接觸。

### 不應過度承諾

- 尚未看到成熟的條件分支、頻控、抑制規則、複雜旅程編排
- 更像 sequence engine，不是完整 enterprise MAP

---

### 8. Revenue Loop / ABM / Enterprise Orchestration

### 系統是否具備完整企業級漏斗閉環？

**尚未完整。**

有一些相關能力已存在，但多數仍屬於擴充層或半完成：

- ML Intent Scoring 訓練與預測：[api/app/services/ml_intent.py](api/app/services/ml_intent.py)
- A/B Test 分流與轉換紀錄：[api/app/api/v1/endpoints/ab_test.py](api/app/api/v1/endpoints/ab_test.py)
- Google Ads Customer Match 同步：[api/app/services/google_ads.py](api/app/services/google_ads.py)
- LinkedIn Audience 同步：[api/app/services/linkedin_service.py](api/app/services/linkedin_service.py)
- Meta Conversions API：[api/app/services/meta_conversions.py](api/app/services/meta_conversions.py)
- IP to Company / 帳戶洞察：[api/app/services/ip_resolver.py](api/app/services/ip_resolver.py)、[api/app/api/v1/endpoints/ai_intelligence.py](api/app/api/v1/endpoints/ai_intelligence.py)

但從企業級標準看，仍缺少幾個關鍵：

- 成交金額 / revenue attribution 閉環
- CRM 雙向 lifecycle 回寫
- Account-level buying committee 聚合
- 進階自動化規則引擎
- 完整 ABM playbook orchestration

### 行銷判讀

這代表 ForgeBase 已經在往完整 RevOps / Revenue Funnel 前進，但現在更適合定位為「官網到詢價」的成長系統，而不是完整營收作業系統。

### 可銷售說法

> 系統已具備延伸到 CRM、廣告再行銷、AI 洞察與 AB test 的基礎能力，可作為後續企業級行銷技術堆疊的核心底座。

### 不應過度承諾

- 不應直接宣稱已具備完整 ABM 或完整 revenue operating system
- 不應宣稱已完整做到 closed-loop attribution

---

## 五、哪些部分已經足以支撐「企業行銷漏斗」這個說法

若回到最關鍵的商業問題：

> 這套系統真的可以為企業建立行銷漏斗嗎？

我的答案是：**可以，而且以下四段已經成立。**

### 1. 官網流量不是黑箱

訪客從首頁、分類頁、產品頁、FAQ、比較頁、CTA、下載、RFQ 的行為，都能被記錄並回溯。

### 2. 系統知道誰比較有可能成交

透過 intent score 與 stage，系統能把「只是看一眼的人」與「正在評估供應商的人」區分開來。

### 3. 高意圖會被往轉換推進

CTA、表單、RFQ、priority 都讓高意圖流量更容易進入業務流程。

### 4. 轉換後不是石沉大海

RFQ 會建立 contact、建立商機、進行 routing、通知與 CRM 同步。

這四點成立，就足以支撐「它已經是一套可用的企業行銷漏斗系統」這個說法。

---

## 六、目前最大的真實限制

以下是我認為最重要、也最值得在對外溝通時克制承諾的地方。

### 1. 它強在中下漏斗，不是強在全鏈路流量獲取

ForgeBase 很擅長承接與轉化官網流量，但不是一個 campaign buying platform。

### 2. 它強在 lead 與 RFQ，不是強在營收閉環

它現在最成熟的是 visitor → lead → RFQ → sales handoff，而不是 RFQ → quote → order → revenue attribution。

### 3. 它有 automation，但還不是 enterprise-grade orchestration

現在的 nurture 與 segment 已經可用，但還沒有複雜旅程設計、規則分支與跨平台抑制能力。

### 4. 它有 account 能力雛形，但還不是完整 ABM

有 IP to company、account insight、company audience 這些元素，但尚未形成成熟的帳戶層漏斗運營。

### 5. 有一個已知技術缺口會影響穩健性

前端離線 queue replay 目前仍使用 `{ events: q }` 格式送 batch：[web/src/lib/analytics.ts](web/src/lib/analytics.ts#L179)，但後端 batch endpoint 現在吃的是原始陣列：[api/app/api/v1/endpoints/events.py](api/app/api/v1/endpoints/events.py#L342)。

這表示在離線補送事件場景下，目前存在契約不一致，會影響 tracking 穩定性。這不會推翻整體漏斗成立，但會影響企業級可信度。

---

## 七、建議對外銷售話術

### 可安全使用的版本

> ForgeBase 不是單純做網站，而是把企業官網變成一套可追蹤、可辨識高意圖買家、可推進詢價與業務跟進的成長漏斗系統。

> 它能把匿名流量逐步轉成可識別名單，再把高意圖詢盤交給業務，並讓管理層看到哪些頁面、哪些內容、哪些流量來源最能帶來 RFQ。

### 更強但仍相對安全的版本

> 對於依賴官網獲客的 B2B 製造商而言，ForgeBase 已經能承擔從網站行為追蹤、意圖判斷、名單收斂到詢價推進的核心漏斗任務。

### 不建議直接使用的版本

- 我們已經完整取代所有 CRM / MAP / CDP / ABM 工具
- 我們已經做完從曝光到營收回收的完整企業級閉環
- 我們已經具備成熟 AI 自動化與 enterprise orchestration

---

## 八、最準確的產品定位

如果要一句話定位 ForgeBase，我建議是：

> **一套以官網為核心，專注於需求擷取、意圖識別、詢價推進與業務接手的 B2B 成長漏斗系統。**

如果要做更商務版定位，可寫成：

> **ForgeBase helps B2B companies turn their website into a measurable demand capture and RFQ conversion funnel.**

---

## 九、成熟度評分

| 能力 | 分數 | 評語 |
|---|---|---|
| 行為追蹤 | 8.5 / 10 | 核心成立，但離線 replay 契約需修正 |
| 意圖判斷 | 8 / 10 | 規則引擎完整，ML 尚非核心 |
| 名單識別 | 7.5 / 10 | RFQ / contact 流程成熟 |
| 轉換推進 | 7 / 10 | CTA 與 RFQ 已形成主通路 |
| 業務接手 | 8 / 10 | routing / notify / CRM sync 已存在 |
| Nurture / Segmentation | 6 / 10 | 可用，但未達 enterprise automation |
| ABM / 帳戶層運營 | 4.5 / 10 | 有雛形，未形成主作業模式 |
| 營收閉環 | 4 / 10 | 尚未完成真正 revenue loop |

### 整體判定

**總體成熟度：約 7 / 10。**

對於「企業官網導向的 B2B 需求開發」來說，已經足夠成立。

對於「完整企業級 MarTech / RevOps 堆疊」來說，仍有明顯差距。

---

## 十、最終判語

如果我是以專業數位行銷顧問身份給你的最終結論，我會這樣說：

**ForgeBase 已經足以被定義為一套真的能替企業建立行銷漏斗的系統。**

它最有價值的地方，不是在做內容管理，而是在把官網從靜態展示頁，變成：

- 可追蹤的流量入口
- 可判斷的意圖引擎
- 可收斂的名單系統
- 可推進的 RFQ 漏斗
- 可交接的業務工作流

但若要成為真正完整的 enterprise funnel system，下一階段仍需補齊：

- 離線追蹤穩健性
- 營收回寫與成交閉環
- 帳戶層 ABM 聚合
- 更成熟的 nurture orchestration
- 更完整的跨平台 audience / CRM lifecycle 編排

**所以最準確的答案不是「有沒有漏斗」，而是：它已經有一條真實可運作的漏斗，只是目前最強的是中下漏斗。**