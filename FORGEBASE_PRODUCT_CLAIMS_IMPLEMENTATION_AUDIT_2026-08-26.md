# ForgeBase 產品宣稱與實作差距稽核紀錄

**稽核日期：** 2026-08-26\
**文件版本：** v1.0\
**稽核基準：** 本工作目錄當下的未提交工作樹\
**用途：** 記錄產品敘述與實際系統的吻合度，作為後續逐項決定「保留、修正文案、補實作、延後或移除」的討論底稿。

---

## 一、執行摘要

目前 ForgeBase **並未完全吻合原始產品敘述**。

核心產品方向已成立：

- B2B 官網 AI 產品／業務顧問。
- 以已發布網站資料及可選文件建立回答上下文。
- 對話朝產品選擇、需求釐清與 RFQ 推進。
- 英文／繁中內容管理與 AI 買方語系草稿。
- 第一方訪客行為追蹤、Intent Score、採購 facets 與顧客旅程。
- RFQ、SLA、業務工作台、成交漏斗與後台 AI 行銷助理。

但原始敘述中最強的自動化成長承諾尚未成立：

- 尚無可正式對外宣稱的 IP-to-Company 公司辨識。
- 尚無公司相關聯絡人候選搜尋與 Email 驗證。
- 尚無依匿名訪客旅程自動生成、寄送個人化陌生開發信。
- 尚無接收客戶 Email 回覆後自動升級為 Lead 的流程。
- 網站內容語系目前只有英文與繁中，不是任意多國語系。
- 多語內容是人工觸發 AI 草稿與人工發布，不是來源內容一改就自動同步所有語言。

因此，現階段最準確的產品定位為：

> ForgeBase 是多租戶 B2B 官網 CMS、可信 AI 產品顧問、訪客採購意圖與 RFQ 成交作業系統。企業揭露、聯絡人補全與 AI 自動個人化陌生外聯仍屬後續研究／POC，不是現成交付功能。

---

## 二、判定標準

| 判定 | 定義 |
|---|---|
| **吻合** | 前後端流程、資料模型與必要路由已存在，核心使用情境可由現有程式完成。 |
| **大致吻合** | 核心能力存在，但範圍、保證程度、支援類型或 UX 與敘述有重要差異。 |
| **部分吻合** | 只有基礎設施或其中一段流程存在，不能完成敘述中的端到端結果。 |
| **未完成** | 缺少主要資料模型、供應商整合、工作流或使用者入口，不能當成現成功能。 |
| **需設定才可用** | 程式存在，但仍依賴金鑰、外部服務、feature flag、平台 kill switch 或部署環境。 |

「已有程式碼」不等於「已於正式環境啟用」；「模型被提示不要捏造」也不等於可保證零幻覺。

---

## 三、原始產品敘述逐項對照

### P01 — AI 客服依訪客語言回答

**判定：大致吻合，但不可宣稱所有語言完整保證。**

已實作：

- 每則訊息偵測訪客最新提問語言。
- 系統提示要求以最新提問的相同語言完整回答。
- 短型號、數量等中性訊息沿用既有對話語言。
- 日文、德文、韓文、西班牙文、法文與中英文有偵測或固定降級文案。
- 非英文問題可先翻成英文只供知識檢索，原始問題仍交由模型以訪客語言回答。

限制：

- 網站 CMS 公開內容語系只有 `en` 與 `zh-TW/zh-tw`。
- 固定問候與 suggestion chips 主要完整支援繁中、日文與英文。
- 安全／失敗降級完整字典主要為英文、中文、日文、德文、韓文、西班牙文與法文。
- 俄文等其他語言在 LLM 正常時可依提示回答，但固定安全降級可能回英文。
- 語言偵測仍可能對很短、混合語言或專有名詞訊息誤判。

**目前可對外使用的安全說法：**

> AI 會辨識買家提問語言並優先以相同語言回答；主要安全降級語言已本地化，其他語言為模型層最佳努力支援。

**證據：**

- `api/app/core/locale.py`
- `api/app/services/chat_locale.py`
- `api/app/services/chat_service.py`
- `api/tests/test_chat_multilingual.py`

**待討論處置：** 擴增俄文等正式支援語言、或收斂對外承諾範圍。

---

### P02 — AI 吸收網站裡所有資訊

**判定：大致吻合，但「所有資訊」過度宣稱。**

