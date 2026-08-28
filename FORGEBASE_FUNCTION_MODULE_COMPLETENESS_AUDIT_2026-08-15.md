# ForgeBase 功能模組完整度盤點（正式環境更新版）

> 原始盤點日期：2026-08-15
>
> 本次完整更新：2026-08-28
>
> 評估基準：正式部署 SHA `2a8bc2cf91c09a3f78b6f346d943d1376478a186`、後續營運控制 commit 至 `0b3d470`、production 只讀稽核、完整 Release Gate、14 批內部產品化、商用前內部強化及實際瀏覽器證據
>
> 北極星：匿名訪客 → 行為追蹤 → 意圖評分 → 推測公司 → 尋找公司相關聯絡窗口 → 依旅程產生個人化信件 → 寄送與追蹤 → 對方回覆 → 真人業務接手 → RFQ／成交

---

## 一、結論先行

### 1.1 最新總判定

- **17 模組加權工程完整度：92.7%**，相較 2026-08-15 的 78.0% 上升 14.7 個百分點。
- 目前已不是「網站加 RFQ、成長能力留待第二階段」的產品；**匿名旅程至 RFQ／成交歸因是同一套核心產品主線**。
- 北極星程式閉環、資料模型、後台工作台、權限、稽核、重試安全、隱私保留及 Release Gate 已完成。
- 正式環境的 IP → 公司推測已由真實 People Data Labs `pdl_ip` provider 執行，兩個 active tenant 均為 `shadow`；production 不再使用 mock 作公司辨識。
- Hunter Domain Search／Email Verifier 與 Resend 已安裝至 production 並可由受控 adapter 使用；但「provider 可用」不等於聯絡人資料品質、真人信箱 deliverability 或市場成效已通過。
- Resend 已完成 public unsubscribe origin／簽章 secret、寄件身分、internal allowlist、真實內部信 provider acceptance＋delivered webhook；outbound 與 inbound webhook 事件目前都完整。專用 `replies.premierbiz.com.tw` MX 已 verified，DKIM 仍在 Resend pending，因此 inbound production secret、開關與真人回信測試尚未啟用。
- 自動外聯仍刻意關閉。系統目前只允許符合政策、人工確認與核准的受控路徑；沒有把「自動大量寄信」當成完成條件。
- 類別四沒有為了追求乾淨而猜測式刪除。`copilot_floating_widget`、`legacy_ip_resolver` 已移除；AgentOS、可選 ML runtime、relation recommender、LINE／Telegram 仍依正式觀察與治理 Gate 處理。
- 正式站外 synthetic monitor 已每 15 分鐘由 GitHub-hosted runner 執行，失敗會建立／更新單一 incident issue、恢復後自動結案；這證明站外檢查與 repository 告警路由，不等於真人通知必達或既定 SLA。

### 1.2 92.7% 代表什麼

這個分數代表「現有程式、UI、資料流程、測試與正式部署證據的工程完整度」，不代表：

- 已以真實 B2B 訪客樣本證明公司辨識 precision ≥ 90%。
- 已證明 Hunter 在台灣、日本、法國、俄語市場能持續找到正確 Persona 與 verified business email。
- 已以真人收件匣證明寄達率、退信率、申訴率、回覆率或 RFQ／成交率。
- 已取得所有外部資料商的多租戶 OEM／Reseller／下游展示書面權利。
- AI 翻譯及回答在所有產業、語言與法規情境皆不會出錯。
- 已承諾高可用 SLA、特定 RPO／RTO 或特定國家法遵結果。

因此，產品的正確現況是：**內部產品化與受控 production 架構已完成；外部商用驗證仍需以真實 pilot 證明。**

---

## 二、北極星逐段驗收

