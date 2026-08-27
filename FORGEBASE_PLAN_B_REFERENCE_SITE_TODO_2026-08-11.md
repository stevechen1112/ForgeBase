# ForgeBase 方案 B：NorthForge 公開 Reference Site TODO 盤點

文件日期：2026-08-11\
文件狀態：待執行\
決策：採用「透明 Reference Site＋真實公開流量＋真實需求提交＋零對外銷售回覆」\
適用範圍：NorthForge Tools 前台、ForgeBase Admin／API、追蹤分析、AI 客服、RFQ／Contact、通知與案例報告

---

## 1. 執行結論

NorthForge 可以公開、可做 SEO、可導入真實流量、可收集真實行為，也可讓訪客提交真實採購需求；但網站必須明確表示它是 **ForgeBase 營運的工業採購 Reference Project**，不是實際手工具製造商、供應商或報價方。

這次改造的成功條件不是讓網站「看起來像假網站」，而是讓它同時做到：

1. 產品目錄、視覺、內容深度與操作流程具有商業網站的完整度。
2. 不捏造可影響交易判斷的法人、工廠、產能、客戶、認證、供貨及回覆承諾。
3. 曝光、訪客、工作階段、事件與需求提交全部來自真實公開流量。
4. 訪客在提交前知道資料由誰收集、用途是什麼，以及不會收到報價或業務回覆。
5. 系統完整測試收件、分流、狀態、內部草稿、分析與稽核，但不發送任何對外訊息。
6. 對外案例只陳述可驗證的真實結果，不把需求提交包裝成合格商機、正式 RFQ 或營收。

### 建議公開定位

> **NorthForge Tools — a ForgeBase-operated industrial sourcing reference project**

建議中文：

> **NorthForge Tools — 由 ForgeBase 營運的工業採購參考專案**

建議表單核心揭露：

> This reference project does not sell tools or issue quotations. Your submission will be used by ForgeBase to evaluate B2B sourcing workflows and platform performance. No sales response will be sent.

建議中文：

> 本參考專案不販售工具，也不提供報價。您提交的內容將由 ForgeBase 用於評估 B2B 採購流程與平台成效，且不會收到業務回覆。

---

## 2. 不可變更的專案原則

以下是方案 B 的硬性邊界；任一項不成立，就不能公開收集資料。

- [ ] **B-01 真實營運主體**：Privacy、Terms、表單與聯絡資訊使用真實且可追溯的 ForgeBase 資料控制者名稱、地址或依法必要資訊、聯絡信箱。
- [ ] **B-02 身分透明**：NorthForge 不自稱為已登記法人、實際工廠、賣方、出口商或證書持有人。
- [ ] **B-03 交易透明**：所有會收集資料的 CTA 與表單，在提交前清楚標示「不販售、不報價、不回覆」。
- [ ] **B-04 真實數據**：公開測試資料只來自真實流量；不得執行訪客、事件、Contact 或 RFQ 的模擬注入。
- [ ] **B-05 零外寄**：Auto-reply、nurture、業務通知後的人工回信、AI 自動寄信、AgentOS send-reply、行銷郵件與簡訊全部關閉或技術性阻斷。
- [ ] **B-06 不誤報成果**：公開報告使用 `requirement_submission`／「需求提交」，不得稱為 qualified lead、正式 RFQ、quote、opportunity、won 或 revenue。
- [ ] **B-07 不偽造信任證據**：不得公開虛構證書、證書編號、核發機構、工廠地址、客戶 Logo、成交案例、測試報告或出貨紀錄。
- [ ] **B-08 可撤回與刪除**：資料主體有可用的查詢、更正、刪除或撤回管道，且後台能完成處理並留下稽核紀錄。
- [ ] **B-09 安全底線**：公開收件前先完成既有全面稽核中的多租戶隔離、XSS／上傳、濫用防護及背景工作 P0。
- [ ] **B-10 禁用兩項產品能力**：不恢復 Legacy Site Intake，也不恢復 AI 產生／翻譯網站內容。

---

## 3. 現況盤點與需處理的主要來源

目前 NorthForge 已具備完整目錄與內容深度，可保留其資訊架構與產品研究價值；但以下來源仍以「真實製造商」敘事呈現，必須同步改造，不能只修改首頁或頁尾。

| 區域 | 現況 | 方案 B 處理方式 |
|---|---|---|
| 品牌與內容藍圖 | 明確定義為虛構台灣製造商，並以「可被誤認為真實」為建構目標 | 改成透明的 Reference Project 內容契約 |
| 公司故事 | 含 2001 創立、人物、發展歷史、出口區域等虛構事實 | 刪除，或改為「此參考情境所模擬的買方問題」 |
| 工廠與能力 | 含製造、品管、包裝、產能、文件與出口執行承諾 | 改為「參考工作流程／買方評估項目」，不得宣稱 NorthForge 擁有 |
| 認證 | ISO 9001、VDE、GS／TÜV、RoHS、REACH 與證書頁 | 移除證書及 holder claim；改成「買方常見標準／文件需求」 |
| 產品與規格 | 32 個產品及完整參考規格 | 可保留，但標示 illustrative／reference specification、非報價與非供貨承諾 |
| 圖片 | AI 生成的工廠、產品與能力情境圖 | 保留前先標示 illustrative；不得暗示是 NorthForge 自有廠房、實物或出貨品 |
| CTA／RFQ | 多處 Request a Quote，並承諾 1 business day、24–48h 回覆 | 改為 Submit a Sourcing Requirement；明示不報價、不回覆 |
| Contact／Legal | 使用 NorthForge 與虛構 sales 信箱，Privacy 用途含 sales follow-up | 改為真實 ForgeBase 控制者、研究／產品評估用途與真實資料權利管道 |
| Nurture／Auto-reply | 種子資料含多封銷售信、價格、案例、Sales Team 寄件人 | 不匯入，清除既有資料，並加 tenant 級 outbound kill switch |
| AI 客服 | 可能將 RFQ 建議自動計為 handoff／商機，且可能通知業務 | 改成 Reference Assistant；只引導需求提交，不承諾供貨、認證、價格或回覆 |
| 分析與案例 | 既有模型使用 lead、RFQ、qualified、quoted、won funnel | 為 Reference Site 建立獨立事件與報表語意，不得沿用交易漏斗名稱 |
| 模擬資料工具 | 可注入訪客、session、Contact 與 RFQ | 生產環境禁止執行；不刪工具，但加入環境護欄與文件警示 |