目前會編譯進公開知識索引的 CMS 類型：

- Product
- Product Category
- Application
- Capability
- Certification
- FAQ
- 一般 Page
- 管理者明確允許公開索引的 ContentAsset

刻意不納入或目前未納入：

- 草稿、排程中或已下架內容。
- Privacy、Terms 等法務頁。
- Comparison、CTA、Redirect、後台資料、聯絡人、RFQ 等。
- 未勾選 `is_indexable` 的文件。
- 無法抽出文字且需要 OCR 的文件。

系統會依租戶、visibility、發布狀態與 locale 查詢，避免跨租戶或讀到未發布資料。

**目前可對外使用的安全說法：**

> AI 以網站已發布的產品、應用、產能、認證、FAQ、一般頁面及經核准的公開文件作為知識來源。

**證據：**

- `api/app/services/knowledge_compile.py`
- `api/app/services/knowledge_retrieve.py`
- `api/app/models/knowledge.py`
- `api/tests/test_knowledge_advisor.py`

**待討論處置：** 是否補 Comparison／其他公開內容型別，以及是否需要知識管理專頁。

---

### P03 — 可上傳 PDF 等文件讓 AI 學習

**判定：部分至大致吻合。**

已實作：

- 資產上傳支援 PDF、DOCX、圖片、CSV、XLS/XLSX、STEP/IGES 等檔案。
- 只有 PDF、DOCX 是目前的文字知識索引類型。
- 文件預設不進公開客服，必須由管理者勾選允許公開索引。
- PDF 可保留頁碼並切塊，回答可引用文件來源。
- 檔案有 MIME／signature、大小、配額與 tenant 邊界檢查。

限制：

- 掃描型 PDF 沒有 OCR，會標記 `needs_ocr`。
- DOCX 只抽一般 paragraphs，註解、修訂標記與複雜結構不保證納入。
- XLSX、CSV、CAD 目前只作資產，不作 AI 知識來源。
- 文件 locale 現行編譯預設為英文，尚無完整的文件語系管理介面。

**證據：**

- `api/app/api/v1/endpoints/assets.py`
- `api/app/services/knowledge_extract.py`
- `api/app/services/knowledge_compile.py`
- `admin/src/app/(dashboard)/dashboard/assets/page.tsx`

**待討論處置：** OCR、XLSX/CSV 結構化擷取、文件語系與知識來源管理 UI。

---

### P04 — AI 不會亂講

**判定：已有重要防護，但不能作絕對保證。**

目前防護：

- 僅將 repository 建立的可信來源傳入回答。
- 無公開來源時改為安全拒答。
- 認證／合規問題缺正式認證來源時拒絕推定。
- 回覆中的未支持數字規格會被 deterministic policy 擋下。
- Prompt injection 模式會被阻擋。
- 回覆附買家可開啟的公開來源連結。
- 下架／刪除來源會 tombstone 並移除 live chunks。

剩餘風險：

- 目前沒有逐句 claim-to-evidence entailment 驗證。
- 一般非數字敘述只要同時存在可信來源，仍可能出現來源未直接支持的文字。
- 價格與交期相關詞目前會產生 warning，但不是所有情況都必然阻擋。
- LLM、檢索與語言偵測都不是數學上的零錯誤系統。

**目前可對外使用的安全說法：**

> 回答以已發布資料接地、附來源，遇到缺資料、數字規格或認證風險時會拒絕推測並引導詢價。

**不可使用：**「絕對不會亂講」「零幻覺」。

**證據：**

- `api/app/services/chat_grounding.py`
- `api/app/services/knowledge_text.py`
- `api/tests/test_knowledge_advisor.py`
- `api/tests/test_round3_closeout.py`

**待討論處置：** 是否建立 claim verifier、grounded accuracy eval 與正式驗收門檻。

---

### P05 — AI 不做無方向閒聊，會導回選品與詢價

**判定：吻合。**

已實作：

- 對話角色明確限定為 B2B manufacturer AI Product Advisor。
- 以產品、規格、認證、OEM、MOQ 與 RFQ 流程為核心。
- 商業需求缺口依序追問 program type、quantity/MOQ、use case、spec、lead time、packaging、market/compliance。
- 每輪最多產生一個高價值 clarifying question。
- 購買意圖成熟時產生 `suggested_action=rfq`。
- 建立短效、tenant-scoped、visitor-bound RFQ draft 與預填連結。
- `chat_start`、`chat_rfq_handoff` 回寫 tracking 與 intent score。

