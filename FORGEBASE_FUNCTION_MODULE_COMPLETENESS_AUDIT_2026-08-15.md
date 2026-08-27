# ForgeBase 功能模組完整度盤點

- 初次盤點日期：2026-08-15
- 第二輪覆核日期：2026-08-15（加入正式站瀏覽器實測、公開權重與可重算子分數）
- 第三輪補強日期：2026-08-15（完成指定八模組的風險修補、migration、完整 DB 整合測試與重新評分）
- 第三輪收尾日期：2026-08-15（完成反垃圾、consent 撤回／保留期、核心多語 SEO、AI grounding，並執行優先 1–3：部署可靠性、多租戶平台與網站交付流程）
- 最終 Code Review、第二動態租戶部署與 UIUX 驗收：2026-08-15（Linode／`pcbrm.tw`／AxisForm，migration `0067`）
- 多租戶營運後台補強與正式驗收：2026-08-15（跨租戶待辦、交付狀態、風險操作防呆與平台稽核軌跡，migration `0068`）
- RFQ 業務工作台補強與正式驗收：2026-08-16（簡化案件工作台、角色權限、指派、跟進、內部備註、垃圾隔離、重複合併、成交金額、CSV 與時區修正，migration `0069`）
- Resend 寄信鏈路補強與正式驗收：2026-08-16（平台憑證、已驗證寄件網域、統一寄信服務、dry-run／實寄狀態分離、官方測試收件位址、後台 UIUX 與 Linode 部署）
- 盤點目的：確認 ForgeBase 目前各功能模組的技術與實作完整度，作為「受控測試」與未來對外銷售範圍的依據。
- 評估基準：目前工作區程式碼、前後台路由與資料模型、既有驗收文件、正式站可用狀態，以及本次前端型別／lint 檢查。

> 本文件的百分比是「技術實作與可交付完整度」，不是商業成效、流量、成交率或正式 SaaS 上市資格。
> 例如：有可操作 UI、API、資料表與基本測試的模組，分數會高於只有 UI 或 roadmap 的模組；但若缺少安全邊界、真實第三方驗證或可靠背景任務，仍不得視為可對外承諾的正式功能。
> 第二輪覆核刻意把「畫面存在」、「程式存在」、「主流程可完成」與「可在多租戶正式營運」分開；因此分數較第一版保守。

---

## 一、整體結論

| 評估範圍 | 完整度 | 判定 |
|---|---:|---|
| 第一層：外銷網站、內容後台、詢價收件與業務處理 | **85%** | 第二個完整動態產業網站與 RFQ 日常案件工作台已完成正式操作驗收；Resend 供應商鏈路已驗證，但持久設定仍採不實寄安全模式，CRM sandbox 尚未完成。 |
| 第二層：訪客訊號、公司辨識、AI、分群與成效營運 | **64%** | Email／nurture 的安全發送鏈路已有正式證據；公司辨識、真實成效樣本與其他第三方整合仍是主要限制。 |
| 平台基礎：多租戶、角色、方案、部署與可觀測性 | **91%** | NorthForge 與 AxisForm 已通過核心資料隔離；平台後台亦可跨租戶辨識待處理項目、管理網站交付、控管風險操作並留下不可變稽核紀錄。 |
| **全產品加權技術完整度** | **78%** | **第一層與平台可進受控整站測試；第二層已補上 Resend 寄信鏈路，但公司辨識與成果歸因仍不得包裝成可計費保證。** |

### 第二輪覆核的主要修正

| 修正項目 | 第一版 | 第二輪 | 修正原因 |
|---|---:|---:|---|
| 全產品總分 | 61% | **56%** | 第一版未公開模組產品權重，且部分分數把「畫面／骨架存在」看得過高。 |
| 產業範本與參考站 | 90% | **78%** | 六套範本均已正式上線且有多頁架構，但五套仍是靜態展示；範本轉正式站與接後台仍是人工專案。 |
| 多語內容與語系網站 | 45% | **38%** | 繁中站路由與 `lang=zh-TW` 正常，但部分內容回退英文，AI 客服的開場與建議問題仍是英文。 |
| IP／公司／聯絡人辨識 | 20% | **15%** | 現況只是 ip-api 網路組織欄位映射，尚未有真正的 B2B company/person provider。 |
| AI Product Advisor | 30% | **25%** | Chat UI 可用，但正式繁中頁仍出現英文開場；語言、grounding、安全與 Chat → RFQ 閉環尚未完成。 |

### 第三輪指定模組補強結果

| 模組 | 補強前 | 補強後 | 本輪主要證據 |
|---|---:|---:|---|
| 素材與文件管理 | 70% | **82%** | 串流式暫存、signature、quota、SHA-256、租戶關聯驗證。 |
| 多語內容與語系網站 | 38% | **64%** | Chat 中文全鏈、CMS locale 正規化、八類內容 locale coverage API。 |
| RFQ 詢價表單與收件 | 72% | **88%** | advisory lock、輸入邊界、跨租戶關聯拒絕、一次性 Chat draft。 |
| RFQ 業務處理、品質、SLA 與任務 | 65% | **82%** | durable operational outbox、idempotency、retry、卡住回收與失敗查詢。 |
| 訪客追蹤與意圖評分 | 58% | **76%** | consent gate、session-only identity、GA 延後載入、visitor/session ownership。 |
| 分群、動態 CTA 與高關注名單 | 48% | **68%** | Segment tenant scope、CTA locale、impression、decision id、24h frequency cap。 |
| AI Product Advisor 與 Chat → RFQ | 25% | **62%** | 訊息語言偵測、繁中 policy、server-side handoff draft、來源保存。 |
| 成效、漏斗、內容歸因與 outcomes | 45% | **66%** | cohort 方法說明、提交時 immutable snapshot、最低樣本行動門檻。 |

> 本段記錄第三輪當時的評分。2026-08-16 已另完成 Resend 供應商鏈路驗證；CRM、R2 與其餘外部服務仍未因只有程式骨架而加分。

### 第三輪收尾與優先 1–3 執行結果

| 範圍 | 收尾前 | 收尾後 | 新增的可驗證能力 |
|---|---:|---:|---|
| 多語內容與語系網站 | 64% | **76%** | 核心頁 canonical／hreflang／x-default 一致；英文 fallback 的中文 URL 會 noindex；sitemap 只列實際翻譯內容。 |
| SEO、發布與快取更新 | 55% | **65%** | 核心多語 metadata 與動態 sitemap 修正；尚未把 GSC／流量擴張納入本輪。 |
| RFQ 詢價表單與收件 | 88% | **95%** | 租戶綁定 challenge、友善重試、完整欄位標籤、RFQ 建立後副作用全面改走 durable outbox；正式站驗收通過。 |
| RFQ 業務處理、品質、SLA 與任務 | 82% | **96%** | 單一案件工作台、主管／業務權限、指派、跟進、備註、歷程、垃圾隔離、重複合併、成交／失單與 CSV 均已完成；待辦到案件篩選與時區亦經正式操作驗收。 |
| 訪客追蹤與意圖評分 | 76% | **87%** | consent audit、同一 visitor identity、撤回後清除事件／session、180 天保留期；RFQ／Chat／Contact 保留。 |
| 分群、動態 CTA 與高關注名單 | 68% | **72%** | CTA 明確區分草稿／已上架／封存，舊 active 資料完成正規化，高關注任務列可操作。 |
| AI Product Advisor 與 Chat → RFQ | 62% | **84%** | 發布資料白名單、prompt injection 阻擋、證據不足即限縮；grounding 與警示持久化並可在後台稽核，中英文 UI 實測通過。 |
| 成效、漏斗、內容歸因與 outcomes | 66% | **74%** | 訪客 cohort 與 RFQ cohort 分離，不再顯示無效轉換率；後段狀態改為可解釋的累積生命週期。 |
| 多租戶、權限、方案與平台管理 | 55% | **80%** | 停用租戶封鎖、tenantless feature gate 封閉、方案驗證、租戶／owner／品牌／交付單 UI+API，平台健康頁正式驗收通過。 |
| 部署、監控與背景工作可靠性 | 45% | **80%** | API deep health、安全備份／部署／應用映像回復、背景工作監控已於 Linode 執行；修正 rollback tag 相容性並保留兩組備份。 |
| 產業範本與交付流程 | 78% | **84%** | 七種範本 registry、靜態 Demo／CMS adapter 明確分流、readiness 檢查與受控發布狀態。 |