主要現有來源：

- `demo/handtool-company/README.md`
- `demo/handtool-company/09-demo-methodology.md`
- `demo/handtool-company/content/*.md`
- `demo/handtool-company/seed/*.json`
- `demo/handtool-company/seed/seed_demo_briefs_ctas_nurture.py`
- `demo/handtool-company/seed/seed_demo_visitors.py`
- `scripts/demo_seed_and_verify.py`
- `web/messages/en.json`
- `web/messages/zh-TW.json`
- `web/src/components/forms/RFQForm.tsx`
- `web/src/components/forms/ContactForm.tsx`
- `web/src/components/chat/ChatWidget.tsx`
- `web/src/lib/siteConfig.ts`
- `api/app/services/rfq_auto_reply.py`
- `api/app/api/v1/endpoints/nurture.py`

---

## 4. 優先級與狀態定義

- **P0**：公開收集真實流量或資料前必須完成。
- **P1**：公開測試前應完成；若延後，會破壞數據可信度或案例品質。
- **P2**：開始累積資料後完成，用來提高實驗效率與案例說服力。
- **狀態**：`[ ]` 未開始、`[-]` 進行中、`[x]` 完成、`[!]` 阻塞。

建議每個 TODO 完成時附上：PR／commit、測試證據、畫面截圖、設定匯出與驗收人。

---

# 5. P0 — 公開前必須完成

## P0-A. 定位、治理與真實營運主體

- [ ] **A-01 指定真實資料控制者**\
  Owner：產品負責人＋法務\
  產出：真實名稱、聯絡地址／必要登記資訊、privacy 聯絡信箱、資料權利處理人。不得使用 NorthForge 虛構資料替代。

- [ ] **A-02 核准 Reference Site 一句話定位**\
  Owner：產品負責人\
  產出：英文與繁中正式版本，供 Hero、About、Footer、Legal、表單與 AI 客服共用。

- [ ] **A-03 建立 Claim Policy**\
  Owner：產品＋內容＋法務\
  至少分類：`verified_fact`、`reference_specification`、`illustrative_workflow`、`prohibited_claim`。每筆內容要能標示類型與驗證來源。

- [ ] **A-04 建立公開內容核准責任**\
  Owner：產品負責人\
  規則：新增或修改公司、工廠、標準、規格、安全、法規、價格、MOQ、交期相關內容時，必須經人工審核，不使用 AI 生成網站內容。

- [ ] **A-05 建立「零對外回覆」書面政策**\
  Owner：產品＋營運\
  說明允許的內部動作、禁止的外部動作、例外處理、資料權利請求與資安事件通知；資料權利／安全通知不屬於銷售回覆，仍須依法處理。

- [ ] **A-06 完成目標市場法務檢核**\
  Owner：合格法律顧問\
  至少檢核台灣個資與公平交易規範；若接受歐盟／英國／美國等地流量，再依實際 targeting 與資料處理範圍檢核。此文件不是法律意見。

### A 組驗收

- [ ] 任一頁都不會讓合理訪客以為 NorthForge 是已存在的法人、工廠或可簽約供應商。
- [ ] 真實控制者資料已由負責人與法務簽核，且可實際收到資料權利請求。
- [ ] Claim Policy 已可供內容 QA 與自動掃描使用。

## P0-B. 全站虛構主張清查與重寫

- [ ] **B-01 重寫 Demo README 與方法論**\
  檔案：`demo/handtool-company/README.md`、`demo/handtool-company/09-demo-methodology.md`\
  移除「讓買方誤認為真實」的建構目標，改為「商業深度高、身份與用途透明」。

- [ ] **B-02 重寫公司藍圖與 Corporate Profile**\
  檔案：`content/01-company-blueprint.md`、`content/04-corporate-profile.md`\
  移除虛構法人、人物、創立年份、歷史、廠址、員工／產線、出口國家與營運承諾。

- [ ] **B-03 重寫首頁與 About 來源**\
  檔案：`content/07-homepage-source.md`、`content/08-about-source.md`、`seed/pages.json`、`web/messages/*.json`\
  將 manufacturer／supplier／our factory／we manufacture 等主張改成 reference catalog／buyer workflow／illustrative program。

- [ ] **B-04 建立逐項 Claims Register**\
  盤點全站文字、JSON、SEO metadata、structured data、alt text、PDF、圖片 prompt 與後台種子資料。欄位至少含：claim、位置、類型、風險、證據、處置、審核人、日期。

- [ ] **B-05 移除或重構 Certifications**\
  檔案：`seed/certifications.json`、certification pages、產品關聯與首頁 badges。\
  不顯示任何假證書或過期／不存在證書；可改成「Standards Buyers Commonly Request」，並明示不是 NorthForge certification。