| 北極星節點 | 現況 | 正式／工程證據 | 尚未跨過的商用 Gate |
|---|---|---|---|
| 匿名訪客 | 已完成 | tenant-scoped visitor、session、consent、可信 proxy/IP 邊界、保留與刪除流程 | 真實流量規模、各市場 consent／legal basis 法務確認 |
| 行為追蹤 | 已完成 | page／product／download／CTA／chat／RFQ 事件、顧客旅程、去重與 tenant isolation | 真實事件品質與長期量測 |
| 意圖評分 | 已完成 | 規則式 intent score、facets、權重、衰減、任務與 UI；ML 非必要主路徑 | 需由真實成交資料校準權重；可選 ML runtime 仍關閉觀察 |
| 推測公司 | 工程完成，production Shadow | PDL `pdl_ip` 已在兩個 active tenant 啟用；quota、成本、國家、privacy 與信心 Gate 生效 | 高信心 precision、match rate、APAC 表現尚無真實樣本統計 |
| 尋找公司相關聯絡窗口 | 工程完成，等待品質驗證 | Hunter Domain Search／Verifier adapter、Persona policy、候選審核、遮罩、重驗證、轉 Contact、成本與 circuit breaker | production tenant 仍不得因 provider 存在而自動補全；需真實 Persona／Email 品質樣本與資料權利 |
| 依旅程產生個人化信件 | 已完成，Review Only | 不可變 journey snapshot、grounded evidence、草稿／重生／核准／拒絕、unsupported-claim gate | 需真實業務核准率、修改量與品牌／法遵審查 |
| 寄送與追蹤 | 工程完成，受控關閉 | Resend adapter、人工核准、冪等寄送、delivery／bounce／complaint／unsubscribe、suppression、頻率與 kill switch；一封 internal allowlist 真實信已 delivered 且 webhook 入庫 | 未開放一般外寄；仍缺真人外部樣本的 reputation、bounce／complaint／unsubscribe 分布 |
| 對方回覆 | 工程完成，外部入口受控 | inbound webhook/mailbox adapter、簽章、大小限制、清理、分類、thread 關聯與 replay safety；`email.received` webhook 與專用子網域 MX 已完成 | Resend DKIM 仍 pending；production inbound secret／switch 與真人來信分類驗收尚未執行 |
| 真人業務接手 | 已完成 | SalesHandoff、SLA、指派、timeline、建立 RFQ、wrong-person／unsubscribe／close | 真實業務團隊的回應 SLA 與操作採用率 |
| RFQ／成交 | 已完成 | RFQ workspace、狀態／指派／跟進／品質、outcome、won/lost、完整 attribution chain | 至少一個非測試 pilot 完成 reply → RFQ → won/lost；商業轉換率尚未證明 |

關鍵語意：公司辨識是「推測公司」，聯絡窗口是「公司相關候選」，不能宣稱已識別匿名訪客本人。

---

## 三、評分方法

每個模組仍沿用原盤點的五維模型，避免因更新方法而製造虛假進步：

| 維度 | 權重 | 判定內容 |
|---|---:|---|
| Data／API | 30% | schema、migration、API、tenant scope、狀態機、稽核與資料生命週期 |
| UI／UX | 20% | 前後台可操作性、狀態揭露、錯誤／空狀態、RBAC 與行動裝置 |
| End-to-end flow | 25% | 是否真正串成閉環、外部失敗是否 fail closed、是否可重播 |
| Tests／review | 15% | unit、integration、browser、security、fault、capacity、code review |
| Production evidence | 10% | 正式部署、真 provider、實際瀏覽器、production 稽核與復原證據 |

分數狀態：

- 90–100：工程上可正式受控使用。
- 75–89：主要能力可用，但仍有重要完整性或 production Gate。
- 50–74：局部可用或非核心 connector，不能擴大承諾。
- 25–49：原型／骨架。
- 0–24：不可視為產品能力。

另設一個不納入百分比的「商用 Gate」。外部資料精準度、資料授權、真人寄達率、法遵與成交成效，不會因測試很多就自動通過。

---

## 四、17 模組總表

| # | 模組 | 權重 | 舊分數 | 新分數 | 加權貢獻 | 最新判定 |
|---:|---|---:|---:|---:|---:|---|
| 1 | B2B 公開網站與產業內容呈現 | 9% | 85% | 94% | 8.46 | 核心已完善 |
| 2 | 範本與網站交付工廠 | 4% | 90% | 93% | 3.72 | 非核心但應保留／交付基礎 |
| 3 | CMS 與內容生命週期 | 10% | 80% | 94% | 9.40 | 核心已完善 |
| 4 | 素材、文件與資產治理 | 4% | 82% | 90% | 3.60 | 核心已完善 |
| 5 | 多國語系與翻譯治理 | 5% | 76% | 92% | 4.60 | 核心已完善；人工發布 Gate 保留 |
| 6 | SEO、結構化資料與搜尋營運 | 5% | 65% | 85% | 4.25 | 非核心但應保留 |
| 7 | 公開 RFQ 收件 | 10% | 95% | 98% | 9.80 | 核心已完善 |
| 8 | RFQ 業務工作台 | 8% | 97% | 98% | 7.84 | 核心已完善 |
| 9 | 行為追蹤、旅程與意圖評分 | 7% | 87% | 96% | 6.72 | 核心已完善 |
| 10 | IP／公司辨識與聯絡窗口補全 | 6% | 15% | 90% | 5.40 | 核心工程完成；商用品質未證明 |
| 11 | 分群、動態 CTA 與營運任務 | 4% | 72% | 87% | 3.48 | 非核心但應保留 |
| 12 | 前台 AI Product Advisor／後台 AI 業務助理 | 7% | 84% | 94% | 6.58 | 核心已完善；外部模型品質持續驗證 |
| 13 | Analytics、成果與閉環歸因 | 5% | 74% | 93% | 4.65 | 核心工程完成；真實成效未證明 |
| 14 | 通知、Email、外聯、回覆與接手 | 4% | 75% | 90% | 3.60 | 核心工程完成；外寄維持受控 |
| 15 | 外部 CRM／廣告／搜尋整合 | 3% | 25% | 61% | 1.83 | 非核心但 connector 邊界應保留 |
| 16 | 多租戶、RBAC 與平台管理 | 6% | 94% | 98% | 5.88 | 核心已完善 |
| 17 | 部署、復原、監控與安全供應鏈 | 3% | 85% | 96% | 2.88 | 核心已完善；不等於 SLA 認證 |
|  | **合計** | **100%** | **78.0%** | **92.7%** | **92.69** | **受控 production-ready；待外部 pilot 證明商用成效** |