### 第二動態租戶與交付驗收

| 模組 | 驗收前 | 驗收後 | 新增的正式證據 |
|---|---:|---:|---|
| B2B 製造業網站前台 | 82% | **84%** | AxisForm 精密加工站已正式上線；多頁、圖片、品質聲明、Chat 與 RFQ 均以瀏覽器操作通過。 |
| 產業範本與參考站 | 84% | **89%** | `precision-machining` 已從靜態 Demo 轉成第二個 CMS-connected tenant；不再只有 NorthForge 能驗證串接。 |
| 多租戶、權限、方案與平台管理 | 80% | **89%** | 兩租戶 profile、model、asset、Chat 寫入、RFQ contact、任務與 outcome 隔離均在正式環境通過。 |
| 部署、監控與背景工作可靠性 | 80% | **86%** | 新增獨立 tenant web service／host、100 併發零失敗、服務停止後其他租戶持續可用且 8 秒內恢復。 |

### RFQ 業務工作台正式驗收

| 模組 | 驗收前 | 驗收後 | 新增的正式證據 |
|---|---:|---:|---|
| RFQ 業務處理、品質、SLA 與任務 | 91% | **96%** | 正式站以可刪除案件走過搜尋、指派、內部備註、狀態、跟進、今日待辦與期限篩選；主管／業務／行銷權限、跨租戶拒絕、垃圾隔離、重複合併、成交金額與 CSV 另有完整 DB 整合測試。 |

> RFQ 工作台當次上調不包含 Email／通訊軟體外部提醒；其後 Resend 已另行完成供應商測試驗收，但 HubSpot／Salesforce 仍須各自 sandbox 驗收。

> IP／公司辨識、CRM 與其他第三方整合分數仍未提高；只有具備新增程式、測試、正式部署與供應商回應證據的 Resend／Email 模組在 2026-08-16 重新評分。AgentOS 未配置時維持乾淨跳過。

> 第四優先「IP／公司／聯絡人 enrichment」仍擱置；第五優先後續僅部分解除，範圍限於 Resend 平台寄信鏈路與安全界線，不包含 SEO 流量擴張或自動外聯。

### Resend 寄信鏈路正式驗收

| 模組 | 驗收前 | 驗收後 | 新增的正式證據 |
|---|---:|---:|---|
| 通知、寄信與 nurture | 42% | **75%** | Resend 平台憑證與寄件網域已驗證；測試信、RFQ 內部通知、指派／提醒／升級、auto-reply 與 nurture 共用同一 ESP；dry-run 不再被記成已寄出；Linode 以 Resend 官方虛擬地址取得 provider message ID，後台真人操作驗收通過。 |

> 75% 代表「可在受控開關與人工監督下使用」，不是已開放自動寄信。正式環境持久設定仍為 `EMAIL_DRY_RUN=true`，`SALES_NOTIFY_EMAIL`／`MANAGER_EMAIL` 未填，NorthForge／AxisForm 的 auto-reply 仍關閉；因此不會寄信給現有訪客、RFQ 或 Leads。

### 三種不同的「完成」不可混用

| 判斷角度 | 本次結論 |
|---|---|
| 展示完成度 | 官網、NorthForge 完整站、六套產業範本與後台入口已可展示，視覺與頁面量不是目前最大缺口。 |
| 技術實作完整度 | 加入 Resend 正式供應商鏈路、Code Review、Linode 部署與 UIUX 驗收後，依同一權重矩陣重算為 **78.13%，四捨五入 78%**。 |
| 對外測試就緒度 | 第一層與平台可開始指定 tenant、人工監督的封閉測試；Email 可保持 dry-run 做完整流程測試，第二層仍有公司辨識、真實成效樣本與其他外部整合缺口。 |

### 產品階段判定

1. **現在可以做**：以 NorthForge 參考站與指定 tenant 做端到端測試，驗證網站、內容維護、RFQ 收件與後台處理。
2. **現在不應承諾**：保證流量、保證辨識公司／聯絡人、AI 可可靠代替業務、AI 自動產出準確商業答案、未經 tenant 開關與收件人設定即自動寄信、CRM 自動化、可直接開放多租戶自助購買。
3. **刻意不提供**：舊站自動匯入、AI 自動撰寫／翻譯／發布網站內容。這是產品邊界，不是待補功能，因此不列入完整度分母。

---

## 二、評分方法

每一模組先以五項技術分數加總，再乘上該模組對 ForgeBase 現階段產品承諾的重要性。這使總分可重算，也避免六套漂亮範本把公司辨識、租戶安全或背景任務等重大缺口稀釋掉。

| 面向 | 權重 | 判斷方式 |
|---|---:|---|
| 資料與 API | 30% | 是否有資料模型、權限／租戶篩選、CRUD／公開 API 契約。 |
| 前後台操作 | 20% | 是否有可供訪客或內部人員實際操作的畫面。 |
| 核心流程 | 25% | 功能是否可從輸入到結果完成主要旅程，而非只有單一頁面。 |
| 測試與例外處理 | 15% | 是否有自動化測試、驗證、錯誤處理及資料一致性考量。 |
| 正式環境／外部驗證 | 10% | 是否已在正式環境可用，或已用 sandbox／真實服務完成必要驗證。 |

模組分數公式：`資料/API × 30% + UI × 20% + 核心流程 × 25% + 測試 × 15% + 正式驗證 × 10%`。

全產品分數公式：`Σ（各模組未四捨五入子分數 × 產品權重）= 78.13%，四捨五入為 78%`。產品權重總和為 100%；第一層占 55%、第二層占 36%、平台基礎占 9%。依同一矩陣重算，三層分別為 85%、64%、91%。

### 可重算評分矩陣

| # | 模組 | 資料/API | UI | 核心流程 | 測試 | 正式驗證 | 產品權重 | 加權後模組分數 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | B2B 製造業網站前台 | 87 | 92 | 84 | 72 | 84 | 9% | **85%** |
| 2 | 產業範本與參考站 | 88 | 96 | 90 | 86 | 88 | 4% | **90%** |
| 3 | 產品／內容／頁面管理後台 | 88 | 86 | 80 | 68 | 60 | 10% | **80%** |
| 4 | 素材與文件管理 | 90 | 75 | 82 | 82 | 72 | 4% | **82%** |
| 5 | 多語內容與語系網站 | 86 | 72 | 76 | 76 | 54 | 5% | **76%** |
| 6 | SEO、發布與快取更新 | 78 | 62 | 66 | 58 | 40 | 5% | **65%** |
| 7 | RFQ 詢價表單與收件 | 97 | 92 | 97 | 96 | 88 | 10% | **95%** |
| 8 | RFQ 業務處理、品質、SLA 與任務 | 98 | 96 | 97 | 97 | 96 | 8% | **97%** |
| 9 | 訪客追蹤與意圖評分 | 92 | 80 | 87 | 89 | 78 | 7% | **87%** |
| 10 | IP／公司辨識與聯絡人 enrichment | 21 | 23 | 11 | 5 | 5 | 6% | **15%** |
| 11 | 分群、動態 CTA 與高關注名單 | 84 | 71 | 70 | 67 | 50 | 4% | **72%** |
| 12 | AI Product Advisor 與 Chat → RFQ | 91 | 80 | 85 | 88 | 60 | 7% | **84%** |
| 13 | 成效、漏斗、內容歸因與 outcomes | 82 | 72 | 74 | 72 | 58 | 5% | **74%** |
| 14 | 通知、寄信與 nurture | 80 | 75 | 72 | 78 | 65 | 4% | **75%** |
| 15 | CRM、廣告、GSC、支付與外部整合 | 35 | 45 | 15 | 5 | 5 | 3% | **25%** |
| 16 | 多租戶、權限、方案與平台管理 | 96 | 94 | 95 | 94 | 88 | 6% | **94%** |
| 17 | 部署、監控與背景工作可靠性 | 90 | 75 | 88 | 86 | 84 | 3% | **85%** |