限制：

- 沒有明確的全類型 off-topic classifier；主要依 system prompt、對話政策及來源不足降級控制。
- 正式 RFQ 仍需買家確認與提交，不會由 AI 未經同意直接建立。

**證據：**

- `api/app/services/chat_policy.py`
- `api/app/services/chat_service.py`
- `api/app/models/rfq_draft.py`
- `api/app/api/v1/endpoints/chat.py`

**待討論處置：** 是否增加 off-topic taxonomy、真人接手狀態與對話成效 KPI。

---

### P06 — 維護一個語系後自動連動所有語言

**判定：部分吻合，原敘述明顯超過現況。**

現況：

- CMS 只支援英文與繁中。
- Tenant 可設定來源語系；另一語系視為 buyer locale。
- 管理者可對單筆 Product、Category、Page、Application、FAQ、Certification、Capability、Comparison 觸發 AI locale draft。
- 型號、規格、圖片、數字、單位、URL 與特定 FK 會複製或 remap，不交給 AI 任意改寫。
- AI 只建立 `draft`，不會自動發布。
- 已發布 buyer-locale 內容不會被新草稿覆寫。
- 來源內容後來更新時，既有已發布譯文只會標記 stale／需更新。
- 後台有 locale coverage、missing、draft、stale 報表與篩選。

尚未做到：

- 修改來源內容後自動產生所有語言的新版本。
- 一次維護任意多國語言。
- 自動審核與自動發布。
- 多語差異檢視、翻譯記憶與大規模批次工作流。

**目前可對外使用的安全說法：**

> 只需維護來源語系，系統可為英文／繁中產生保留規格與型號的買方語系草稿，並提示缺漏或過期內容；人工確認後再發布。

**證據：**

- `api/app/core/locale.py`
- `api/app/services/translation_draft.py`
- `api/app/services/locale_support.py`
- `api/app/api/v1/endpoints/locale_draft.py`
- `api/app/api/v1/endpoints/locale_quality.py`
- `admin/src/lib/i18n.ts`
- `api/tests/test_locale_draft.py`

**待討論處置：** 擴增語言、事件驅動自動起草、批次草稿或維持人工觸發的治理模式。

---

### P07 — 記錄訪客頁面、動作並依權重辨識價值

**判定：吻合，且實作比原敘述更完整。**

已實作：

- 第一方 visitor cookie 與 sessionStorage session。
- Analytics consent 未同意時不送詳細追蹤事件。
- Page、Category、Product、Application、FAQ、Comparison、Spec download、Certification、CTA、Form、RFQ、Chat 等事件。
- 前端離線佇列與恢復連線後批次送出。
- 可選 GA4 平行事件映射。
- 不同行為有預設權重，也可由租戶調整規則。
- Cold、Warm、Hot、Sales-ready 階段。
- 四個採購 facet：產品興趣、信任驗證、採購準備度、急迫性。
- 「為何 Hot」文字解釋。
- 可選 ML intent score。
- Hot／Sales-ready 通知。

限制：

- 使用者拒絕 analytics consent 時，不會形成敘述中的完整旅程。
- visitor_id 是瀏覽器第一方識別，不等於自然人或企業身分。
- 跨瀏覽器、清除 cookie、不同裝置與某些網路情境無法自然合併。

**證據：**

- `web/src/lib/analytics.ts`
- `web/src/components/tracking/PageViewTracker.tsx`
- `web/src/components/tracking/AnalyticsConsent.tsx`
- `api/app/api/v1/endpoints/events.py`
- `api/app/services/intent_scoring.py`
- `api/app/services/intent_facets.py`
- `api/app/services/ml_intent.py`

**待討論處置：** 對外敘述需加入「經同意的第一方行為」及匿名身分邊界。

---

### P08 — 後台顯示完整顧客旅程

**判定：吻合。**

Journey API 會整合：

- Visitor profile 與 intent facets。
- Tracking events。
- Chat sessions 與訊息摘要。
- RFQ 紀錄與提交時 intent score。
- 已知 Contact 連結。