### 4.1 五維評分明細

| # | Data／API | UI／UX | E2E flow | Tests／review | Production | 加權後模組分數 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 95 | 92 | 94 | 93 | 95 | 94% |
| 2 | 94 | 92 | 94 | 92 | 93 | 93% |
| 3 | 95 | 92 | 94 | 95 | 92 | 94% |
| 4 | 90 | 89 | 90 | 90 | 88 | 90% |
| 5 | 92 | 90 | 92 | 92 | 94 | 92% |
| 6 | 88 | 82 | 85 | 86 | 80 | 85% |
| 7 | 99 | 96 | 98 | 98 | 98 | 98% |
| 8 | 98 | 97 | 98 | 98 | 97 | 98% |
| 9 | 97 | 94 | 96 | 98 | 96 | 96% |
| 10 | 95 | 92 | 90 | 95 | 65 | 90% |
| 11 | 88 | 86 | 87 | 90 | 82 | 87% |
| 12 | 95 | 92 | 94 | 95 | 90 | 94% |
| 13 | 94 | 91 | 93 | 95 | 90 | 93% |
| 14 | 95 | 92 | 88 | 96 | 68 | 90% |
| 15 | 65 | 58 | 60 | 72 | 45 | 61% |
| 16 | 98 | 96 | 98 | 98 | 97 | 98% |
| 17 | 97 | 93 | 97 | 96 | 96 | 96% |

五維值是整數化稽核量尺，各模組分數依五維權重四捨五入；總分以發布的模組整數分數乘模組權重，加總為 92.69%。模組 10、14 的 Production 維度特別保守，因為正式 adapter／政策已存在，但真實品質、寄達及回覆仍未形成足夠樣本。

新分數不是把所有 TODO 視為完成。模組 10、13、14 的工程分高，但仍明確標記「真實品質／成效 Gate 未通過」；模組 15 則因不是北極星必要依賴，維持較低分不阻擋核心產品。

---

## 五、逐模組完整更新

### 1. B2B 公開網站與產業內容呈現 — 94%

**已到位**

- NorthForge 與 AxisForm 具產品、分類、應用、能力、證書、FAQ、公司、聯絡及 RFQ 多頁網站。
- 公開網站與 API 皆以 tenant／host 解析，第二租戶已證明不讀寫第一租戶資料。
- desktop／mobile、主要 CTA、導覽、fallback、空狀態與正式瀏覽器回歸已納入 Release Gate。

**保留邊界**

- 新租戶內容、素材、網域與逐語審核仍需 Tenant Delivery Factory 的人工 acceptance，不宣稱全自動架站。
- 真實客戶品牌驗收、無障礙外部稽核與不同產業的內容成效仍是導入工作。

### 2. 範本與網站交付工廠 — 93%

**已到位**

- 七種 template registry；NorthForge／handtool 與 AxisForm／precision 為已驗證 CMS adapter，其餘五種 registry 範本維持未串 CMS 身分；獨立 Template Portfolio 共六套展示站。
- SiteBuild、網域唯一性、公開語系、readiness、handoff、acceptance 與 publish invariant 均為可稽核狀態。
- Tenant Delivery Factory 可重播建立租戶骨架，失敗不留下半成品。

**保留邊界**

- Demo 不能被標成已串 CMS 的正式租戶；DNS、憑證、客戶素材與驗收仍需真實交付。
- 範本是加速交付能力，不是北極星的第二套產品方案，因此應保留但不另行包裝成分級產品。

### 3. CMS 與內容生命週期 — 94%

**已到位**

- 產品、分類、應用、FAQ、證書、頁面與相關內容的 CRUD、發布狀態、排序、tenant scope 及公開查詢已完成。
- Admin 已重構為單一產品導向資訊架構，內容與成長流程可從同一後台操作。
- Knowledge sync queue 具併發 claim、retry、stale recovery、tombstone、migration round trip 與故障隔離。

**保留邊界**

- 大量匯入、複雜審批層級與外部 PIM／DAM 同步不是當前北極星必要條件。

### 4. 素材、文件與資產治理 — 90%

**已到位**

- 圖片、文件、下載、關聯、配額、health、tenant isolation 及前後台使用路徑已完成。
- AI 與公開頁只引用已發布、可追溯的內容；隱私及保留作業不會誤刪已形成商務證據的鏈路。

**保留邊界**

- R2／off-site 資產生命週期與大量真實檔案容量仍需正式資源和長期運行證據。