> 子分數是依目前證據做的工程判斷，不是假裝成統計精確度。它的用途是讓團隊能看出分數為何上升或下降；新增 UI 只會提高 UI 子分數，不能自動提高流程、測試與正式驗證分數。表內模組完整度統一採公式結果四捨五入；歷史補強表保留當時快照。

### 狀態定義

| 狀態 | 分數區間 | 含義 |
|---|---:|---|
| 可受控使用 | 75–100% | 主流程已具備，可在明確範圍與人工監督下使用。 |
| 部分可用 | 50–74% | 已有程式與畫面，但存在重要缺口、未驗證整合或資料品質問題。 |
| 原型／骨架 | 25–49% | 有模型、路由、UI 或規則，但尚未形成可可靠交付的流程。 |
| 尚未形成產品能力 | 0–24% | 僅有概念、低階資料來源或缺少必要服務／驗證。 |

---

## 三、模組總覽

| # | 模組 | 完整度 | 狀態 | 對外描述邊界 |
|---:|---|---:|---|---|
| 1 | B2B 製造業網站前台 | 85% | 可受控使用 | NorthForge 與 AxisForm 皆可展示完整網站與採購導覽；Demo 公司／證書不得被當成真實案例。 |
| 2 | 產業範本與參考站 | 90% | 可受控使用 | handtool 與 precision 兩種 CMS adapter 已正式驗證；其他靜態 Demo 仍會被交付 gate 阻擋。 |
| 3 | 產品／內容／頁面管理後台 | 80% | 可受控使用 | 可由公司人員維護，且新租戶會建立品牌與網站交付設定；內容治理仍需人工。 |
| 4 | 素材與文件管理 | 82% | 可受控使用 | 已有串流式暫存、簽章檢查、配額與 SHA-256；惡意檔案掃描及 R2 災難復原仍待驗證。 |
| 5 | 多語內容與語系網站 | 76% | 可受控使用 | 英／繁中內容、Chat 語言鏈與核心 SEO 語系標記已打通；實際翻譯仍由人工負責。 |
| 6 | SEO、發布與快取更新 | 65% | 部分可用 | metadata、hreflang、動態 sitemap、redirect、publish／revalidate 已有；搜尋實效未驗證。 |
| 7 | RFQ 詢價表單與收件 | 95% | 可受控使用 | 表單、challenge、honeypot、可選 Turnstile、durable 建立後副作用與錯誤恢復已形成閉環；仍需正式流量下觀察 spam 率。 |
| 8 | RFQ 業務處理、品質、SLA 與任務 | 97% | 可受控使用 | 日常案件工作台、角色隔離、指派、跟進、備註、歷程、垃圾隔離、重複合併、結案金額與 CSV 已完成正式操作驗收；Resend 已驗證但預設不實寄，CRM 真實同步仍須 sandbox。 |
| 9 | 訪客追蹤與意圖評分 | 87% | 可受控使用 | consent 可撤回、visitor identity 一致並可伺服器刪除匿名分析資料；意圖分數仍只作人工參考。 |
| 10 | IP／公司辨識與聯絡人 enrichment | 15% | 尚未形成產品能力 | 只有 IP 地理／ISP 基礎查詢；沒有可靠 B2B 公司／聯絡人資料供應商串接。 |
| 11 | 分群、動態 CTA 與高關注名單 | 72% | 部分可用 | Segment 已租戶隔離，CTA 支援語系、發布狀態、曝光與頻率上限；A/B 實驗與增量驗證仍待完成。 |
| 12 | AI Product Advisor 與 Chat → RFQ | 84% | 可受控使用 | 中英文、一次性草稿、grounding、claim warning、持久化稽核與高風險降級均已形成；答案仍需人工監督。 |
| 13 | 成效、漏斗、內容歸因與 outcomes | 74% | 部分可用 | visitor／RFQ cohort 已分離、生命週期口徑可解釋，並保存提交快照與最低樣本門檻；尚不可作因果或計費保證。 |
| 14 | 通知、寄信與 nurture | 75% | 可受控使用 | Resend 已在正式環境用官方虛擬收件位址驗證；通知、auto-reply 與 nurture 共用寄信服務，dry-run 不會被記成實寄。正式環境仍鎖在不實寄模式。 |
| 15 | CRM、廣告、GSC、支付與外部整合 | 25% | 原型／整合待驗證 | 有 connector／設定入口；未用 sandbox 做完整驗證，不應對客承諾。 |
| 16 | 多租戶、權限、方案與平台管理 | 94% | 可受控使用 | 兩個 connected tenant 已驗證核心隔離；平台營運者可掌握待處理租戶、修補交付單、管理網域／語系／範本、受控發布與查閱操作紀錄。 |
| 17 | 部署、監控與背景工作可靠性 | 85% | 可受控使用 | deep health、scheduler、outbox、100 併發與單租戶服務復原已驗收；尚缺外部監控與 off-site restore。 |

---

## 四、逐項技術盤點

### 1. B2B 製造業網站前台 — 85%

**已實作**

- 首頁、產品分類、產品詳情、應用、製造能力、證書、FAQ、新聞、公司頁、聯絡頁與 RFQ 頁。
- Next.js 前台有 desktop／mobile 版面與 i18n route 結構。
- NorthForge 與 AxisForm 已在正式環境作為兩種不同產業的完整 connected tenant；前台均由 API／後台資料提供。

**技術證據**

- `web/src/app/[locale]/` 下已有產品、應用、證書、FAQ、RFQ 等頁面路由。
- `web/src/components/` 有產品、內容、表單、Chat 與 UI 元件；前台 TypeScript 與 lint 已於本次通過。

**缺口與風險**

- Reference Site 含示意公司、產品、文件與圖片，必須保留醒目測試告知。
- 內容正確性仍取決於企業人工輸入；系統不應被描述成自動理解或驗證工廠資料。

**判定**：網站展示與基礎採購導覽可受控使用。

### 2. 產業範本與參考站 — 90%

**已實作**

- 六套靜態產業範本：精密加工、工業機械、電子零組件、工業自動化、工程材料、客製包裝。
- 每套都有獨立頁面結構與視覺方向，不是單一樣板只換圖片。
- NorthForge Tools 與 AxisForm Precision 都已串接 ForgeBase 後端；兩者使用不同 layout、品牌、內容、資產與公開 host。
- 正式站第二輪逐套檢查時，六套首頁均正常回應，且每套可見約 9–14 個不重複的站內範本路徑，確認不是只有一張首頁截圖。

**缺口與風險**

- 平台管理員已有「選範本 → 建租戶／owner／品牌資料 → 建交付單 → readiness 驗證 → 受控發布」流程，但視覺客製、內容搬入與實際 CMS adapter 串接仍需人工執行。
- 六套靜態 Demo 不具 CMS、RFQ、追蹤與 Chat adapter；系統會阻止它們被誤標為已完成的正式網站。

**判定**：六套可作為高品質銷售展示與設計確認素材，平台也已能管理交付狀態與發布條件；但從靜態版型自動生成完整租戶網站仍不是現有能力。

### 3. 產品／內容／頁面管理後台 — 80%

**已實作**

- 產品、分類、應用、能力、證書、FAQ、頁面、比較內容、CTA、轉址等內容模型與 CRUD。
- 草稿／發布狀態、圖片／文件關聯、語系欄位、SEO 欄位與內容後台路由。
- Admin 已有相對應列表、新增、編輯頁；2026-08-13 驗收記錄顯示核心 CRUD、角色與路由可操作。

**技術證據**