- [ ] **B-06 重構 Capabilities**\
  將「NorthForge 擁有的工廠能力」改為「ForgeBase 可呈現的供應商能力資料模型」或「買方常見評估流程」，不得暗示實際生產。

- [ ] **B-07 重構產品資料契約**\
  32 個產品可保留作 reference catalog，但每個產品頁需顯示：參考型號、參考規格、非可供貨商品、非安全／合規保證、無報價。

- [ ] **B-08 清查 FAQ、比較頁與應用頁**\
  移除或改寫 MOQ、lead time、sample、shipping、capacity、certification、warranty、客戶市場、實際製造與交付承諾。

- [ ] **B-09 清查新聞、職缺、Dealer Locator 與 Contact**\
  移除虛構擴產、產品線發布、招募、經銷商、合作夥伴、團隊和區域分流資訊；不保留會造成「公司正在營運」的假證據。

- [ ] **B-10 重製 SEO metadata 與 schema.org**\
  不使用 `Organization`／`Manufacturer`／`LocalBusiness` 的虛構地址、創立年、聯絡人或認證；採真實 ForgeBase 組織資料與清楚的 reference-project 說明。

- [ ] **B-11 圖片語意與標示清查**\
  工廠與生產圖改為 illustrative scene，不使用「our factory」alt／caption；產品圖標示為 reference rendering，並確認無第三方標誌、證書章或可能混淆的安全標章。

- [ ] **B-12 移除虛構聯絡方式**\
  清除 `sales@northforgetools.com`、假電話、假地址與虛構人名；只保留真實 ForgeBase privacy／project 聯絡管道，且不得暗示提供銷售報價。

### B 組驗收

- [ ] 對 repo、CMS 匯出與已發布資料執行 claim 掃描，`manufacturer`、`factory`、`ISO 9001 certified`、`VDE certified`、假地址／人物／信箱等禁止語句為 0，合法的教育性內容需列白名單並人工抽查。
- [ ] 英文與繁中首頁、產品、About、Capabilities、Standards、FAQ、Contact、Legal 與 sitemap 隨機抽查無矛盾。
- [ ] 搜尋引擎結果標題與描述不再宣稱 NorthForge 是台灣 OEM 製造商。

## P0-C. CTA、Contact 與 Requirement Submission

- [ ] **C-01 建立新的轉換命名**\
  主 CTA 建議：`Submit a Sourcing Requirement`／「提交採購需求」。\
  次 CTA 可使用：`Explore Reference Products`、`Test the Requirement Workflow`。\
  禁用：`Request a Quote`、`Get Pricing`、`Talk to Sales`、`Request Sample`。

- [ ] **C-02 全站替換 CTA**\
  範圍：Header、Hero、Footer、產品卡、產品詳情、應用、能力、比較、AI 客服、sticky CTA、404、下載門檻與動態 CTA。

- [ ] **C-03 重命名公開 RFQ 頁**\
  UI／SEO／breadcrumb 改為 Sourcing Requirement；API／資料表可暫時保留內部 `rfq` 技術名稱，但管理後台必須顯示 Reference 標籤，避免營運誤讀。

- [ ] **C-04 在表單上方加入明顯揭露**\
  在使用者輸入個資前可見，不放在摺疊區或僅靠頁尾；說明非賣方、無報價、無銷售回覆、資料用途與控制者。

- [ ] **C-05 在 Submit 按鈕旁加入短版揭露**\
  不以預勾選同意取代通知；Privacy Policy 必須是可操作連結。

- [ ] **C-06 重寫成功頁／成功訊息**\
  移除「1 business day」與「24–48h」回覆承諾。改為：已收到需求、僅供研究／平台驗證、不會收到報價或業務回覆、可要求刪除。

- [ ] **C-07 重寫 Contact 流程**\
  一般產品詢問不應假裝導向 NorthForge 團隊。產品研究需求可進相同 requirement workflow；privacy／平台問題則導向真實 ForgeBase 聯絡窗口。

- [ ] **C-08 資料最小化**\
  重新判定 full name、company、email、phone、country、預算、規格、附件是否必要。可選欄位應清楚標示，非必要不得強制蒐集。

- [ ] **C-09 敏感資訊警示**\
  表單與 AI 客服提醒勿提交機密設計、營業秘密、付款資料、身分證明、受出口管制資料或不必要個資。

- [ ] **C-10 Spam／濫用防護**\
  加入 honeypot、rate limit、風險式 CAPTCHA、附件限制、server-side schema validation 與重複提交 idempotency；不得用暗藏追蹤繞過同意。

- [ ] **C-11 附件策略**\
  若現階段無安全掃描、保存政策與權限隔離，公開測試先關閉附件；否則完成 MIME sniffing、惡意檔掃描、隔離儲存、到期刪除與下載稽核。

- [ ] **C-12 表單端到端驗收**\
  測試英文／繁中、桌機／手機、成功、驗證錯誤、timeout、重複送件、bot、停用 JS、API error、刪除請求與 accessibility。

### C 組驗收

- [ ] 訪客在首次輸入個資前與按下提交前，都能理解這不是報價管道且不會收到業務回覆。
- [ ] 全站不存在對外的 quote／sample／sales-response 承諾。
- [ ] 成功提交只建立一筆需求與可追溯事件，不重複通知或重複計數。

## P0-D. Privacy、Cookie 與資料治理