已知聯絡人是在 Contact Form／RFQ 或既有資料來源產生後，透過 visitor_id 和匿名旅程連接；沒有留資前仍是匿名 visitor。

**證據：**

- `api/app/api/v1/endpoints/visitors.py`
- `admin/src/app/(dashboard)/dashboard/visitors/[id]/page.tsx`
- `api/app/models/visitor.py`
- `api/app/models/contact.py`

**待討論處置：** 旅程 UX、關鍵節點摘要及隱私揭露文字。

---

### P09 — 透過 IP 反查訪客公司

**判定：未完成，不可列為現成功能。**

目前只有：

- `resolve_ip_to_company()` 基礎函式，呼叫 ip-api.com 查 country、city、org。
- 此函式沒有接入 tracking event 或 visitor 建檔流程。
- 目前沒有正式的 company identification endpoint 或後台 UI。

缺少：

- NetworkObservation。
- CompanyIdentification。
- Provider Adapter。
- Business／ISP／VPN／hosting 分類。
- Confidence、evidence、TTL、review、rejection 與 audit trail。
- PDL、Albacross、Snitcher、IPinfo 等正式供應商整合與 SaaS 展示授權。
- 多租戶用量、成本與 quota 管理。

重要觀念修正：

- 並非每家公司都有固定且唯一的對外 IP。
- ISP `org`、ASN 或 network owner 不能直接等同進站公司。
- VPN、共享 NAT、雲端出口、行動網路、代理與共享辦公室會造成誤判。
- 即使高信心辨識公司，也不能宣稱辨識到哪一位自然人。

現有公司辨識計畫明確將此模組定義為研究／POC／受控測試，並將資料模型及正式 Adapter 列為未完成工作。

**不可使用：**「每家公司 IP 都固定」「可知道是哪家公司／哪個人來看過」「100% 辨識」。

**證據：**

- `api/app/services/ip_resolver.py`
- `FORGEBASE_COMPANY_IDENTIFICATION_AND_CONTACT_ENRICHMENT_PLAN_2026-08-16.md`
- `api/app/models/` 中不存在 NetworkObservation、CompanyIdentification、ContactCandidate。

**待討論處置：** 取消此承諾、維持 roadmap，或依既有計畫進入供應商 Shadow Mode。

---

### P10 — 自動找出公司公開聯絡方法

**判定：未完成。**

目前 `Contact` 的來源為：

- Contact form。
- RFQ form。
- 人工或既有整合匯入／同步。

不存在：

- 依推測公司自動找相關聯絡人。
- 職能、職級、地區 relevance score。
- Hunter／PDL person search。
- Business Email verification。
- ContactCandidate 接受／拒絕／過期工作流。
- 「聯絡人是公司相關窗口、但不是進站本人」的正式資料模型與 UI。

**待討論處置：** 必須與 P09 一起決策，不能獨立宣稱已完成。

---

### P11 — AI 鎖定高潛客並自動寄個人化開發信

**判定：只有已知聯絡人培育基礎，原敘述的陌生外聯未完成。**

現有能力：

- Nurture Sequence 與多步驟 Step。
- Intent stage、Segment 或 Manual trigger。
- 只有已存在的 Contact 才能 enroll。
- Sequence 必須由管理者核准。
- 到期信件只會排入 `NurtureOutbox`。
- 每封信仍需管理者按「確認寄出」。
- 後台 AI 可建立一次性 follow-up email，但同樣只排入人工核准 outbox。
- 具寄送 idempotency、dry-run、外部寄送 kill switch 與 suppression 檢查。

尚未做到：

- 從匿名高意圖 visitor 找出可寄送的公司或聯絡人。
- 依完整 journey 自動選出感興趣產品並寫入信件。
- AI 動態產生每封培育信內容。
- 無人核准的全自動外部寄送。
- Cold outreach 的合法性、退訂與區域規則決策。

現行 Step 直接使用管理者預先建立的 `subject`、`html_body`、`text_body`，不是 journey-personalized AI content。

**目前可對外使用的安全說法：**

> 已知聯絡人可依意圖階段或分眾加入核准制培育流程；到期信件進入待寄佇列，由管理者確認後寄出。

**證據：**

- `api/app/models/nurture.py`
- `api/app/api/v1/endpoints/nurture.py`
- `api/app/services/email_service.py`
- `api/app/services/email_governance.py`
- `api/app/services/copilot/action_tools.py`
- `admin/src/app/(dashboard)/dashboard/nurture/outbox/page.tsx`