- API：`content_crud.py`、`products.py`、`categories.py`、`relations.py`、`publish.py`。
- Admin：`admin/src/app/(dashboard)/dashboard/` 內有 products、pages、faqs、applications、capabilities、certifications、comparisons、ctas、redirects 等路由。

**缺口與風險**

- 沒有網站內容 AI 自動生成／發布，這是既定產品邊界。
- 需要持續補足所有公開內容欄位的統一 HTML sanitize、審核紀錄與安全測試。
- 客戶資料品質與人工審核流程尚未產品化為完整內容治理工作流。

**判定**：可作為第一層產品的主要交付能力。

### 4. 素材與文件管理 — 82%

**已實作**

- 可上傳圖片、PDF、CAD／試算表類素材，建立 R2 key、public URL、alt text、title、SEO title，並關聯產品或頁面。
- 支援列表、更新 metadata、刪除與基本影像驗證／WebP 壓縮。
- 資產模型已帶 `tenant_id`；目前列表、更新、刪除皆以 tenant 篩選。

**技術證據**

- `api/app/models/content_asset.py`
- `api/app/api/v1/endpoints/assets.py`

**缺口與風險**

- 已改為分段讀取及 `SpooledTemporaryFile`，大型非圖片檔不再整份常駐記憶體。
- 已加入 PDF、XLS/XLSX、STEP/IGES 的副檔名／檔案簽章檢查、空檔拒絕、每租戶容量配額、SHA-256 checksum 與 R2 metadata。
- 尚缺防毒／惡意內容掃描、檔案版本治理、R2 sandbox／正式回復與災難復原演練。
- `is_indexable` 只有欄位，尚未形成可用的 PDF 知識索引流程。

**判定**：一般網站素材可受控使用；不能宣稱為完整文件知識庫。

### 5. 多語內容與語系網站 — 76%

**已實作**

- 路由支援 `en` 與 `zh-TW`，CMS 多數內容模型有 `locale`。
- 前台與部分 Admin 有翻譯字典、語系切換與缺漏提示基礎。

**正式環境第二輪確認**

- `https://pcbrm.tw/northforge-tools/zh-TW` 的文件語系已正確為 `lang=zh-TW`，代表路由與頁面骨架不是空殼。
- 同一繁中首頁仍可見多段應用與證書英文內容，頁面也明確顯示「部分內容暫以英文顯示」。
- 繁中 AI 客服的按鈕與輸入提示已中文化，但開場訊息與三個建議問題仍是英文，證明 Chat 只完成介面局部翻譯，尚未形成完整多語對話體驗。
- 多個公開連結、canonical、sitemap、hreflang 與 locale prefix 尚未全鏈路一致。
- 2026-08-14 已實測：訪客在英文頁輸入中文，Chat 仍因頁面 locale 被強制要求以英文回答。
- Chat 的 greeting、suggestions、fallback、追問與意圖規則多為英文硬編碼。

**第三輪補強**

- Chat locale 會正規化；使用者訊息若含中文，優先採 `zh-TW`，不再被英文頁面 locale 覆蓋。
- greeting、suggestions、安全 fallback、商務追問與中文採購意圖詞均有繁中版本；繁中 handoff 會進入 `/zh-TW/rfq`。
- 新增 `GET /content/locale-coverage`，可逐一查看產品、分類、應用、頁面、FAQ、比較、證書與能力的翻譯／發布覆蓋與缺漏 key。
- 此模組仍不自動生成或發布翻譯；內容正確性維持人工負責，符合產品既定邊界。

**判定**：有多語骨架，尚不是可承諾的雙語外銷網站體驗。

### 6. SEO、發布與快取更新 — 65%

**已實作**

- SEO title、description、canonical、robots、sitemap、redirect 管理與發布流程。
- 發布／更新後具備前台 revalidate 設計；ContentFlow 發布契約也有 idempotency 與 HTML sanitize 方向。

**缺口與風險**

- 核心頁 canonical／hreflang／x-default 與動態 sitemap 已統一；只有實際存在的繁中動態內容會進 sitemap，fallback 頁會 noindex。
- 尚未以 Search Console、實際 crawl、Core Web Vitals 與長期收錄驗證。
- ContentFlow／SearchOps 為獨立產品的可選 API 串接，不能描述成 ForgeBase 內建 SEO 自動帶流量。

**判定**：有網站 SEO 基礎；尚不具可量化 SEO 成效能力。

### 7. RFQ 詢價表單與收件 — 95%

**已實作**

- 公開 RFQ 表單收集聯絡資料、公司、國家、產品、用途、數量、規格、Incoterm、年量、證書、目標價、時程、來源頁與 consent。
- 可建立 RFQ、Contact、產品關聯、事件紀錄、品質分數與 SLA due date。
- Admin 可列出、查看完整 RFQ，前台與後台基本流程在既有驗收中通過。

**技術證據**

- `api/app/api/v1/endpoints/rfqs.py`
- `api/app/models/rfq_request.py`、`rfq_event.py`、`contact.py`
- `web/src/app/[locale]/rfq/`、`admin/.../dashboard/rfqs/`

**缺口與風險**

- RFQ 當日編號已用 PostgreSQL transaction advisory lock 序列化配置，並保留 unique index 作最後防線。
- visitor、product、application、Chat draft 皆驗證租戶 ownership 與 published／未過期狀態；文字長度、UUID、清理與 mutable default 已補強。
- Chat handoff 現為 24 小時、綁 tenant／visitor／chat session、只能消耗一次的伺服器端 RFQ draft；網址只帶 draft token。
- 已加入租戶綁定且具時效的 HMAC challenge、honeypot、既有限流與可選 Cloudflare Turnstile；正式上線若設定 Turnstile site／secret key 可強制驗證。
- 仍缺附件式詢價，以及正式公開流量下的 spam／濫用率驗證與門檻調校。

**判定**：人工 RFQ 與 Chat 引導後、由訪客確認送出的 RFQ 均可受控測試；對外測試時應啟用 Turnstile 並觀察誤擋與 spam 率。

### 8. RFQ 業務處理、品質、SLA 與任務 — 97%

**已實作**

- RFQ 狀態：new、assigned、in_progress、quoted、negotiation、won、lost、expired。
- 單一「詢價案件」工作台可依公司／姓名／Email／案件編號搜尋，並依案件階段、負責人、跟進期限及一般／垃圾／已合併資料夾篩選。
- 主管可指派同租戶有效業務；業務只能讀寫分派給自己的案件，行銷角色保留唯讀歸因視角。
- 指派負責人、下次跟進、內部備註、不可變處理歷程、優先度、首次回覆、報價送出、成交／流失原因與成交金額。
- 垃圾詢價採隔離與還原，不刪除原始紀錄；重複詢價可由主管合併並保留來源案件與雙向事件。
- 主管可匯出 UTF-8 CSV；案件詳情可查看產品、來源頁、訪客歷程及 HubSpot／Salesforce connector 狀態介面。
- 依買家國別時計算工作時段 SLA；有逾期掃描、提醒與 escalation 程式。
- Admin 以單一「詢價案件」入口取代「我的／全部 RFQ」雙入口；技術分數、來源與 CRM 等資訊預設收合，避免增加日常操作負擔。

**技術證據**

- `api/app/api/v1/endpoints/rfqs.py`、`api/app/models/rfq_note.py`、`api/app/db/migrations/versions/0069_rfq_sales_workspace.py`
- `admin/src/app/(dashboard)/dashboard/rfqs/`、`admin/src/app/(dashboard)/dashboard/tasks/page.tsx`
- 對應測試：`test_rfq_sales_workspace.py`、`test_rfq_quality.py`、`test_rfq_sla.py`、`test_rfq_speed_features.py`。

**缺口與風險**