- [ ] **D-01 重寫 Privacy Policy**\
  至少包含：真實控制者、蒐集目的、資料類別、法源／依據、使用方式、處理者、跨境、保存期間、權利、申訴／聯絡管道、安全原則與政策版本。

- [ ] **D-02 移除不實隱私承諾**\
  現有「We will never share your data with third parties」與實際 analytics、hosting、email、LLM、CRM 等處理者可能矛盾；改成準確揭露處理者及用途。

- [ ] **D-03 建立 Subprocessor Register**\
  盤點 hosting、CDN、analytics、error monitoring、email、CRM、LLM、Langfuse、chat、backup 等實際接收資料的服務；未使用者不得寫入政策充數。

- [ ] **D-04 Cookie／Consent 實作**\
  必要與非必要儲存分離；依 targeting 市場決定 consent mode。拒絕分析後不得繼續用等價識別方式追蹤。

- [ ] **D-05 Retention Policy**\
  為 raw event、IP、session、chat、Contact、requirement、附件、通知 log、backup 分別定義保存期與刪除工作；禁止「永久保留供研究」。

- [ ] **D-06 Data Subject Request 流程**\
  能依 email／visitor／session 找出、匯出、更正、刪除資料；建立身份驗證、處理期限、例外與稽核記錄。

- [ ] **D-07 IP 與裝置資料最小化**\
  評估截短／雜湊 IP、user agent 保存、地理推斷精度與 raw log 期限；analytics dashboard 不直接暴露不必要識別資料。

- [ ] **D-08 Chat 專用揭露**\
  AI 客服開啟前說明由 AI 回覆、可能出錯、對話會保存／人工檢視、不要輸入機密或個資，以及不會產生報價／銷售回覆。

- [ ] **D-09 資料地圖與處理紀錄**\
  建立從 Browser → CDN → Web → API → DB／analytics／LLM／通知的資料流，標示 controller、processor、資料類別、目的、區域與保存期。

- [ ] **D-10 Incident Response**\
  建立個資或需求內容外洩的偵測、封鎖、評估、通知、證據保存與 postmortem 流程。

### D 組驗收

- [ ] Privacy／Cookie／表單實際行為一致，且有真實可用的權利請求管道。
- [ ] 非必要追蹤拒絕後，瀏覽器與後端驗證不建立對應識別事件。
- [ ] 測試資料刪除後，主資料、索引、附件與 downstream processor 均能按政策處理。

## P0-E. 零外寄與內部流程隔離

- [ ] **E-01 建立 tenant 級 Outbound Kill Switch**\
  對 NorthForge reference tenant 設 `outbound_external_enabled=false`；所有 email、SMS、LINE、Telegram、CRM workflow、webhook、nurture、Agent reply 都必須在單一共用 policy layer 檢查，不能只靠 UI toggle。

- [ ] **E-02 關閉 RFQ Auto-reply**\
  驗證 `auto_reply_enabled=false`，並新增自動測試證明 NorthForge tenant 無法發送；即使設定誤開也被 kill switch 阻斷。

- [ ] **E-03 關閉 Nurture 與行銷自動化**\
  不執行 `seed_demo_briefs_ctas_nurture.py` 的銷售序列；清除已匯入的假案例、價格、Sales Team 寄件人及待發 outbox。

- [ ] **E-04 阻斷 AgentOS／AI Send Reply**\
  可產生內部測試草稿，但不得 dispatch；UI 顯示 `Reference tenant — external send disabled`，API 回傳明確 policy error 並寫 audit log。

- [ ] **E-05 通知分級**\
  允許「對內」系統通知給已授權的 ForgeBase 測試操作員；禁止任何送到提交者或第三方業務名單的訊息。通知內容不得稱新 lead／qualified RFQ。

- [ ] **E-06 CRM／Webhook 策略**\
  未完成 processor 揭露與資料最小化前全部關閉。若為測試整合而啟用，只能送至 ForgeBase 控制的 test sink，且 payload 去識別化。

- [ ] **E-07 防止人工誤寄**\
  NorthForge 後台不顯示可用的 Send／Reply／Enroll 按鈕，或需要不可由一般 operator 解除的 policy；複製 email 也應有警示與 audit event。

- [ ] **E-08 Outbound Canary Test**\
  上線前對每個 outbound path 建立測試，確認被阻斷且事件標記 `blocked_by_reference_policy`；不得以真正外寄驗證。

- [ ] **E-09 監控與告警**\
  `external_delivery_attempt > 0` 立即告警；報表顯示 blocked 次數、來源功能與操作者。

### E 組驗收

- [ ] 從 Contact、Requirement、AI Chat、Admin、API、Nurture、AgentOS、Webhook、CRM 各走一次，對提交者的外寄數皆為 0。
- [ ] 即使誤開 auto-reply 或建立 nurture，policy layer 仍阻擋送達。
- [ ] 資料權利或資安事件聯絡有獨立流程，不被錯誤阻擋。

## P0-F. 真實流量與量測可信度

- [ ] **F-01 禁止生產環境注入模擬資料**\
  `seed_demo_visitors.py` 與 `scripts/demo_seed_and_verify.py --mode demo` 加入 hard guard：production／reference tenant 無法執行，除非在隔離測試環境且使用明確測試 tenant。

- [ ] **F-02 清除或隔離既有模擬資料**\
  先辨識目前 DB 是否已有 seed visitors／sessions／contacts／RFQs。不得直接刪除未知真實資料；以來源標記與人工核准後移到 test tenant 或排除於報表。