### 5. 多國語系與翻譯治理 — 92%

**已到位**

- 公開介面支援英文、繁中、日文、法文、俄文；20 個 desktop 與 10 個 mobile 關鍵路由已由 production-build Chromium 驗證。
- locale switch、HTML `lang`、導覽、CTA、AI greeting／suggestion／安全降級、canonical／hreflang／sitemap 與 fallback 規則已完成。
- 單一來源內容可進翻譯／同步／審核流程，不需維護五套互不相干的網站。

**保留邊界**

- 系統會自動連動，但不會把未審核翻譯冒充已正式發布；產品規格、法規與產業用語仍需母語／領域人工審核。
- 不能對外保證任何 AI 翻譯永遠正確。

### 6. SEO、結構化資料與搜尋營運 — 85%

**已到位**

- metadata、canonical、hreflang、x-default、sitemap、fallback noindex 與結構化頁面基礎完成。
- 內容發布與搜尋營運具可追蹤的資料契約，不會把不存在或 fallback 的翻譯頁宣告為獨立在地化頁。

**保留邊界**

- GSC 真實資料、索引覆蓋、關鍵字排名、內容導流及自然搜尋轉換率仍需時間與外部流量。
- SEO 應保留，但不能承諾排名或 Lead 數。

### 7. 公開 RFQ 收件 — 98%

**已到位**

- tenant 綁定、結構化欄位、驗證、honeypot、簽章 challenge、限流、可選 Turnstile、consent 與品質分數完成。
- 建立後以 durable outbox 處理 routing、通知及下游工作；公開請求不等待外部服務，job 不複製個資。
- 正式 UI 已建立、操作、完成閉環並清除驗收資料。

**保留邊界**

- 開放未知大量流量前仍應配置 Turnstile 並觀察 spam／誤擋率。

### 8. RFQ 業務工作台 — 98%

**已到位**

- 搜尋、篩選、指派、狀態、備註、跟進時間、今日待辦、SLA、quality、won/lost 與 outcome 完成。
- 狀態機不倒退；tenant／role 權限與直接 deep-link 存取由 API 和瀏覽器矩陣共同驗證。
- 可由 inbound handoff 建立 RFQ，並保留 outreach／reply／handoff／outcome 關聯。

**保留邊界**

- 真實業務採用率、SLA 達成率及成交資料仍需 pilot。

### 9. 行為追蹤、旅程與意圖評分 — 96%

**已到位**

- 匿名 visitor／session、page／product／download／CTA／chat／RFQ 事件、顧客旅程及同意治理完成。
- 規則式意圖評分、facets、時間衰減、權重、分群與任務是正式主路徑。
- trusted proxy、bot／hosting／privacy eligibility、tenant isolation、保留及匿名訪客 erasure 已受測。

**保留邊界**

- ML scoring runtime 不是核心意圖評分本身，現階段關閉觀察；規則式評分不可因 ML 退場而刪除。
- 權重仍需以真實 RFQ／成交反饋校準。

### 10. IP／公司辨識與聯絡窗口補全 — 90%

**已到位**

- NetworkObservation、CompanyIdentification、ProviderUsage、政策、信心、證據、人工確認／拒絕、quota、成本、國家、保留期與 circuit breaker 完成。
- 2026-08-28 production 稽核確認 AxisForm 與 NorthForge 均為 `shadow / pdl_ip / ready=true`；真實 PDL 認證請求合法回傳 `no_match`、0 units，沒有使用 mock 或捏造候選。
- ContactCandidate、Persona policy、Hunter Domain Search、Hunter Email Verifier、遮罩、來源、verification status、人工審核、重驗證、轉 Contact 與 metric 完成。
- production registry 已確認 `pdl_ip`、`hunter_domain`、`hunter` 可用；所有 active production tenant 的公司辨識政策皆未使用 mock，mock adapter 仍保留供開發與 deterministic 測試。

**尚未完成的商用 Gate**

- PDL Shadow Mode 只產生公司候選，不自動確認公司、不自動找人、不寄信。
- 尚未以已知真實公司樣本證明 high-confidence precision ≥ 90%，也沒有分市場 match rate／誤判率。
- Hunter 尚未以台灣、日本、法國、俄語市場的目標 Persona 盲測證明 relevance、任職新鮮度及 verified email 品質。
- 免費帳號與 API 認證不等於多租戶 OEM／Reseller／下游展示權；書面資料權利仍是 production 商用 Gate。

**判定**

這是北極星核心，不是實驗功能，也不應刪除。工程已完成到受控 Shadow／Review 架構；剩餘工作是外部資料品質與權利驗證，而不是再造一套 resolver。

### 11. 分群、動態 CTA 與營運任務 — 87%

**已到位**

- 依行為、意圖、journey facets 與成果建立分群、CTA 狀態、高關注任務及後台導流。
- 不同分母的 visitor／RFQ cohort 已拆開，避免用錯誤轉換率誤導營運。