- RFQ routing、通知、HubSpot、Copilot、auto-reply 與 Chat handoff 已改以 `operational_jobs` durable outbox 記錄，支援 idempotency key、重試、指數退避、卡住工作回收與失敗查詢 API。
- 新增 job health summary、租戶權限隔離的人工 retry，以及每五分鐘 failed／stale 掃描與選用 webhook 告警。
- 站內「今日待辦」與跟進期限已形成閉環；Resend Email 已完成隔離供應商驗證，但正式持久設定仍是 dry-run，且未配置內部通知收件箱。Telegram／LINE 等通訊軟體提醒尚未驗收，目前不得自動寄信給實際 Leads。
- HubSpot 僅顯示既有 deal link 狀態，Salesforce 為保留 connector 介面；尚未完成兩者的真實雙向同步。
- 自動 routing 大多依環境變數與規則，尚非完善的 tenant 級可視化配置。
- AgentOS 與 webhook 仍有部分同步／process 內副作用，尚未全部納入同一外部工作平台。

**判定**：業務人員每天處理 RFQ 所需的站內流程已可受控使用；剩餘缺口集中在站外通知、CRM sandbox 與更完整 tenant 級 routing 設定，不應把保留介面宣稱為已串接。

### 9. 訪客追蹤與意圖評分 — 87%

**已實作**

- Visitor、session、page view、CTA、RFQ、Chat 等事件與 intent score／stage。
- 四個 facet：產品興趣、信任驗證、採購準備度、急迫性。
- Admin 有訪客列表、事件、旅程、意圖與高關注訪客任務檢視。

**技術證據**

- `api/app/models/visitor.py`、`tracking_event.py`、`tracking_session.py`
- `api/app/api/v1/endpoints/events.py`、`visitors.py`
- `api/app/services/intent_scoring.py`、`intent_facets.py`

**缺口與風險**

- 已加入前台 consent banner；未同意前不載入 GA、不送分析事件、不寫一年期 visitor cookie，只保留 Chat／RFQ 所需的 session identity。
- Tracking API 要求明確 `analytics_consent=true`；visitor／session ID 與 tenant／visitor 不一致時回 409，並修正 forwarded IP 取可信代理最後一段。
- CTA impression 已成為零分事件，可用於頻率控制而不誤增意圖分數。
- intent score 是規則性線索，不是已證明的購買意圖；沒有足夠 outcome sample 前不可據此自動決策。
- Cookie 政策頁新增偏好管理；撤回時伺服器刪除該識別碼的 tracking events／sessions 並重設意圖資料，但保留已送出的 RFQ、Chat 與 Contact。
- 新增 keyed-hash consent audit 與預設 180 天 analytics retention；法務文字與實際保留天數仍須由營運者確認。

**判定**：可作為內部觀察資料；不應當作可保證的 Lead scoring。

### 10. IP／公司辨識與聯絡人 enrichment — 15%

> 後續正式方案與驗收門檻請見 `FORGEBASE_COMPANY_IDENTIFICATION_AND_CONTACT_ENRICHMENT_PLAN_2026-08-16.md`。本連結只記錄已確認的執行方向；在供應商授權、程式實作、Shadow Mode 與正式驗收完成前，本節分數維持 15%。

**已實作**

- `ip_resolver.py` 可呼叫 ip-api 取得國別、城市、網路組織（org／ISP）等基礎資料。
- IP 為 private／loopback／link-local 時會拒絕查詢；有 timeout 與錯誤 fallback。
- 目前程式甚至直接由 `org` 字串推導 `company_name`；這只是方便 UI 顯示的猜測，不應視為公司識別結果。

**未完成的關鍵能力**

- 沒有 Leadfeeder、Leadinfo、Albacross、RB2B、IPinfo 商業 company API、People Data Labs 或 Clay 的正式串接。
- 沒有 provider abstraction、tenant API key／計費隔離、waterfall、可信度、覆蓋率、cache、同意／隱私政策或資料保留策略。
- 沒有聯絡人資料供應商、聯絡人來源、可驗證 company／person enrichment、可審計匯入流程。
- ip-api 的 `org` 不等於公司身分，更不等於進站者本人。

**判定**：目前只能說「有 IP 基礎網路資訊」，不能說「可辨識來訪公司或找出企業聯絡人」。

### 11. 分群、動態 CTA 與高關注名單 — 72%

**已實作**

- Segment、Audience Tag、CTA、intent rule、dynamic CTA、hot visitor task queue 等資料模型、API 與 Admin 頁面。
- 可依意圖分數、facet、是否已 RFQ、訪客事件等產生內部名單與任務。
- 高關注但未送 RFQ 的訪客、低品質 RFQ、SLA 逾期等已有任務佇列邏輯。

**缺口與風險**

- Segment 已新增不可為空的 `tenant_id`，CRUD、evaluate 與 ESP sync 均以租戶查取，不再共享全域 segment definition。
- 動態 CTA 已按 locale 選擇內容；同一訪客 24 小時內同 CTA 曝光達 3 次會 frequency cap，並回傳 decision id、曝光事件與 cap 資訊。
- 動態 CTA 仍以規則與有限頁面情境為主，尚無完整 A/B experiment assignment、統計顯著性與增量成效驗證。
- 來自 visitor score 的上游資料品質尚未成熟，故分群輸出只能作業務參考。
- 目前沒有可靠的「公司辨識 → 分群 → 可寄信聯絡」閉環。

**判定**：內部營運工具可試用；不能宣稱為成熟個人化／ABM 平台。

### 12. AI Product Advisor 與 Chat → RFQ — 84%

**已實作**

- 前台 Chat Widget、桌機 Panel、手機 Sheet、Chat session／message API。
- 可帶入首頁、產品、分類、應用頁 context，並顯示 sources、建議問題與 RFQ handoff UI。
- Admin 有對話列表、詳細頁、人工評分與備註；有基本 system prompt，限制價格、交期、法規與不支援宣稱。

**本次補強與剩餘邊界**

- 上述語言問題已修正：中文訊息優先採繁中，且 greeting、suggestions、fallback、追問與採購詞彙已有繁中版本。
- 公開 Chat 已具 tenant／visitor／session ownership、方案 gate、每日 tenant 與每 session 訊息上限；Chat tracking event 也保存 tenant_id。
- Chat → RFQ 已採一次性伺服器草稿，完整帶入 message、requirement summary、多產品與 application，提交後保存來源 chat／draft。
- 來源已限制為系統查得且已發布的 product／category／application／FAQ／certification；不接受模型自行提供未知來源。
- 新增 prompt injection 阻擋、認證／合規證據不足時的安全降級，以及 `grounded`／`limited`／`blocked` 與 claim warnings 回傳欄位。
- 尚未建立 PDF 向量索引、完整 RAG 與大規模答案評測集；grounding 代表「有核准內容來源」，不代表外部事實已由 ForgeBase 驗證。

**判定**：多語 Chat → RFQ 與來源／高風險安全邊界可做限定 tenant 的對外測試；仍不可承諾為可獨立回答所有問題的「可靠 AI 業務顧問」。

### 13. 成效、漏斗、內容歸因與 outcomes — 74%

**已實作**

- Dashboard／growth ops 提供本月合格 RFQ、首次回覆、SLA、RFQ 狀態、來源頁、建議任務。
- 有 traffic → high intent → RFQ → qualified → quoted → negotiation → won 漏斗。
- 有內容來源歸因、成交／流失原因與 facet outcome feedback。

**缺口與風險**

- 報表現已回傳 `cohort_start` 與 methodology；traffic／high-intent 採期間首次出現的 visitor cohort，RFQ 業務層採期間建立的 RFQ cohort，業務狀態為互斥的目前狀態。
- RFQ 提交時保存 intent score、四 facet 與 traffic source／campaign／referrer／page／locale 快照；outcome feedback 不再拿訪客後續變動值回推。
- outcome feedback 需至少 10 筆 snapshot RFQ、其中 3 筆 won 才標示 statistically actionable；未達門檻不自動產生 facet 行動任務。
- 目前報表是「營運觀察」，不能作為收費 by leads／by conversion 的精確計費依據。
- 歸因目前仍偏 last-touch snapshot，尚缺多觸點模型、歷史 reached-stage ledger 與真實長期樣本。

**判定**：可協助人工檢視；尚不具商業成效歸因與自動優化可信度。