- [ ] **F-03 建立資料來源標記**\
  所有 visitor、session、event、chat、requirement 至少有 `environment`、`tenant`、`data_origin`、`is_internal`、`is_bot`、`consent_state`；歷史缺值不可默認為真實。

- [ ] **F-04 排除內部流量**\
  ForgeBase 團隊 QA、監控、預覽、Playwright、健康檢查與 uptime bot 必須可識別並在公開 KPI 預設排除，同時保留可稽核 raw count。

- [ ] **F-05 Bot 與 spam 分類**\
  建立 verified bot、suspected bot、spam、duplicate 與 human-valid 分層；不得把搜尋引擎 crawler 算成訪客或 engagement。

- [ ] **F-06 Server-side 事件契約**\
  定義 event name、觸發條件、去重鍵、必要欄位、PII 禁止欄位與版本。公開 endpoint 不得讓任意 client 偽造高意圖／轉換事件。

- [ ] **F-07 Requirement submit truth event**\
  只有後端成功寫入且通過基本 validation／spam check 才發 `requirement_submitted`；開表單、AI 建議或按 CTA 不得算完成。

- [ ] **F-08 建立同 cohort 漏斗**\
  Impression → landing session → engaged session → CTA click → form start → valid requirement submission 使用同一 cohort、時間窗與去重規則。

- [ ] **F-09 UTM／Referrer／SEO 歸因**\
  保存 first-touch 與 last-touch，處理 direct／unknown、跨網域與 consent；不得把無法判斷的來源硬歸因給特定活動。

- [ ] **F-10 分析 QA**\
  用已知測試流量在 staging 驗證每個事件一次且只出現一次；正式環境僅以內部標記 QA，不注入虛構外部訪客或成果。

### F 組驗收

- [ ] 任一 KPI 都能追溯到事件定義、SQL／API、排除規則與原始紀錄。
- [ ] 公開儀表可同時顯示 raw、bot/internal 排除後與 valid submission 數，不混淆。
- [ ] 既有 seed data 不會出現在正式 reference case study。

## P0-G. 公開測試所需平台安全修正

以下承接《ForgeBase 全面稽核》；方案 B 仍會收集真實個資與需求，不能因為不銷售就延後。

- [ ] **G-01 ContentAsset 全面 tenant isolation**。
- [ ] **G-02 Credential API 不信任 client `tenant_id`，由 auth context 決定租戶**。
- [ ] **G-03 Public visitor／session UUID 綁定 tenant，拒絕跨租戶重用**。
- [ ] **G-04 Contact／Requirement 對 visitor、product、application 關聯做同租戶驗證**。
- [ ] **G-05 修正 stored XSS；所有 rich content 走一致 sanitizer**。
- [ ] **G-06 Upload 做 magic-byte sniffing、SVG sanitize／隔離、大小限制與 malware policy**。
- [ ] **G-07 Scheduler 改為單一執行者，避免多 worker 重複工作**。
- [ ] **G-08 公開 AI Advisor 加 rate limit、token／成本 budget、plan／tenant gate 與 abuse controls**。
- [ ] **G-09 修正前端 production dependency High vulnerabilities，或完成有期限的風險接受**。
- [ ] **G-10 背景任務 durable 化**：需求收件後的 routing、internal notification、webhook／CRM test sink 等採 outbox、retry、idempotency、dead-letter。
- [ ] **G-11 Secrets 與 logging 清查**：log 不記錄完整表單、chat、token、cookie、authorization、附件內容。
- [ ] **G-12 安全 E2E**：跨租戶、越權、XSS、惡意 SVG、暴力提交、IDOR、重送與 outbound policy 測試進 CI。

### G 組驗收

- [ ] 既有 8 項 P0 均有修正證據或正式 risk acceptance；涉及個資隔離、XSS、濫用及外寄者不得接受延期。
- [ ] Release CI 自動執行 tenant isolation、public forms、outbound block 與 critical security tests。

## P0-H. 部署、監控與停止機制

- [ ] **H-01 建立獨立 reference tenant 與環境設定**，不可共用 demo／staging tenant。
- [ ] **H-02 CI Gate**：typecheck、lint、unit、integration、migration、security E2E、outbound canary、claim scan 全通過才可 deploy。
- [ ] **H-03 DB／asset backup 與 restore drill**，明確 RPO／RTO、加密、權限和 retention。
- [ ] **H-04 Production configuration inventory**：domain、DNS、TLS、CDN、API、DB、storage、analytics、email、LLM、Sentry／logs 全部列出 owner 與目的。
- [ ] **H-05 建立 Kill Switches**：公開表單、AI Chat、tracking、非必要 analytics、附件、整站維護模式可個別關閉。
- [ ] **H-06 建立監控**：availability、JS error、API 5xx、form success、spam、DB latency、queue backlog、LLM latency／cost、external delivery attempt。
- [ ] **H-07 Incident runbook**：假主張漏出、資料外洩、外寄誤發、追蹤未經同意、事件灌水、服務中斷各有處理步驟與 owner。
- [ ] **H-08 上線後 24h／72h／7d review**：確認收件、資料品質、外寄為零、privacy／cookie 行為與搜尋引擎呈現。

---

# 6. P1 — 公開測試品質與完整功能驗證

## P1-A. Reference Site 內容與 UX 完整度