**保留邊界**

- 動態 CTA 與 segment 應作核心的輔助能力保留，不另做方案分層；真實 uplift 需 A/B 或 pilot 流量證明。

### 12. 前台 AI Product Advisor／後台 AI 業務助理 — 94%

**已到位**

- 以前台公開內容與已上傳／發布知識為可信來源，支援多語問答、來源、grounded／limited／blocked、警示與 Chat → RFQ draft。
- 對 prompt injection、未證實認證、價格、交期、unsupported numeric claim 進行阻擋或降級；證據不足不附假來源、不顯示不當 CTA。
- Frozen AI／Knowledge Gate、正式瀏覽器多租戶問答及完整 Release Gate 通過。
- 登入後另有專用「AI 業務助理」頁，可在 tenant scope 內查詢 RFQ、訪客、漏斗與聯絡資料；只有使用者明確要求時才可更新 RFQ、指派、建立跟進草稿或提醒，寄送草稿仍需人工核准。
- 退場的是重複的 floating widget，不是專用後台 AI 業務助理；對話歷史、統計、RBAC 與專用頁仍保留。

**保留邊界**

- deterministic gate 證明安全契約，不等於所有外部模型回答的自然語言正確率已證明。
- 對外應說「有知識來源、證據不足時降級／轉 RFQ」，不可承諾絕不 hallucinate。
- 後台助理的產業建議與營運判斷仍屬輔助資訊；資料查詢、寫入權限、硬編碼 heuristics 與外部模型輸出需持續做 claim／RBAC 回歸，不能當成自動決策或無需人工確認的事實。

### 13. Analytics、成果與閉環歸因 — 93%

**已到位**

- visitor → company → contact candidate → outreach → reply → handoff → RFQ → outcome 的關聯與回查已完成。
- 事件、journey、provider usage、草稿、核准、寄送、delivery、reply、handoff、RFQ 與 won/lost 可在 tenant scope 下稽核。
- attribution 使用正確 cohort 與生命週期語意，避免把測試資料、不同分母或尚未成熟的漏斗寫成成效。

**尚未完成的商用 Gate**

- production 目前 RFQ 已經標記測試資料；尚無非測試 pilot 可證明 reply、positive reply、RFQ 或 won rate。
- 工程閉環完成不代表「系統已證明能增加成交」。

### 14. 通知、Email、外聯、回覆與接手 — 90%

**已到位**

- Resend／SendGrid 共用寄信服務，正式寄件顯示名稱、寄件身分與真人接手收件身分已配置；provider accepted 與 dry-run 語意分離。
- OutreachMessage 保存不可變內容、journey snapshot、核准者、冪等鍵、provider message id 與事件 timeline。
- delivery、bounce、complaint、unsubscribe、tenant／global suppression、頻率、成本、雙 kill switch 與重試邊界完成。
- inbound receipt、簽章驗證、thread、分類、正文／附件限制、保留清除、SalesHandoff、SLA、指派及 RFQ conversion 完成。

**尚未完成的商用 Gate**

- production 外部寄送與自動外聯保持關閉；金鑰存在不會自動聯絡訪客或候選。
- 已完成一封 internal allowlist 真實信的 provider accepted、delivered 與 webhook 閉環；這不等於一般外寄的 deliverability 或 reputation 已證明。
- 專用 inbound MX 與 `email.received` 訂閱已完成，但 Resend DKIM 仍 pending；尚未注入 inbound route secret、開啟受控 tenant policy 或執行真實 reply → handoff。
- 尚未取得足量 bounce／complaint／unsubscribe／reply 樣本以判斷營運門檻。
- 第一階段只應開 `APPROVAL_SEND`，且每封人工核准；`CONTROLLED_AUTO` 必須等待公司／聯絡品質、法遵與寄送信譽穩定。

### 15. 外部 CRM／廣告／搜尋整合 — 61%

**已到位**

- IntegrationCredential、加密、provider 狀態、fail-closed adapter、outbox、webhook 與 connector 邊界可重用。
- PDL、Hunter、Resend 是北極星資料／傳輸 provider，已透過 provider-neutral adapter 接入；產品資料與判斷仍由 ForgeBase 擁有。
- HubSpot、GSC、Google／Meta、Mailchimp／SendGrid 等既有 connector 或設定骨架不應被誤寫成已完成客戶導入。

**判定與處置**

- CRM 不是北極星必要依賴；不需為了產品成立而使用 HubSpot，也不應把北極星資料只放在單一 CRM。
- 保留小而穩定的 connector contract 與已使用 adapter；沒有客戶需求、沒有真 sandbox 驗收的個別 connector 不應放在主要選單或對外承諾。
- 這一模組的 61% 不阻擋核心上線，也不值得為追分而先擴建大量第三方整合。

### 16. 多租戶、RBAC 與平台管理 — 98%

**已到位**