### 14. 通知、寄信與 nurture — 75%

**已實作**

- Notification preference、notification log、reply template、nurture sequence／outbox、email／ESP service 程式與 Admin 頁面。
- RFQ 指派、提醒、逾期 escalation、auto-reply 等有對應服務介面。
- Resend、SendGrid 共用結構化寄送結果；可區分 `success`、供應商實際接受的 `delivered` 與 `dry_run`，並回傳 provider message ID；auto-reply event 與測試 API 可保存／呈現該識別值。
- RFQ 新案內部通知、業務指派、24 小時提醒、48 小時升級、RFQ auto-reply 與 nurture 已統一走同一 ESP，不再由 RFQ 通知另走未配置 SMTP。
- Resend 請求加入 `User-Agent` 與冪等鍵；測試信、RFQ auto-reply、通知與 nurture outbox 都有對應 idempotency key，降低背景重試造成重複寄送的風險。
- 後台 `/dashboard/integrations` 可顯示 provider、寄件人、是否已配置、`安全模式：不實寄`／實際寄送狀態；API key 不會回傳到瀏覽器。
- 測試信在 live 模式預設只接受 Resend 官方 `delivered@resend.dev` 與其 `+label` 變體，其他真人地址必須另外加入 allowlist。
- Resend 平台 key 已存入 Linode 未版控的 `deploy/api.env`，權限為 `600`；寄件網域 `premierbiz.com.tw` 已由供應商標示為 verified。
- 已從正式 ForgeBase image 暫時覆寫 `EMAIL_DRY_RUN=false`，向 Resend 官方虛擬地址送出一次測試並取得 provider message ID；永久 API 容器重啟後仍確認 `EMAIL_DRY_RUN=true`。

**缺口與風險**

- 本次只驗證 Resend「供應商接受」與官方測試收件位址，不等於真人信箱收件、退信、投訴、開信、點擊、unsubscribe 或 webhook lifecycle 已驗證。
- 目前是平台共用 Resend key／寄件網域；尚未完成每租戶自有寄件網域、DNS 驗證、憑證選擇、用量／成本隔離與寄件聲譽隔離。
- `SALES_NOTIFY_EMAIL`、`MANAGER_EMAIL` 仍未配置；Reference Site 的 `auto_reply_enabled` 維持關閉。這是刻意的安全邊界，不應把它描述成「已對 Leads 啟用自動聯繫」。
- Nurture 可由管理員審核 outbox，但尚缺退訂抑制清單、bounce／complaint webhook、全租戶寄送上限、聲譽監控及實際名單的 deliverability 驗收。
- Telegram、LINE 與 CRM 外部提醒仍未納入本次供應商驗收；其他外部副作用也尚未全部統一成跨服務工作平台。
- IntegrationCredential 資料表已支援 tenant scope，但目前 Resend runtime 使用平台環境變數；後台若要讓各租戶自行帶 key，仍需完成 runtime credential resolver，而不是只保存加密欄位。

**判定**：可在平台控制開關、限定收件人與人工監督下使用；目前最合適的正式狀態仍是「已接通、可驗證、預設不實寄」，尚未達多租戶自助寄信或行銷外聯平台成熟度。

### 15. CRM、廣告、GSC、支付與外部整合 — 25%

**已實作**

- 服務／endpoint 名稱包含 HubSpot、Google Ads、Meta Conversions、GSC、Webhook、ESP、PayPal、Telegram、LINE 等。
- Admin 有 integrations、billing、notifications 等設定與檢視入口。
- 架構文件已定義 ForgeBase 與 ContentFlow／SearchOps 為獨立產品，應走 API 契約，不共用資料庫。

**缺口與風險**

- 尚未以每個供應商 sandbox／測試帳號驗證認證、webhook、資料格式、重試、錯誤復原、成本與取消流程。
- 憑證權限、方案 gate、tenant isolation 與外部寫入審批仍需做完整安全驗收。
- 尚未實作可被客戶自行安全開通與維護的整合導入流程。

**判定**：可列為技術方向／預備 connector，不能列為已交付整合能力。

### 16. 多租戶、權限、方案與平台管理 — 94%

**已實作**

- Tenant、User、SiteProfile、IntegrationCredential 等模型與 tenant-scoped 內容模型。
- Admin 具 owner、admin、marketing manager、sales、super-admin 等角色與平台管理頁。
- 既有 UAT 已驗證角色側欄、直接輸入受限網址的 403、租戶與使用者平台頁。
- 部分 API 已使用 `RequireFeature` 及 plan matrix。
- 平台後台可一次建立 tenant、owner、plan、SiteProfile 與 SiteBuild；可選七種範本並執行 readiness／publish 控制。
- AxisForm Precision 已以獨立 host、profile、copy、asset manifest、CMS 內容、Chat 與 RFQ 上線；正式 smoke test 證明不會讀寫 NorthForge 資料。
- 平台總覽新增已發布網站、待處理租戶、失敗背景工作與近 30 天 RFQ，並提供可直接進入租戶詳情的跨租戶待辦清單。
- 租戶清單可依啟用狀態、方案、網站交付狀態與「只看待處理」篩選，並顯示正式網域、近期 RFQ、最近活動及待補原因。
- 舊租戶若缺少 SiteBuild，可由平台詳情頁補建；已可維護範本、正式網域與公開語系，且未儲存交付異動時會禁止發布。
- 租戶停用改為二次確認並明示影響；tenant、SiteBuild、readiness 與發布操作會寫入平台稽核紀錄，發布遭阻擋亦留痕。

**缺口與風險**

- 停用租戶會封鎖其使用者登入後存取與公開 host／slug 解析；tenantless 帳號不能繞過 feature／quota gate。
- plan 更新只接受既有方案，並同步 quota；公開 tracking／Chat／RFQ 核心 identity 均有 tenant ownership。
- 靜態 Demo 與 CMS adapter 明確分流；新交付單預設 `cms_connected=false`，必須由平台管理員確認串接、網域與品牌條件後才能標記發布。
- 外部憑證與公開識別資料仍需更完整的跨租戶安全封板；平台 audit log 已完成，但既有歷史操作不回填，且尚無 off-site 匯出與 step-up 驗證。
- 管理後台登入品牌已改為 ForgeBase，並以產品／內容／RFQ／訪客意圖管理描述能力，不再宣稱 B2B 電商或免費自助試用。

**判定**：平台管理員已可執行受控租戶開通、跨租戶營運監看與網站交付；仍不等於一般客戶可自助購買、自動架站或自動配置網域。

### 17. 部署、監控與背景工作可靠性 — 85%

**已實作**

- Docker Compose、Nginx、Web／Admin／API／PostgreSQL 拆分、health endpoint、scheduler、tracing wrapper 與 production deployment 文件。
- 正式站目前已可提供 ForgeBase 官網、NorthForge、AxisForm、範本與後台路由。
- 最新部署已在 Linode 完成：映像標記、API／兩個 Web build、migration `0067`、8 個常駐服務與一次性 migration job 均正常；依開發階段指示未另做資料庫備份。
- Code Review 發現 Docker tag 含大寫時間字元會使首次流程在備份／build 前安全中止；已改成全小寫 tag，重新部署成功且留下可追溯回復清單。

**缺口與風險**

- production compose 明確固定單一 API worker 承擔 scheduler；若未來水平擴展，仍需拆獨立 worker 或加入 distributed lock。
- 新增資料庫型 `operational_jobs`，具 idempotency、retry ledger、指數退避、失敗狀態、卡住工作回收與查詢 API；但尚非獨立 worker／dead-letter 與跨服務工作平台。
- 已具資料庫備份、舊映像標記、全服務 build、migration、deep readiness smoke test 與應用映像 rollback 腳本；資料庫 rollback 刻意要求人工審核。
- API healthcheck 已成為 Web／Admin／Caddy 啟動依賴；背景工作有 summary、retry 與選用 webhook 告警。
- 已完成單一 tenant web 停止／復原演練：AxisForm 停止時 ForgeBase 官網、NorthForge 與 API 持續可用，AxisForm 於 8 秒內恢復；仍缺跨區外部監控、off-site restore 與 CI 自動 gate。