- [ ] **P1-A01 建立全站 reference label component**，確保 Header／Footer／form／AI／product disclaimer 使用相同已核准文案。
- [ ] **P1-A02 保留商業吸引力**：Hero 聚焦「探索專業手工具採購規格與需求流程」，而非強調這只是軟體 demo。
- [ ] **P1-A03 產品頁提供真實研究價值**：規格比較、應用條件、買方問題清單、所需文件欄位與可下載的 reference checklist。
- [ ] **P1-A04 下載內容不偽裝成真證書／catalog**；檔名、封面與頁尾均標示 reference material。
- [ ] **P1-A05 完整繁中／英文 parity**；未知 locale 不回退成可能誤導的英文發布內容。
- [ ] **P1-A06 Accessibility**：WCAG 導覽、焦點、label、錯誤訊息、色彩、鍵盤、dialog 與手機表單。
- [ ] **P1-A07 Performance／Core Web Vitals**：圖片尺寸、LCP、CLS、JS bundle、third-party scripts 與快取。
- [ ] **P1-A08 SEO technical QA**：canonical、hreflang、robots、sitemap、redirect、404、metadata、OG、structured data。
- [ ] **P1-A09 將 AI 生成圖片的 reference／illustrative 屬性寫入 asset metadata**，讓前台可一致顯示。
- [ ] **P1-A10 建立真人內容審核 checklist**，不使用 AI 寫內容或 AI 翻譯內容。

## P1-B. AI 客服改為 Reference Assistant

- [ ] **P1-B01 更名與揭露**：從模擬客服改為 Reference Assistant／採購規格導覽助手。
- [ ] **P1-B02 回答邊界**：不得聲稱 NorthForge 可製造、供貨、認證、定價、交期、保固或回覆。
- [ ] **P1-B03 知識來源只讀取 published、approved、reference-safe 內容**。
- [ ] **P1-B04 修正 session／tenant ownership 與 rate limit／budget**。
- [ ] **P1-B05 修正 handoff 語意**：AI 建議不等於 conversion；只有訪客確認並成功提交才計 `requirement_submitted`。
- [ ] **P1-B06 建立 server-side requirement draft**；不把需求或 PII 放在 query string。
- [ ] **P1-B07 顯示來源與不確定性**；找不到可靠內容時明確說不知道，不生成假 confidence 或假規格。
- [ ] **P1-B08 Unsupported claim validator**：對 manufacturer、certification、price、lead time、safety、legal claim 做 post-validation。
- [ ] **P1-B09 AI config Admin**：開關、model、budget、system policy version、allowed sources、blocked claims、retention、quality dashboard。
- [ ] **P1-B10 AI E2E**：英文／繁中、惡意 prompt、PII、機密資料提醒、引用、not-found、draft、確認提交、outbound block。

## P1-C. Admin 營運流程

- [ ] **P1-C01 Reference tenant banner**：所有頁面顯示「真實公開資料／非銷售 tenant／外寄停用」。
- [ ] **P1-C02 將 Inbox 顯示名稱改為 Requirements**，保留技術 ID，但不叫 Sales Leads。
- [ ] **P1-C03 增加資料分類**：valid requirement、research-only、spam、duplicate、test/internal、data-rights request。
- [ ] **P1-C04 建立內部處理狀態**：received → validated → internally reviewed → workflow tested → archived；禁用 quoted／negotiation／won。
- [ ] **P1-C05 內部 SLA 不假裝 customer response SLA**：改量測 validation time、review time、routing time、workflow completion time。
- [ ] **P1-C06 Draft 僅供測試**：可測 AI／template draft，但清楚標示 never sent，且不能讓狀態變 quoted 或 first_response。
- [ ] **P1-C07 Role／audit**：誰查看、匯出、分類、刪除、嘗試外寄都留 audit event。
- [ ] **P1-C08 PII access controls**：最小權限、遮罩、export 權限、短效下載連結與存取稽核。
- [ ] **P1-C09 不要求 operator 輸入 raw UUID／JSON** 完成主要工作。
- [ ] **P1-C10 Dashboard 加上 reference metric definitions 與資料品質警示**。

## P1-D. 真實公開測試計畫

- [ ] **P1-D01 設定測試期間與基準線**：至少定義開始日、觀察窗、主要市場／語言與不做付費誘導的限制。
- [ ] **P1-D02 建立 acquisition plan**：SEO、可識別的 ForgeBase owned channels、內容發布與必要時透明廣告；廣告素材同樣標示 reference project，不以假工廠身分投放。
- [ ] **P1-D03 定義主要假設**：例如 reference product depth 是否提高 engaged session、需求表單完成率及規格欄位完整度。
- [ ] **P1-D04 每次只變更可歸因的主要元素**，記錄 experiment ID、版本、開始／結束、樣本與結果。
- [ ] **P1-D05 建立低樣本規則**：未達預設樣本不下轉換結論，不用百分比掩蓋極小分母。
- [ ] **P1-D06 觀察真實需求但不進行銷售 follow-up**；不得利用未告知用途另行拓客。
- [ ] **P1-D07 定期資料品質 review**：每週抽查 submission、spam、bot、event chain、consent、source 與 duplicate。
- [ ] **P1-D08 建立停止條件**：發現誤導內容、外寄、資料外洩、過量 spam、AI 危險回答或 consent 失效時立即停用對應功能。

---

# 7. P2 — 成效深化與銷售案例產出

## P2-A. 實驗與產品學習