- tenant、user、role、plan、feature、quota、SiteProfile、SiteBuild、IntegrationCredential 及所有北極星資料均 tenant-scoped。
- 平台可建立／停用租戶、建立 owner、交付網站、管理 readiness／publish、查看跨租戶營運與不可變稽核。
- 真實 Admin Browser／RBAC matrix 驗證選單、角色、403、deep link、Platform Admin 與 tenant isolation。
- 兩個 active production tenant 的 identity、網站與政策已完成只讀資料品質稽核；測試 RFQ 不冒充正式商務資料。

**保留邊界**

- 目前是平台管理員受控開通，不是自助購買、即時自動建站、自助取消或全自動刪除。
- 產品不再切成兩階段方案；plan／feature 基礎留作 tenant policy、配額與營運治理，不作舊式功能拆售選單。

### 17. 部署、復原、監控與安全供應鏈 — 96%

**已到位**

- Docker／Caddy／PostgreSQL、deep readiness、safe deploy、migration、image manifest、rollback、資料庫備份、off-site 加密流程與隔離 restore lab 完成。
- Operational／Knowledge queues 具 retry、stale recovery、fault isolation、idempotency、監控、SLO evidence 與 incident console。
- 完整 Release Gate 覆蓋 API、migration、North Star、AI、fault、capacity、privacy、retirement、Admin RBAC、五語公開站、四前端、六個 production image、SAST、secrets、dependency、SBOM 與 recovery。
- 最新 release／deploy run `33144552515`（SHA `2a8bc2c`）、站外監控 `33144986004`、商用只讀稽核 `33145033057` 與正式隔離還原／瀏覽器驗收 `33145064129` 全部成功。

**保留邊界**

- 隔離 restore RTO、短 soak 或 CI capacity 是 regression baseline，不是 production SLA。
- 站外 synthetic monitoring 已完成；真實長時間壓力、跨區災難復原、外部滲透測試、GitHub issue 以外的 on-call 到達演練與正式 SLA 仍應依營運規模補齊。

---

## 六、依北極星重新分類

### 6.1 核心已完善

以下指工程與受控 production 能力已到位，不代表市場成效已證明：

1. B2B 公開網站、CMS、資產與五語介面。
2. 匿名訪客、同意、行為追蹤、顧客旅程、規則式意圖評分。
3. 結構化 RFQ、業務工作台、SLA、outcome。
4. 前台 AI Product Advisor、知識 grounding、安全降級、Chat → RFQ，以及登入後的受控 AI 業務助理。
5. 多租戶、RBAC、平台開通、交付、稽核與資料品質治理。
6. North Star 全鏈資料模型、API、後台、replay safety 與 attribution。
7. Release、資安、復原、隱私保留、監控與事故治理。

### 6.2 核心未完善

這裡的「未完善」已從缺程式，縮小為外部品質／權利／商用實證：

1. **公司辨識品質**：真實 PDL Shadow 已開，但尚缺已知樣本的 precision／match rate／市場分布。
2. **聯絡窗口品質**：Hunter adapter 已就緒，但尚缺 Persona relevance、任職新鮮度、verified email 與多市場盲測。
3. **資料使用權**：免費 API key 不等於多租戶商用、保存、展示、外聯及 OEM／Reseller 權利。
4. **真人寄送與回覆**：Resend／inbound 工程完成，但尚缺正式 DNS／reputation、真人 deliverability、事件與回信驗收。
5. **真實成交閉環**：尚缺至少一個 pilot tenant 的非測試 reply → handoff → RFQ → won/lost 資料。
6. **Controlled Auto**：在前五項 Gate 未通過前維持關閉；這是治理要求，不是漏做功能。

### 6.3 非核心但應該留

1. 範本 portfolio 與 Tenant Delivery Factory。
2. SEO、sitemap、結構化資料與未來 GSC connector。
3. 分群、動態 CTA、內容成效與營運任務。
4. Provider-neutral connector contract、整合憑證、outbox／webhook 基礎。
5. plan／feature／quota 基礎，用於租戶政策與風險控制，不用來恢復兩階段產品包裝。
6. 通知核心、Email／in-app 歷史與真正使用中的營運告警。

### 6.4 非核心可以刪除／退場

| 項目 | 最新處置 | 原因／限制 |
|---|---|---|
| Copilot floating widget | 已移除 | 與後台主工作流重複，source path 已稽核無殘留 |
| Legacy IP resolver | 已移除 | 已由 governed provider adapter 取代，避免 mock／舊 resolver 被誤認為真辨識 |
| AgentOS runtime | 入口關閉，觀察中 | 需完成正式 30 天連續 telemetry、資料處置與 rollback/removal plan 才可刪 |
| ML scoring runtime | 入口關閉，觀察中 | 僅指可選 ML 層；規則式核心意圖評分受保護、不可刪 |
| Relation recommender | 入口關閉，觀察中 | 需完成正式 60 天 Gate，不提前猜測刪除 |
| LINE／Telegram 個別通知渠道 | 入口關閉，60 天觀察中 | 通知核心保留；個別渠道需等零設定、零使用與資料處置證據才決定移除 |