**待討論處置：** 保留雙重人工核准、改為 sequence-level 核准後自動寄，或另建受控 AI personalization。

---

### P12 — 客戶回信後自動成為高價值名單

**判定：未完成。**

現有 Resend webhook 可處理事件、去重、退信、申訴及 suppression，但沒有：

- Inbound Email 接收。
- Reply event 與原寄件／Contact／Visitor 關聯。
- AI 回覆意圖分類。
- 自動建立或升級 Lead／RFQ。
- 指派真人業務接手的 reply workflow。

**證據：**

- `api/app/api/v1/endpoints/webhooks.py`
- `api/app/models/email_delivery.py`
- `api/app/services/resend_webhook.py`

**待討論處置：** 是否要做 inbound reply，或改成依 ESP／CRM 外部系統完成。

---

### P13 — 後台 AI 可回答管理者對目前狀況的問題

**判定：吻合，但定位是 Sales Ops AI，不是完整系統說明客服。**

可查詢：

- Dashboard KPI。
- RFQ 列表與明細。
- Hot visitors 與 visitor profile。
- 逾期 RFQ。
- Contact 搜尋與 profile。
- Product interest 與 funnel。
- Company profile 與產品搜尋。

可執行的受控動作：

- 更新 RFQ status。
- 記錄首次回應。
- 指派 RFQ 給自己。
- 建立跟進提醒。
- 建立待人工核准的 follow-up email。

UX 現況：

- `/dashboard/copilot` 有獨立 AI 行銷助理頁面。
- `CopilotFloatingWidget` 元件已存在。
- 全專案沒有任何其他檔案 import／掛載該 widget；Dashboard layout 現在不會顯示右下角浮動 AI。
- `/dashboard/support` 是 mailto 支援表單，不是 AI 操作說明知識庫。

**目前可對外使用的安全說法：**

> 後台 AI 行銷助理可依租戶即時 CRM、RFQ、訪客與漏斗資料回答營運問題，並協助建立受控的業務動作。

**證據：**

- `api/app/services/copilot/chat_engine.py`
- `api/app/services/copilot/tools.py`
- `api/app/services/copilot/action_tools.py`
- `api/app/api/v1/endpoints/copilot.py`
- `admin/src/app/(dashboard)/dashboard/copilot/page.tsx`
- `admin/src/components/copilot/CopilotFloatingWidget.tsx`
- `admin/src/components/layout/DashboardShell.tsx`

**待討論處置：** 掛載浮動 widget、建立系統操作知識庫，或維持 Sales Ops 專屬定位。

---

## 四、原始敘述未提到、但系統已有的功能

### A. RFQ 業務工作台

- 結構化 RFQ 與貿易欄位。
- RFQ quality score 與理由。
- AI RFQ 分析與專業回信草稿。
- Status、assignee、follow-up、notes、spam、merge、CSV export。
- Reply checklist、Quote Readiness、建議反問與回覆範本。
- RFQ lifecycle event timeline。
- 可選 AgentOS 分析／草稿／核准工作流。

### B. SLA、成交與成效閉環

- 依買家國家時區計算 SLA。
- 即將逾期與已逾期掃描、提醒與升級。
- `new → assigned → in_progress → quoted → negotiation → won/lost/expired`。
- Won／Lost 必填原因；Won 可記錄成交金額與幣別。
- Outcomes dashboard、七層 funnel、內容成交歸因與 intent outcome feedback。
- 今日任務佇列與內容成效頁。

### C. 訪客分眾與 CTA

- 條件式 Segment CRUD 與即時計算。
- Segment 同步 Mailchimp／SendGrid。
- 依 intent stage 與 facet 切換 Dynamic CTA。
- AI 單訪客 CTA 建議。
- 可選 ML intent train／score／batch score。

### D. CMS 與 B2B 信任內容

- Product、Category、Page、Application、FAQ、Certification、Capability、Comparison、CTA。
- Product gallery、R2／本地資產、圖片壓縮、ALT 與 SEO metadata。
- Product ↔ Application、Certification、FAQ、替代品等內容關聯。
- AI／行為共現關聯推薦。
- Draft、Publish、Unpublish、Scheduled Publish。
- JWT preview token。
- 發布後 Next.js revalidation。