- [ ] **P2-A01 CTA 實驗**：比較 `Submit a Sourcing Requirement` 與 `Test the Requirement Workflow`，但兩版揭露強度必須相同。
- [ ] **P2-A02 表單長度實驗**：不以多蒐集個資換取「完整度」；比較 progressive disclosure 與單頁表單。
- [ ] **P2-A03 內容深度實驗**：產品規格表、比較表、採購 checklist、應用頁對 engagement／submission 的影響。
- [ ] **P2-A04 AI 輔助實驗**：量測 helpfulness、citation coverage、draft confirmation，不把 chat open 當 conversion。
- [ ] **P2-A05 Intent 模型驗證**：先以 rule-based、submit-time snapshot 和人工標記比對；低樣本不宣稱 ML 能預測成交。
- [ ] **P2-A06 多語表現**：分語言比較曝光、engagement、form start 與 valid requirement，避免跨語言直接合併造成偏差。

## P2-B. 可對外引用的案例研究

- [ ] **P2-B01 建立不可變 KPI snapshot**：報告期間結束後保存查詢、資料字典、排除規則、hash／匯出與審核紀錄。
- [ ] **P2-B02 案例敘事只描述真值**：可寫 impressions、human sessions、engaged sessions、CTA clicks、valid requirement submissions、零人工銷售 follow-up。
- [ ] **P2-B03 清楚揭露研究條件**：Reference Site、流量來源、期間、語言、bot/internal 排除、沒有銷售回覆與沒有收入驗證。
- [ ] **P2-B04 不使用不可證明的商業結果**：不寫 lead quality、quote rate、close rate、revenue uplift、ROI、客戶成功或工廠成交。
- [ ] **P2-B05 案例內容不公開提交者 PII 或可識別商業需求**；引用需求主題時先聚合、去識別並達最低群組門檻。
- [ ] **P2-B06 建立可重現 appendix**：事件版本、SQL／API 定義、樣本數、信賴區間、已知限制與變更紀錄。
- [ ] **P2-B07 第二階段升級路徑**：若要證明完整 RFQ→Quote→Won，另找一家具正式授權、願意履約與回覆的真實製造商；不可從 NorthForge reference data 推論。

---

## 8. 正式量測資料字典

| 指標 | 正式定義 | 不得包含／不得解讀為 |
|---|---|---|
| Search impression | Search Console 或相應平台記錄的真實曝光 | 訪客、品牌認知或潛在客戶 |
| Human session | 排除 verified／suspected bot、內部、監控與測試後的 session | 唯一自然人、合格買家 |
| Engaged session | 符合預先定義的互動／時間／頁數門檻 | 高意圖或採購意願的直接證明 |
| CTA click | 使用者明確點擊 reference CTA | 表單開始、提交或 lead |
| Form start | 使用者開始輸入必要欄位 | 同意、有效需求或完成提交 |
| Requirement submitted | 後端成功建立、通過 schema 與基本反 spam 的提交 | 正式 RFQ、報價請求被接受、qualified lead |
| Valid requirement | 經預定規則或人工判定為可理解、非 spam／duplicate 的需求 | 可供貨、會成交或值得業務追蹤 |
| Workflow completed | ForgeBase 內部完成分類、routing、draft／review 與歸檔測試 | 已回覆、已報價或 customer SLA 完成 |
| AI handoff suggested | AI 顯示需求表單建議 | handoff completed 或 conversion |
| Requirement draft confirmed | 使用者確認 draft 並進入表單 | 正式提交；仍須後端成功才成立 |
| External replies sent | 對 NorthForge reference tenant 應永遠為 0 | 若大於 0，視為 incident，不是功能成果 |

### 對外案例可用句型

> During the stated observation period, the ForgeBase-operated NorthForge reference site generated X search impressions, Y human sessions, and Z valid sourcing-requirement submissions. The project sent no sales replies and did not test quotation or revenue conversion.

中文：

> 在所述觀察期間內，由 ForgeBase 營運的 NorthForge 參考網站取得 X 次搜尋曝光、Y 次真人工作階段與 Z 筆有效採購需求提交。此專案未發送業務回覆，也未測試報價或營收轉換。

---

## 9. 建議執行順序與依賴

### Phase 0 — 決策與封鎖（1–2 天）

1. A-01～A-06：核准控制者、定位、Claim Policy 與零外寄政策。
2. E-01～E-09：先完成技術性 outbound block。
3. F-01～F-03：禁止正式環境 seed，建立資料來源標記。
4. H-05：確認表單、Chat、tracking 可即時關閉。

出口條件：即使有人誤操作，也無法對提交者發信；production 不接受模擬資料注入。

### Phase 1 — 內容與收件契約（3–7 天）

1. B 組：全站 Claims Register、內容改寫、認證／工廠／人物處理。
2. C 組：CTA、表單、成功訊息與防濫用。
3. D 組：Privacy、Cookie、retention、權利請求與資料流。
4. P1-A01～A05：統一 reference label 與雙語。

出口條件：任何入口到提交完成，都沒有虛構交易身分或回覆承諾。

### Phase 2 — 平台安全與分析真值（依 P0 修正量排程）

1. G 組：多租戶、XSS、上傳、Chat 濫用、scheduler、durable jobs。
2. F-04～F-10：事件契約、bot/internal 排除、同 cohort funnel。
3. H 組：CI、backup、monitoring、incident runbook。

出口條件：公開個資可安全處理；KPI 可追溯；CI 能阻止重大回歸。

### Phase 3 — 完整產品 dogfood（3–5 天＋觀察期）

1. P1-B：Reference Assistant。
2. P1-C：Admin requirement workflow。
3. P1-D：公開測試計畫與停止條件。
4. 桌機／手機、英文／繁中完整 E2E。

出口條件：真實 requirement 從前台到內部歸檔全程可運作，但沒有對外送達。

### Phase 4 — 真實流量與案例（建議至少 4–8 週觀察）