退場治理的最新 production snapshot 不核准任何新增刪除：`new_removals_authorized=[]`。因此「該刪除的徹底乾淨」目前只適用於已核准的 Copilot widget 與 legacy resolver；其餘候選是有意識的 fail-closed 觀察，不算無人負責的技術債。

---

## 七、正式環境與驗證證據

| 證據 | 最新結果 | 能證明什麼 | 不能證明什麼 |
|---|---|---|---|
| Complete Release Gate／Deploy `33144552515` | success，SHA `2a8bc2c` | API、migration、North Star、AI、fault、capacity、privacy、retirement、RBAC、五語、前端、images、security、SBOM、recovery 與部署全通過 | 真實市場成效、長期 SLA |
| API 完整 PostgreSQL suite | 358 passed、3 skipped、1 deselected、0 failed | 核心資料與整合回歸 | 外部 provider 資料品質 |
| North Star E2E Lab | 全鏈通過；provider 使用 deterministic fake | 真實 DB、狀態機、權限、稽核、冪等、歸因閉環 | PDL／Hunter／Resend 的真實成效 |
| Admin Browser／RBAC | Chromium matrix 通過 | 實際登入、選單、權限、deep link、關鍵操作 | 每種人員日常使用習慣 |
| Five-locale browser | 英／繁中／日／法／俄通過 | production build 路由、lang、切換、mobile、console | 母語產業內容與法務校對 |
| Provider sync `33132485016` | success | production registry 有 `pdl_ip`、`hunter_domain`、`hunter`，金鑰未進 repo | 多租戶資料權利與候選品質 |
| PDL policy apply `33141690665` | success | 真實 PDL probe 後才切換 tenant policy | PDL 一定能 match 每個 IP |
| PDL final audit `33142199489` | success | 兩 active tenant 均 `ready=true`、`shadow/pdl_ip`、無 mock policy | precision ≥ 90% 或找得到訪客本人 |
| Production data quality `33138620002` | success | 2 active tenant identity 正確、8 筆 RFQ 均標記為測試 | 已有真實客戶或真實成交 |
| Production retirement `33140492663` | success | 已移除項無殘留、關閉項 fail closed、無新刪除 | 30／60 天觀察已到期 |
| External uptime `33144986004` | success，8／8 | GitHub-hosted runner 的公網、API readiness、兩展示站與 asset probe；monitor 已登錄 readiness | 真人告警必達、商務流程或 SLA |
| Commercial readiness `33145033057` | success（guarded） | PDL／Hunter／Resend registry、tenant policy、transport switch 與 activation blockers；無外部呼叫、無寄信、無政策修改 | provider 品質、資料權、寄達率、回覆或成交 |
| Controlled production email `33149263859` | success | internal allowlist 真實信由 Resend 接受、delivered，且 sent／delivered webhook 入庫；全域 delivery／outreach switch 仍關閉 | 一般外部收件品質、退信／申訴率或自動外聯 |
| Resend account audit `33153202238` | success | 寄件網域 verified，outbound webhook 完整，`email.received` inbound webhook 已啟用 | inbound 子網域 DKIM 或真人回覆已完成 |
| Resend inbound DNS `33153648940` | partial external state | `replies.premierbiz.com.tw` receiving-only；MX verified、sending disabled、receiving enabled；TXT 與三個公開 resolver 逐字一致 | Resend DKIM 仍 pending，故不啟用 production reply loop |
| Recovery／browser `33145064129` | success | 最新 off-site recovery point、隔離復原、48 小時內備份／15 分鐘內演練證據、演練後公網 8／8 與 Platform Admin Chromium | 正式事故 RPO／RTO 保證或 live DB 覆寫演練 |

核心參考文件：

- `FORGEBASE_NORTH_STAR_CORE_GAP_IMPLEMENTATION_PLAN_2026-08-26.md`
- `FORGEBASE_NORTH_STAR_IMPLEMENTATION_PROGRESS_2026-08-26.md`
- `FORGEBASE_INTERNAL_PRODUCTIZATION_14_BATCH_PROGRESS_2026-08-27.md`
- `FORGEBASE_CATEGORY4_RETIREMENT_AUDIT_2026-08-27.md`
- `FORGEBASE_PRODUCT_CLAIMS_IMPLEMENTATION_AUDIT_2026-08-26.md`

---

## 八、對外產品承諾邊界

### 8.1 現在可以說

- ForgeBase 是一套 B2B 多語網站、AI Product Advisor、匿名旅程、意圖辨識、公司候選、聯絡窗口候選、受控個人化外聯、回覆接手與 RFQ／成交歸因的單一產品。
- 網站內容可由單一來源維護並連動多語；每個語言仍可人工審核發布。
- AI 依已發布網站與知識庫回答，證據不足時會降級、拒絕高風險推論或導向 RFQ。
- 系統可記錄匿名訪客旅程、計算意圖並在符合 privacy／成本／品質政策時推測公司。
- 系統可提出公司相關聯絡窗口候選、生成有旅程證據的個人化草稿，並在人工核准及寄送 Gate 開啟後寄送、追蹤與接手回覆。
- 真人業務可在後台接手、建立 RFQ 並記錄 outcome。