### E. SEO 基礎設施

- Canonical。
- Hreflang 與 x-default。
- Sitemap。
- JSON-LD／structured data。
- SEO Redirect CRUD 與 public resolve。
- 搜尋／分頁頁面的 noindex 與 canonical 控制。

### F. 通知與每日營運摘要

- New RFQ、Hot visitor、Chat handoff、SLA、Churn risk 等事件。
- Telegram／LINE／Email channel。
- Quiet hours、偏好、去重與通知 log。
- 每日 KPI digest 與行動建議。

### G. 多租戶 SaaS 與平台營運

- Tenant-scoped 內容、Chat、Tracking、Contact、RFQ 與 AI context。
- Starter／Professional plan 與 feature entitlements。
- 產品及資產配額。
- Platform admin 跨租戶 dashboard、workspace、delivery board、RFQ、tenant、users、health、resources、usage、audit。
- Site template、tenant provisioning、site build validation／publish。

### H. 隱私、安全與營運可靠性

- Analytics consent／revoke 與 consent audit。
- Anonymous tracking retention cleanup。
- Form challenge、honeypot 與可選 Cloudflare Turnstile。
- API rate limits、tenant daily chat budget 與 message limit。
- Email external-delivery kill switch。
- Bounce／complaint suppression。
- Operational outbox、retry、idempotency。
- 健康檢查、外部監控、備份／還原與部署腳本。

---

## 五、目前本機啟用狀態快照

以下只代表 2026-08-26 本工作目錄的 `api/.env`，不代表其他正式部署環境；檢查過程沒有記錄或輸出任何 secret 值。

| 能力 | 本機設定狀態 | 影響 |
|---|---|---|
| Database URL | 已設定於 `api/.env` | 測試程序未把它匯出為 OS `DATABASE_URL`，因此 DB integration tests 仍跳過。 |
| OpenAI API key | 已設定 | AI 程式具備呼叫條件；實際可用性仍取決於模型、額度與網路。 |
| R2 | 未設定 | 資產會使用本機 storage fallback，不是 Cloudflare R2。 |
| Resend／SendGrid | 未設定 | 無法實際寄送外部 Email。 |
| External Email kill switch | 未明確開啟，程式預設為 false | 外部收件人寄送會被平台政策阻擋。 |
| Telegram | 未設定 | Telegram 通知不會送出。 |
| LINE | 未設定 | LINE 通知不會送出。 |
| IP enrichment key | 未設定 | ip-api 函式只可能走開發 fallback，且正式流程本來就未接入。 |

程式存在但外部服務未設定時，不應在本機展示中宣稱已可實際送信、發通知、存 R2 或辨識公司。

---

## 六、驗證結果

### 本輪重新驗證

2026-08-26 執行：

```text
pytest:
53 passed, 3 skipped, 3 warnings

web TypeScript:
tsc --noEmit passed

admin TypeScript:
tsc --noEmit passed
```

涵蓋：

- Chat multilingual。
- Knowledge advisor／grounding。
- Email delivery safety。
- Intent facets。
- Web 與 Admin TypeScript。

### 前一輪全 API 測試結果

```text
226 tests collected
156 passed
70 skipped
19 warnings
```

70 個主要因測試程序沒有 OS-level `DATABASE_URL` 而跳過，包含 PostgreSQL integration／tenant isolation／部分端到端流程。因此本文件可證明「程式與單元行為存在」，不能單憑本機結果宣稱所有資料庫端到端流程已正式驗收。

目前 warnings 包含：

- `datetime.utcnow()` deprecation。
- SQLModel 建議使用 `session.exec()` 的 deprecation。
- 少量 async connection cancel coroutine resource warning。

---

## 七、對外產品宣稱紅線

在補實作與正式驗收前，不應使用：

- 「支援所有國家／所有語言且保證同語回答」。
- 「AI 已學會網站裡所有資料」。
- 「AI 絕對不會亂講／零幻覺」。
- 「只改一個語言，所有語言立即自動同步並上線」。
- 「每家公司都有固定 IP」。
- 「能知道是哪家公司或哪個人來看過哪些頁面」。
- 「自動找到匿名訪客聯絡方式」。
- 「AI 會自動寄出依旅程個人化的陌生開發信」。
- 「客戶一回信就會自動成為可交給業務的 Lead」。
- 「後台每一頁右下角都有 AI 助理」。