1. 啟動 SEO／owned acquisition。
2. 24h、72h、7d 上線檢查；其後每週資料品質 review。
3. 達預設樣本後進行 P2 實驗。
4. 產出帶限制條件、可重現的案例研究。

---

## 10. Go／No-Go 上線閘門

只有以下全部為「是」，才允許公開收集 requirement：

- [ ] 真實 ForgeBase 控制者、Privacy 聯絡管道與資料用途已核准。
- [ ] Header／About／Footer／表單／成功頁／AI 均清楚說明 Reference Project。
- [ ] 虛構法人、工廠、人物、地址、認證、客戶、產能、供貨與回覆承諾已移除或正確重構。
- [ ] `Request a Quote`、`Get Pricing`、`Request Sample` 與回覆時窗已從公開體驗移除。
- [ ] Outbound kill switch 通過所有路徑測試，對提交者外寄為 0。
- [ ] Production／reference tenant 無法執行模擬 visitor／event／Contact／RFQ seed。
- [ ] Privacy、Cookie、retention、processor 與實際資料流一致。
- [ ] 多租戶隔離、XSS／upload、濫用防護與 Chat 成本控制的 P0 已修正。
- [ ] 表單具有 anti-spam、idempotency、server validation、錯誤處理與 accessibility。
- [ ] Analytics 能排除 internal／bot／test，且 requirement 只由後端成功事件計數。
- [ ] Kill switches、backup／restore、monitoring、incident runbook 已驗證。
- [ ] 英文／繁中、桌機／手機、SEO metadata 與 structured data 已人工抽查。
- [ ] 法務已依實際目標市場完成 review。

### 立即 No-Go 條件

出現以下任一情況，應關閉表單／Chat 或下線修正：

1. 使用虛構製造商身分引導真實買方提交資料。
2. 公開假證書、假證書編號、假廠址、假人物或假成交案例。
3. 未在提交前說明不報價、不回覆與資料用途。
4. 對提交者發送 auto-reply、nurture、AI／人工 sales reply。
5. 無法證明報表已排除 seed、內部與 bot 流量。
6. 發生跨租戶存取、stored XSS、惡意檔風險或個資外洩。
7. Privacy／Cookie 宣稱與實際 processor 或 tracking 不一致。

---

## 11. 驗收證據包

每次上線應保存以下資料，未保存即視為未完成驗收：

- [ ] 核准的定位、Claim Policy、Privacy／Terms／Cookie 版本與生效日。
- [ ] Claims Register 與禁止主張掃描結果。
- [ ] 全站英文／繁中關鍵畫面：Hero、About、Product、Standards、Footer、form before submit、success、Chat disclosure。
- [ ] Outbound kill switch 設定匯出與各路徑測試紀錄。
- [ ] CI 測試：tenant、XSS／upload、forms、AI、analytics、outbound、migration。
- [ ] Production config inventory、processor register 與資料流圖。
- [ ] Analytics event spec、metric dictionary、bot／internal 排除規則與查詢版本。
- [ ] Backup／restore drill 與 incident runbook 演練紀錄。
- [ ] 上線後 24h／72h／7d review 結果。
- [ ] 案例報告所用 immutable KPI snapshot 與限制說明。

---

## 12. 本次不做與明確禁用

- 不使用 Legacy Site Intake／舊站匯入。
- 不使用 AI 產生或翻譯網站內容；公開文案由人工撰寫、審核與發布。
- 不執行正式環境的假訪客、假 session、假 Contact、假 requirement／RFQ seed。
- 不把 NorthForge 包裝成真實法人、工廠、證書持有人、供應商或賣方。
- 不以小字頁尾或隱藏 Terms 修補 Hero、產品頁或 CTA 的重大誤導。
- 不對 requirement submitter 發送 sales／quote／sample／nurture 回覆。
- 不宣稱本實驗能證明 ForgeBase 的 quote、close、revenue 或 ROI 成效。
- 不公開提交者的個資、公司、完整需求、圖面或可重識別資料。

---

## 13. 外部法規核對基準

以下僅作產品與資料治理盤點基準，不取代目標市場的正式法律意見：

- 台灣《個人資料保護法》：蒐集與處理應遵守誠實信用、目的必要性與告知義務，並具備適法依據。\
  <https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=I0050021>
- 台灣《公平交易法》第 21 條：不得對足以影響交易決定的品質、製造者、製造地等事項作虛偽不實或引人錯誤表示。\
  <https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0150002>
- 歐盟 GDPR（若實際 targeting／資料處理適用）：資料處理須符合公平、透明、目的限制、資料最小化、正確性與保存限制。\
  <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679>

---

## 14. 最終 Definition of Done

方案 B 完成不是「網站加上一句 Demo 聲明」，而是以下結果同時成立：

1. NorthForge 是一個視覺與內容皆完整、但身份和目的透明的 reference site。
2. 訪客基於真實看到的 reference proposition 自願瀏覽與提交需求。
3. ForgeBase 能完整接收、追蹤、分類、分析、內部處理與歸檔真實資料。
4. 任何功能或人員都不能向提交者發出銷售、報價或培育訊息。
5. 數據可證明是真實公開流量，並能排除 seed、內部、bot、spam 與 duplicate。
6. 對外案例準確描述「Reference Site 的流量與需求提交成效」，不跨越到未被測試的銷售成果。
7. 平台的多租戶、安全、隱私、事件與營運 P0 已達公開測試標準。

達成以上條件後，NorthForge 才能成為 ForgeBase 的可信 dogfood tenant、公開測試場與未來銷售範例。