### 8.2 現在不能說

- 一定能識別每位匿名訪客、一定知道訪客本人或保證公司辨識正確。
- 一定能找到正確聯絡人、任職一定最新、Email 一定有效。
- 系統目前會自動寄信給所有高意圖訪客；production 自動外聯仍關閉。
- AI 絕不亂講、翻譯絕不出錯或任何回答皆具法律／產業保證。
- 已證明能提高 Leads、回覆率、RFQ 或成交率。
- 已取得所有市場法遵、資料商轉售權或高可用 SLA 認證。

---

## 九、剩餘工作：只做能改變商用判定的驗證

不應再以擴增內部 TODO 或新增非核心 connector 來追求百分比。下一步依序為：

1. 使用已完成的去識別化 POC scorecard 與範本建立 company-identification ground-truth 樣本，分台灣／日本／其他目標市場量測 high-confidence precision、match rate、false positive 與成本；工具完成不代表樣本已取得。
2. 對同一批已知公司平行評估 PDL Person／Hunter 候選，量測 Persona relevance、任職新鮮度、verified business email、coverage 與每個可用窗口成本；每個 provider 必須各自覆蓋至少兩個市場且每市場樣本達 Gate。
3. 向 PDL／Hunter 取得 ForgeBase 多租戶展示、保存、外聯、刪除及 OEM／Reseller／Solution Provider 書面權利；未通過則維持 Shadow／Review Only 或更換 provider。
4. Public unsubscribe origin／signing secret、寄件身分、allowlist、suppression 與一封真實 internal delivered probe 已完成；下一步仍須以明確的小量名單、人工核准及法遵條件驗收後才可開 `APPROVAL_SEND`。
5. 等 Resend 專用 inbound 子網域 DKIM 由 pending 轉為 verified，再注入 inbound signing secret，維持全域 switch 關閉完成 audit，最後才以單一受控 tenant 驗收 positive／question／RFQ／wrong-person／not-now／negative／auto-reply 及跨租戶隔離。
6. 導入第一個非測試 pilot tenant，以不可混入 synthetic data 的方式走完整 reply → handoff → RFQ → won/lost。
7. 只有 precision、候選品質、bounce、complaint、unsubscribe、SLA 與成本持續在門檻內，才考慮白名單式 `CONTROLLED_AUTO`。
8. 到達正式 30／60 天觀察期限後，逐一處理 AgentOS、ML runtime、relation recommender、LINE／Telegram；每一項另立 removal change、資料處置與 rollback revision。

---

## 十、版本差異摘要

| 舊盤點敘述 | 2026-08-28 更新 |
|---|---|
| 整體 78%，僅適合封閉展示 | 工程完整度 92.7%，可受控 production 使用；外部商用成效仍待 pilot |
| IP／公司／聯絡人 15%，第四優先擱置 | 北極星核心；全鏈已實作，PDL production Shadow 已真實啟用，Hunter adapter 已就緒 |
| Email 永久 dry-run，外聯擱置 | Resend provider 與完整受控寄送／回覆鏈已實作；一般外寄與自動外聯仍由 kill switch 關閉 |
| 日／法／俄只是未完成語系 | 五語公開介面包與 Chromium Release Gate 已完成；租戶內容仍需逐語審核 |
| 北極星能力列為第二層 roadmap | 取消兩階段產品概念，北極星全鏈為同一核心產品 |
| 類別四尚未系統化處理 | 兩項已移除，五項有 fail-closed、telemetry、30／60 天及 governance Gate；目前無新刪除授權 |
| 部署與測試證據零散 | 完整 Release Gate、六 image SBOM、資安、站外監控、復原、瀏覽器、資料品質與 production provider／transport 稽核已制度化 |

---

## 十一、最終判定

ForgeBase 的產品主體已完整重構為單一北極星：

**匿名訪客 → 行為追蹤 → 意圖評分 → 推測公司 → 公司相關聯絡窗口 → 個人化草稿 → 受控寄送與追蹤 → 回覆 → 真人接手 → RFQ／成交。**

就內部工程、正式部署、安全邊界與可稽核性而言，產品化目標已大致完成；目前真正剩下的不是再補大量頁面或再造 mock，而是用真實、合法、可量測的外部資料與 pilot 證明三件事：

1. 公司與窗口候選夠準。
2. 寄送與回覆流程在真實世界安全有效。
3. 最終確實能帶來 RFQ／成交，而不只是技術閉環。

在這三項獲得證據前，對外應稱為「受控 production／pilot-ready」，不稱為「商業成效已驗證」或「全自動獲客已完成」。