---

## 八、建議後續逐項討論順序

| 順序 | 議題 | 核心決策 | 初步優先級 |
|---:|---|---|---|
| 1 | P09 公司辨識 | 取消現承諾、列 roadmap，或正式啟動 Shadow Mode | P0 |
| 2 | P10 聯絡人補全 | 是否納入產品；資料授權、成本、隱私及非本人語意 | P0 |
| 3 | P11 自動個人化寄信 | 維持人工核准、降低核准層級，或建立受控 AI personalization | P0 |
| 4 | P12 Inbound reply | ForgeBase 自建，或交由 ESP／CRM | P1 |
| 5 | P06 多語內容 | 維持英／中，或擴語言與事件驅動批次草稿 | P1 |
| 6 | P01 對話語言 | 正式支援語言清單與俄文等 safety copy | P1 |
| 7 | P04 AI 可信度 | Claim verifier、eval dataset 與正式 SLA | P1 |
| 8 | P13 後台 AI | 掛載浮動 widget、增加系統說明知識，或維持 Sales Ops | P2 |
| 9 | P02/P03 知識庫 | OCR、Comparison、XLSX／CSV、知識管理 UI | P2 |
| 10 | 對外文案 | 依最終決策重寫官網、簡報、Demo script 與銷售話術 | P0，需隨前述決策同步 |

---

## 九、決策紀錄模板

後續每一項討論完成後，在本節新增紀錄：

```markdown
### DEC-XXX — 議題名稱

- 日期：YYYY-MM-DD
- 對應項目：PXX
- 決策：保留／修正文案／補實作／延後／移除
- 產品範圍：
- 對外文案：
- 工程範圍：
- 隱私／法務條件：
- 驗收標準：
- 負責人：
- 目標版本／日期：
- 狀態：待辦／進行中／已完成／已取消
```

目前尚無已定案的處置決策；本文件只記錄第二輪稽核事實與建議討論順序。

---

## 十、主要程式證據索引

| 主題 | 主要檔案 |
|---|---|
| Chat 語言與政策 | `api/app/core/locale.py`、`api/app/services/chat_locale.py`、`api/app/services/chat_policy.py` |
| 前台 AI 顧問 | `api/app/services/chat_service.py`、`api/app/api/v1/endpoints/chat.py` |
| Grounding | `api/app/services/chat_grounding.py` |
| Knowledge index | `api/app/models/knowledge.py`、`api/app/services/knowledge_compile.py`、`api/app/services/knowledge_retrieve.py` |
| 文件抽取 | `api/app/services/knowledge_extract.py`、`api/app/api/v1/endpoints/assets.py` |
| 多語草稿 | `api/app/services/translation_draft.py`、`api/app/services/locale_support.py`、`api/app/api/v1/endpoints/locale_draft.py` |
| Tracking／Intent | `web/src/lib/analytics.ts`、`api/app/api/v1/endpoints/events.py`、`api/app/services/intent_scoring.py`、`api/app/services/intent_facets.py` |
| Journey | `api/app/api/v1/endpoints/visitors.py` |
| 公司辨識現況 | `api/app/services/ip_resolver.py`、`FORGEBASE_COMPANY_IDENTIFICATION_AND_CONTACT_ENRICHMENT_PLAN_2026-08-16.md` |
| Nurture／Email | `api/app/models/nurture.py`、`api/app/api/v1/endpoints/nurture.py`、`api/app/services/email_service.py`、`api/app/services/email_governance.py` |
| Email webhook | `api/app/api/v1/endpoints/webhooks.py`、`api/app/models/email_delivery.py` |
| 後台 AI | `api/app/services/copilot/`、`api/app/api/v1/endpoints/copilot.py`、`admin/src/app/(dashboard)/dashboard/copilot/page.tsx` |
| RFQ／SLA／Outcomes | `api/app/api/v1/endpoints/rfqs.py`、`api/app/services/sla.py`、`api/app/api/v1/endpoints/growth_ops.py` |
| SaaS／平台營運 | `api/app/services/subscription.py`、`api/app/api/v1/endpoints/platform_admin.py` |
| 隱私與防濫用 | `api/app/api/v1/endpoints/privacy.py`、`api/app/services/privacy_retention.py`、`api/app/services/form_challenge.py` |