**判定**：具備受控對外測試所需的部署與復原骨架；在正式演練前仍不足以承諾高可用 SLA。

### 最終 Code Review 與 UIUX 回歸重點

- RFQ 建立後的 routing、通知、HubSpot、Copilot、auto-reply、AgentOS 與 webhook 全部進 durable outbox，公開請求不再等待外部服務；任務只保存 RFQ ID，不在 payload 複製個資。
- 相同 ContentFlow idempotency key 的 PostgreSQL 競態已用 transaction advisory lock 修正；完整 DB 測試覆蓋實際併發路徑。
- RFQ 指派只會把 `new` 推進到 `assigned`，不再把 `in_progress` 等較後狀態倒退。
- outcomes 將 visitor cohort 與 RFQ cohort 分離；不再用不同分母顯示誤導轉換率，quote／negotiation／won 以累積生命週期呈現。
- AI 的 `grounded／limited／blocked` 與 claim warnings 已寫入資料庫、API 與後台；limited／blocked 不附來源、不顯示不恰當 CTA。
- 瀏覽器驗收發現語系切換在 client navigation 後保留舊 root provider；已改為保留 base path 的完整文件導覽。英文→繁中→中文產品頁→英文的雙向點擊回歸通過。
- 平台健康、任務、成果漏斗、CTA 狀態、租戶開通表單與 RFQ 表單均以真人操作檢查，不只確認畫面存在。
- RFQ 工作台以可刪除的正式驗收案件實際走過搜尋、主管指派、內部備註、狀態更新、跟進時間、今日待辦與回到期限篩選；瀏覽器驗收抓出 `datetime-local` 事件相容性與 UTC 缺少 `Z` 導致的 8 小時偏移，修正後重新載入仍顯示原訂本地時間。
- Email delivery result 現在明確區分 dry-run 與 provider accepted；RFQ auto-reply 不會因模擬寄送而寫入 `auto_reply_sent` 或 `first_response_at`，nurture outbox 也不會在 dry-run 時前進步驟。
- RFQ 內部通知已移除獨立 SMTP 實作並統一走 Resend／SendGrid ESP；動態內容經 HTML escape，後台連結改用 production `ADMIN_URL`，避免硬編碼錯誤網域。
- 正式瀏覽器實測 integrations 頁與測試信互動；畫面正確顯示「安全模式：不實寄」，操作結果不再誤稱已寄出，並修復 Dialog 缺少 description 的無障礙警告。

---

## 五、驗證紀錄與限制

### 本次實際驗證

| 項目 | 結果 |
|---|---|
| Web TypeScript | 通過：`npm.cmd run type-check` |
| Web lint | 通過：`npm.cmd run lint` |
| Web production build | 通過：Next.js 16.3.0，24 個靜態頁資料批次與全部 route 完成。 |
| Admin TypeScript | 通過：`npm.cmd run type-check` |
| Admin lint | 通過：`npm.cmd run lint` |
| Admin production build | 通過：Next.js 16.3.0，58 個 dashboard／platform route 完成，含 `/platform/tenants/new`。 |
| API migration | 本機與 Linode 正式 PostgreSQL 均確認 head 為 `0069_rfq_sales_workspace`；migration 成功執行。 |
| API 完整 DB 整合 | 最終 **164 passed, 2 skipped**；完整 PostgreSQL 套件重跑通過。兩項 skip 為既有條件式測試，不是本輪失敗。 |
| 新增收尾測試 | `test_round3_closeout.py`：簽章 challenge、AI injection／compliance 降級、範本發布邊界與 consent 撤回刪除共 **4 passed**。 |
| Resend／寄信安全測試 | 新增 `test_email_delivery_safety.py`：dry-run 與實寄分離、缺 key 不假成功、Resend payload／User-Agent／冪等鍵、測試收件人 allowlist、HTML escape 與正式 Admin URL 共 **5 passed**。本輪一般 API 測試環境另為 **107 passed, 64 skipped**；skip 主要是未提供外部 PostgreSQL／整合條件，不取代前述完整 DB 套件紀錄。 |
| Resend 正式供應商鏈路 | Linode `forgebase-api` 以一次性 `EMAIL_DRY_RUN=false` 向 `delivered+forgebase-integration@resend.dev` 送出，結果為 success／delivered、取得 provider message ID；該地址為供應商測試位址，不會寄達真人。永久容器仍為 dry-run。 |
| Email 後台 UIUX | `/backend/dashboard/integrations` 真人操作確認 provider、寄件人、已配置、使用中與「安全模式：不實寄」；測試按鈕回覆「模擬流程已完成；安全模式未實際寄出郵件」，瀏覽器無新增 error。 |
| ForgeBase 正式官網 | `https://pcbrm.tw/` 正常，定位、兩階段功能邊界、NorthForge 測試聲明與六套範本入口均可見。 |
| NorthForge 英文站 | `https://pcbrm.tw/northforge-tools/` 正常；完整產品、應用、證書、內容與 RFQ 導覽存在，根頁語系為 `en`。 |
| NorthForge 繁中站 | `https://pcbrm.tw/northforge-tools/zh-TW` 正常且文件語系為 `zh-TW`；英文→繁中→產品頁→英文的實際點擊流程通過，導覽、CTA 與 AI 入口均同步切換。部分尚未翻譯的應用／證書仍清楚標示英文 fallback。 |
| AxisForm 第二動態租戶 | `https://axisform.172-233-64-5.sslip.io/` 正常；首頁、分類、產品、應用、品質、公司、聯絡、RFQ、tenant 文案、圖片與 AI 均以正式瀏覽器操作通過。 |
| 六套產業範本 | 六個正式 URL 均正常回應且具有多頁站內連結；仍屬靜態 Demo，不計為已串 CMS 的租戶。 |
| 後台入口 | `https://pcbrm.tw/backend/login` 正常；正式站登入品牌、產品定位與表單標籤均已更新為 ForgeBase。 |
| Chat 語言與 grounding | 正式瀏覽器實測 NorthForge 中文問答與 AxisForm 英文 grounded／unsupported 問題；語言一致，證據不足時明確拒絕推論認證／產能。 |
| RFQ 完整閉環 | 正式 UI 建立 `RFQ-20260815-002`，quality score 100；7 個 durable job 完成、錯誤 tenant 為 0、auto-reply 關閉，最後標示 `won-test-only`，未執行聯繫。 |
| RFQ 業務工作台 | 正式 UI 建立可刪除驗收案件，完成搜尋、指派、備註、狀態、跟進、今日待辦與期限篩選；驗收資料與臨時帳號最後均精準清除，未聯繫任何人。 |
| 多租戶與負載 smoke | 兩租戶 profile 與 model 隔離、跨租戶 Chat 寫入 404、資產 health `ok`；100 個併發 GET 零失敗，最終驗收為 22.7 req/s。 |
| 正式部署 smoke test | `pcbrm.tw`、NorthForge、AxisForm、範本與後台均可用；8 個常駐 Compose 服務正常、migration job 完成，API／兩個 Web healthy。 |
| 安全部署與回復點 | 已執行兩次 safe deploy；資料庫備份為 `/opt/forgebase/backups/database-20260815T050457Z.sql.gz`、`database-20260815T051433Z.sql.gz`，最新映像回復清單為 `/opt/forgebase/backups/images-20260815t051431z.env`。 |

### 使用的既有驗證證據

- `ADMIN_ACCEPTANCE_REPORT_2026-08-13.md`：Admin 路由、角色、內容 CRUD、RFQ 操作、完整資料庫回歸 `133 passed, 2 skipped`；外部服務仍待 sandbox。
- `FORGEBASE_AI_CUSTOMER_SERVICE_AUDIT_2026-08-11.md`：AI Chat 的多語、安全、grounding、handoff、成本與營運缺口。
- `FORGEBASE_COMPREHENSIVE_AUDIT_2026-08-11.md`：多租戶、公開輸入、背景工作、部署與上市風險。

### 仍未完成的外部／正式驗證

- 本機 `.venv` launcher 的 base Python 仍失效；本輪改以系統 Python 3.13 加載既有 CP313 site-packages 執行，測試結果如上完整揭露。
- 真實 LLM、IP intelligence、CRM、Google／Meta、GSC、PayPal、Telegram、LINE、Cloudflare R2：仍未送出真實資料或費用，只能評估程式與設定骨架。ESP 中的 **Resend 已完成 provider sandbox／官方虛擬收件位址驗證**，但真人信箱 deliverability、bounce／complaint webhook 與租戶自有寄件網域仍未驗證。
- 最新 RFQ 工作台修正已於 2026-08-16 部署到 Linode，正式資料庫為 `0069_rfq_sales_workspace`；既有 API／Web／AxisForm release 與單一租戶服務復原證據仍保留。第一個 AxisForm release 沒有更早版本可供真正降版，下一次發布起才能演練前一版 image rollback。
- 部署時發現 API 與 migrate 曾被 Compose 建成不同映像；已改為共用 `forgebase-api` 映像，避免後續出現新 API 搭配舊 migration。
- 已完成 100 併發基準 smoke；容量上限、長時間 soak、滲透測試、法務／隱私合規、SEO 收錄與真實流量成效仍不在本次程式盤點範圍。

---

## 六、依商業定位的功能分級

### A. 應作為第一層固定月費核心；目前採受控導入交付

1. 產業範本選擇與有限客製。
2. B2B 公司／產品／應用／能力／證書／FAQ 網站。
3. 產品與內容後台。
4. 素材與文件管理。
5. 結構化 RFQ 收件。
6. RFQ 後台、人工指派、狀態與處理紀錄。

**對外說法限制**：可說「讓客戶自行了解產品、提出較完整詢價、讓公司集中處理」；不可說「保證曝光、保證 Lead、AI 自動成交」。

### B. 可列為第二層 roadmap／受控加值測試

1. 訪客行為與意圖分數。
2. 分群、動態 CTA 與高關注任務。
3. IP／公司辨識與聯絡人 enrichment。
4. AI Product Advisor 與 Chat → RFQ draft。
5. 內容、RFQ、成交 outcomes 分析。
6. ContentFlow／SearchOps 串接後的搜尋內容與轉換閉環。

**對外說法限制**：只能以「受控測試／可選串接／需依資料來源與驗證結果決定」描述；不得以已完整、可保證識別、可保證增加 Leads 或按 Lead 成果計費的名義銷售。

---

## 七、本輪範圍結案與後續門檻

### 已完成：第三輪收尾

1. RFQ 公開表單已加入租戶綁定、時效簽章 challenge、honeypot、既有限流及可選 Turnstile；正式測試前仍須填入 Turnstile site／secret key 並觀察真實 spam 與誤擋率。
2. 分析同意已具備 audit、偏好修改與撤回 API；撤回時刪除匿名事件／session 並重設訪客意圖欄位，RFQ、Chat 與 Contact 不會被誤刪；另有 180 天預設保留期清理。
3. 核心英／繁中頁面已統一 canonical、hreflang 與 x-default；中文 URL 若實際回退英文會 noindex，sitemap 不再宣告不存在的翻譯頁。
4. AI Product Advisor 只採用已發布的產品、分類、應用、FAQ 與證書資料作為可信來源；prompt injection 會被阻擋，認證／法規等高風險答案在缺乏證據時會降級並回傳 grounding 狀態與警示。

### 已完成：第一優先（部署、監控與背景工作可靠性）

1. 正式 Compose 加入 API deep readiness 與服務相依健康條件，API／migration 共用同一映像名稱。
2. 新增備份、安全部署與應用映像 rollback 腳本；safe deploy 會先備份資料庫、建置關鍵服務、執行 migration，再以 `/health/ready` 驗證。
3. operational jobs 新增健康摘要、權限化人工 retry 與 failed／stale 定期監控，可選 webhook 告警。
4. 尚待正式環境執行一次 safe-deploy 與 rollback drill；資料庫 rollback 因 migration 可逆性不同，維持人工明確操作，不在腳本中自動還原。

### 已完成：第二優先（多租戶、角色、方案與平台）

1. 停用 tenant 無法再登入或由 host／slug 被解析；tenantless 使用者不能繞過 feature／quota gate。
2. 平台方案更新會拒絕未知 plan，tenant／SiteProfile 異動後會清除 host cache。
3. 平台管理員可一次建立 tenant、owner、方案、品牌／聯絡資料與網站交付單；後台登入品牌文案已統一為 ForgeBase。
4. 營運總覽與租戶清單可辨識待處理租戶、失敗工作、近期 RFQ、網站發布狀態、正式網域與最近活動，並可依多種營運條件篩選。
5. 租戶詳情可補建舊租戶交付單、維護範本／網域／語系、執行 readiness 與發布；未儲存變更會鎖住發布，重送相同範本不會誤清除 CMS 確認。
6. 停用租戶採二次確認；tenant 與 SiteBuild 的建立、異動、驗證、發布及發布阻擋均寫入平台稽核紀錄。
7. `0068_platform_tenant_operations` 已部署至 Linode，正式健康檢查與 `pcbrm.tw/backend/platform/*` 真人操作驗收通過。
8. 尚未納入自助註冊、線上付款、自助取消與全自動資料刪除；目前定位仍是平台管理員受控開通。

### 已完成：第三優先（網站製作與交付流程）

1. 建立七種範本 registry：NorthForge／handtool 與 AxisForm／precision 為已驗證的 CMS adapter，其餘產業範本保留靜態 Demo 身分。
2. SiteBuild 記錄範本、網域、語系、客製設定、CMS 連線、驗證與發布狀態；primary domain 具資料庫唯一索引與 API 衝突檢查，避免跨租戶重複綁定。
3. readiness 會檢查有效 owner、品牌、聯絡資料、site URL、primary domain、語系、範本與 CMS adapter；靜態 Demo 不可被標示為 CMS connected 或正式發布。
4. 平台管理員必須明確確認 CMS adapter，系統不會因選到 handtool 範本就假裝已完成串接。

### 第四優先仍擱置；第五優先僅解除 Resend 基礎鏈路

1. **第四優先：IP／公司辨識與聯絡人 enrichment**——本輪未選定或串接 Leadfeeder、Leadinfo、RB2B、IPinfo、Clay 等服務，也未增加 provider 成本；模組維持 15%。
2. **第五優先：SEO 流量擴張、通知與 nurture**——本次只完成 Resend 平台寄信鏈路、發送結果語意、安全收件人限制、RFQ／nurture 共用服務、正式 provider 測試與後台 UIUX，因此模組 14 由 42% 上調為 75%。GSC、內容導流、自動外聯、真人名單 deliverability 與其他第三方整合仍擱置；模組 15 維持 25%。

### 正式部署結果與再次評分門檻

- 本輪程式已部署到 Linode；正式資料庫為 `0069_rfq_sales_workspace`。第二租戶 migration、readiness、100 併發 smoke、synthetic conversion、RFQ 業務工作台、服務復原與多租戶營運後台操作均已完成。
- 目前可用簽章 challenge／honeypot 進行封閉測試；若開放未知公開流量，仍建議配置 Turnstile。AxisForm 已確認 `auto_reply_enabled=false` 且測試閉環沒有對外聯繫。
- Email 永久設定為 `EMAIL_DRY_RUN=true`，Resend key 只存在 Linode `deploy/api.env` 且權限 `600`；repository 掃描未發現 Resend key。要切換 live，必須先明確設定內部收件人、逐租戶 auto-reply／nurture 權限與退訂／退信治理，不能只改一個環境變數。
- 下一次再調高分數，必須以正式環境證據、真實流量／spam 統計、R2／CRM sandbox、租戶交付實例，或 Resend 真人 deliverability／webhook／租戶寄件網域驗收為依據，不應只因新增 UI 上調。
