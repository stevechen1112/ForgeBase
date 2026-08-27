# ForgeBase 北極星產品分類與核心缺口實作計畫

> 文件日期：2026-08-26\
> 文件狀態：產品決策基準／工程實作藍圖\
> 適用範圍：ForgeBase B2B 官網、訪客意圖、企業辨識、聯絡人補全、個人化外聯、回覆接手與 RFQ／成交歸因\
> 依據：2026-08-26 現有程式碼、資料模型、測試結果、產品功能目錄與既有公司辨識 POC 計畫
> 最新補充：Build vs. Buy 邊界、供應商候選、OEM／Reseller Gate 與資料飛輪策略

---

## 1. 本文件的結論

ForgeBase 的北極星不是單一的 AI 客服、追蹤工具或 EDM 工具，而是一條完整的 B2B 商機轉換鏈：

```text
匿名訪客
  → 行為追蹤
  → 意圖評分
  → 推測公司
  → 尋找公司相關聯絡窗口
  → 依旅程產生個人化信件
  → 寄送與追蹤
  → 對方回覆
  → 真人業務接手
  → RFQ／成交
```

產品功能應依此分成四類：

1. **核心已完善**：已有可運作的主流程、資料模型、權限與測試基礎；後續以生產驗證及細部強化為主。
2. **核心未完善**：北極星不可缺少，但目前只有局部元件、POC 計畫或尚無正式資料模型；必須列入優先實作。
3. **非核心但應該留**：不是北極星主幹，卻能提高內容效率、轉換率、可管理性或產品競爭力。
4. **非核心可以刪除**：不支援北極星、沒有實際使用證據，或會造成維護／安全負擔；須經停用與依賴稽核後再移除。

最重要的分類修正如下：

- **公司辨識、聯絡人補全、個人化外聯不是實驗功能，而是尚未交付的核心成長引擎。**
- **意圖評分是核心；ML 只是意圖評分的一種可選演算法。** 現有規則式評分和多構面訊號可以先支撐北極星，不應把「沒有 ML」誤判為「沒有意圖評分」。
- **寄送郵件不等於完成外聯。** 必須能保存旅程依據、內容快照、審核、寄送事件、回覆、接手與 RFQ／成交歸因，才算完成北極星閉環。
- **隱私、租戶隔離、同意管理、退訂、抑制名單、冪等與稽核不是旁支功能，而是核心護欄。**

---

## 2. 與其他文件的關係

本文件是產品優先級與實作順序的主文件，並引用以下既有文件：

- `FORGEBASE_PRODUCT_CLAIMS_IMPLEMENTATION_AUDIT_2026-08-26.md`：原始產品敘述逐項查核、證據、測試與風險。
- `FORGEBASE_COMPANY_IDENTIFICATION_AND_CONTACT_ENRICHMENT_PLAN_2026-08-16.md`：公司辨識、供應商 POC、Shadow Mode、準確率及合規方向。

若三份文件出現用語差異，以本文件的北極星和四分類決策為優先；技術證據仍回查原始稽核文件與程式碼。

---

## 3. 分類判定規則

### 3.1 「核心已完善」的定義

本文件中的「已完善」不代表永遠不需改進，而是至少符合：

- 已有正式資料模型或可靠的資料來源。
- 已有 API／服務和可操作介面，或有清楚的自動化入口。
- 多租戶範圍及權限邊界已存在。
- 主要成功、失敗及重送路徑可被測試。
- 不依賴尚未取得的第三方授權才能成立。
- 能在測試／試營運環境形成可驗證成果。

生產環境仍需另外確認部署設定、郵件網域、資料庫、監控、告警及法遵條件。

### 3.2 「核心未完善」的定義

只要缺少以下任一項，就不得因為已有 UI、服務檔案或概念驗證而標為完善：

- 穩定且可追溯的領域資料模型。
- 從上一個北極星節點到下一個節點的正式關聯。
- 供應商成本、品質、失敗與重試治理。
- 人工審核、權限、同意或退訂護欄。
- 可證明的準確率、送達率、回覆或成交歸因。
- 對應的端到端測試與生產觀測。

### 3.3 「非核心但應該留」的定義

符合至少一項：

- 明顯提高核心漏斗的轉換效率。
- 降低多語、內容、SEO 或營運維護成本。
- 是人工判讀、客服、業務或平台管理的重要工作介面。
- 是現有功能的安全、治理、可解釋或可回復能力。
- 已有可靠實作，保留成本低於刪除及日後重建成本。

### 3.4 「非核心可以刪除」的定義

必須同時確認：

- 不在北極星主幹，也不是必要護欄。
- 沒有客戶、營運流程、資料遷移或其他模組依賴。
- 近 30～60 天沒有有效使用證據，或從未正式啟用。
- 停用後不影響已承諾的方案與資料存取。
- 已有資料保留、匯出或回復方案。

因此第四類應稱為「**可刪除候選**」，不是看到檔案後立即刪除。

---

## 4. 北極星逐節點現況

| 北極星節點 | 現有基礎 | 主要缺口 | 分類結論 |
|---|---|---|---|
| 匿名訪客 | `Visitor`、第一方訪客識別、tenant 關聯、同意狀態 | 生產環境追蹤覆蓋率仍需觀測 | 核心已完善 |
| 行為追蹤 | `TrackingEvent`、session、頁面／動作、分數增量、旅程查詢 | 公司辨識前的網路訊號需另建安全資料層 | 核心已完善 |
| 意圖評分 | 規則分數、意圖階段、四構面訊號、自訂規則；另有 ML 服務 | ML 缺乏穩定訓練資料時不可作主判斷 | 核心已完善；ML 為可選 |
| 推測公司 | 既有 POC／供應商計畫；feature catalog 中 `company_identification` 鎖定關閉 | 尚無正式 `NetworkObservation`／`CompanyIdentification` 模型、供應商 runtime、Shadow Mode 結果 | 核心未完善 |
| 尋找聯絡窗口 | 既有 `Contact` 可保存已知聯絡人；公司辨識計畫有 `ContactCandidate` 構想 | 尚無候選人、來源、職能、信箱驗證、信心與審核流程 | 核心未完善 |
| 依旅程產生個人化信件 | Copilot 可建立需核准的跟進信；Dynamic CTA 與旅程資料可提供內容訊號 | 尚無旅程摘要、公司／產品興趣快照、可驗證個人化草稿及禁止杜撰規則的完整管線 | 核心未完善 |
| 寄送與追蹤 | Nurture sequence／step／enrollment／outbox、人工核准、Resend 事件、bounce／complaint suppression | Outbox 未保存完整內容快照；Delivery event 缺 tenant 與內部信件 FK；缺 click／unsubscribe 與北極星歸因主鍵 | 核心未完善（元件可重用） |
| 對方回覆 | 現有 webhook 處理寄送、退信、客訴等 outbound events | 沒有 inbound email webhook、thread、reply 模型與意圖分類 | 核心未完善 |
| 真人業務接手 | RFQ 指派、SLA、跟進提醒、Chat handoff、營運通知 | 未把 inbound reply 轉成可指派的持久任務，缺回覆上下文與 SLA | 核心未完善（接手基礎已存在） |
| RFQ／成交 | `RFQRequest`、狀態、品質、SLA、outcome、won／lost 與成果面板基礎 | 缺 outreach → reply → handoff → RFQ → revenue 的閉環歸因 | RFQ 核心已完善；閉環歸因核心未完善 |

這張表顯示：北極星的前段觀察與後段 RFQ 工作台已有良好基礎，真正斷裂在「**推測公司 → 找聯絡窗口 → 個人化外聯 → 收到回覆 → 接手與歸因**」。

---

## 5. 四分類完整清單

### 5.1 類別一：核心已完善

#### A. 官網與內容基礎

- 受管 B2B 官網交付。
- 商品、分類、頁面、應用、FAQ、認證與產能等內容管理。
- 圖片、文件與替代文字資產管理。
- 公開內容查詢與網站呈現。

#### B. AI 產品顧問／前台客服

- 依網站已發布內容及知識來源回答。
- 可使用網站內容與上傳文件建立知識來源。
- 有來源約束、引用／可追溯方向與知識評估基礎。
- 能引導產品、需求條件及 RFQ，而不是純粹無方向閒聊。
- 前台 AI 顧問與後台 Copilot 角色有明確區隔。

> 完善邊界：AI 不可宣稱「絕不錯誤」；正確產品說法應是「只依授權知識回答、資訊不足時拒答或轉交」。

#### C. 匿名訪客與第一方行為資料

- 匿名 `Visitor` 與 session 關聯。
- `TrackingEvent` 保存頁面、動作、分數變化和必要網路訊號。
- 可查詢訪客旅程、來源、裝置、國家與互動。
- 同意狀態、租戶邊界與資料最小化已具備基礎。

#### D. 意圖評分與可解釋訊號

- 規則式分數與階段。
- 不同頁面／動作權重。
- 四構面或多訊號的意圖解釋。
- 可用於通知、分群、CTA、Nurture 等後續動作。

> 核心是「可信且可解釋的意圖判斷」，不是特定 ML 技術。ML 只有在資料量、標籤品質及離線／線上評估通過後才可升級為核心演算法。

#### E. 已知聯絡人與 RFQ 作業

- `Contact` 可關聯 tenant、email 與 visitor。
- RFQ 建立、品質分數、狀態、指派、備註、匯出與歷程。
- 待辦、期限、逾期、通知與 SLA。
- RFQ outcome、won／lost 及成果資料基礎。
- RFQ 回覆信具有租戶開關、品質門檻及外部 kill switch。

#### F. 核心護欄

- 多租戶隔離及角色權限。
- Feature entitlement 與產品階段開關。
- 郵件核准閘門。
- Bounce／complaint suppression。
- Durable operational outbox、重試與 idempotency 基礎。
- 隱私最小化與雜湊郵件事件。

### 5.2 類別二：核心未完善

#### A. 公司辨識正式化

- 安全的來源 IP／網路觀測資料。
- VPN、代理、雲端主機、bot 與私人網段排除。
- 一個或多個公司辨識 provider adapter。
- 公司候選、信心、證據、來源、衝突與 TTL。
- Provider 用量、成本、quota、cache、retry、circuit breaker。
- 人工確認／否決／修正與可回饋資料。
- 30 天 Shadow Mode 與高信心 precision 驗證。

#### B. 公司相關聯絡窗口補全

- 依公司、產業、地區、產品興趣及目標職能尋找候選人。
- 候選人的職稱、部門、資歷、公開來源及公司關聯。
- 商務信箱驗證、catch-all／unknown 狀態、來源時間及信心。
- 去重、過期、退出及禁止聯絡處理。
- 候選人不等於訪客本人；UI 和文案不可暗示個人身份已被辨識。
- 人工選擇候選人後，才轉成正式 `Contact` 或外聯收件人。

#### C. 旅程理解與個人化外聯草稿

- 將頁面、產品、下載、CTA、詢價草稿、時間與意圖構面轉成可讀摘要。
- 產生「為何選這家公司／窗口／產品」的證據包。
- 只使用已發布產品與已核准知識，禁止生成未有依據的規格、價格或客戶關係。
- 每封信保存完整、不可變的 subject／HTML／text 快照。
- 保存 prompt／policy／knowledge version、證據引用及人工修改差異。
- 草稿預設只進審核佇列，不直接寄送。

#### D. 可追溯的寄送與互動事件

- 建立穩定的 `OutreachMessage`，而不是只靠可變的 `NurtureStep`。
- 將 provider message id、delivery event、收件人、公司、訪客旅程與 RFQ 串在同一歸因鏈。
- 支援 queued、approved、sending、sent、delivered、opened、clicked、replied、bounced、complained、unsubscribed、failed 等狀態。
- 支援退訂連結、租戶／全域 suppression、頻率上限及安靜時段。
- 寄送前再次檢查權限、抑制、信箱品質、內容版本與冪等鍵。

#### E. Inbound reply 與真人接手

- 接收 provider inbound webhook／mailbox event。
- 以 message-id／references／provider thread id 關聯原始外聯。
- 安全保存必要的主旨、正文及附件 metadata；阻擋惡意內容與 oversized payload。
- 分類 positive、question、RFQ、not-now、wrong-person、unsubscribe、negative、auto-reply。
- 任何 unsubscribe／complaint 立即停止後續寄送。
- Positive／question／RFQ 自動建立可指派的 `SalesHandoff`，附上旅程、公司、窗口、信件與回覆摘要。
- 真人可接受、改派、聯絡、建立 RFQ 或結案。

#### F. 閉環歸因

- 保存 visitor → company identification → contact candidate → outreach → reply → handoff → RFQ → outcome 的關聯。
- 支援 direct、assisted、unknown 等 attribution 類型，避免把所有成交誤算為 AI 成效。
- 成果面板顯示數量、轉換率、SLA 與 revenue；可回查原始證據。

### 5.3 類別三：非核心但應該留

| 功能 | 保留原因 | 建議狀態 |
|---|---|---|
| 多語內容草稿與連動 | 降低 B2B 多國網站維護成本，也是原始產品賣點 | 保留；維持人工確認後發布 |
| Dynamic CTA | 可把不同意圖階段引導至下載、產品、聯絡或 RFQ | 保留；持續 A/B 驗證 |
| 受眾分群 | 可支援外聯候選篩選、分析與營運 | 保留；不可取代核心公司／聯絡人模型 |
| Nurture sequence | 可承載已知聯絡人的培育及後續信件 | 保留並與新 `OutreachMessage` 整合 |
| ESP／CRM 整合 | 支援寄送、事件及業務作業 | 保留；依實際 provider 啟用 |
| 通知與 digest | 支援 RFQ、回覆及接手 SLA | 保留；控制噪音與退訂 |
| 後台 AI Copilot | 幫使用者查詢營運狀態、產生需核准動作 | 保留；不得繞過權限或寄信護欄 |
| 商品比較／進階頁面 | 提高內容價值與 SEO／轉換 | 保留；按使用率調整投入 |
| 排程發布、預覽、SEO redirects | 降低內容營運風險 | 保留 |
| AI relation／內容建議 | 可改善站內導覽和內容效率 | 保留觀察；需有採用率指標 |
| Platform admin／方案與 feature 管理 | 多租戶 SaaS 營運必要 | 保留 |
| ML scoring 的資料契約與離線評估能力 | 未來資料成熟後可升級，但不阻塞北極星 | 預設關閉；保留最小可回復能力 |

### 5.4 類別四：非核心可以刪除候選

| 候選 | 判定條件 | 處置建議 |
|---|---|---|
| AgentOS／automation runtime | 沒有實際租戶、外部執行環境或已核准使用案例 | 維持關閉；依賴稽核後移除 UI／route／service，保留 migration 歷史 |
| 重複的 Copilot floating widget | 已確定只使用專屬 Copilot 頁且沒有嵌入式入口需求 | 先移除入口與 bundle，再刪除元件 |
| ML scoring 線上 runtime／UI | 連續觀察無訓練資料、沒有模型 owner、沒有上線計畫 | 移除 runtime 與 UI；可保留欄位／歷史資料及離線契約 |
| 未使用的通知渠道 | 沒有租戶設定、事件量或送達需求 | 個別渠道停用後移除，不刪通知核心 |
| 無採用的 AI relation 推薦介面 | 連續 60 天無採用且不影響網站關聯內容 | 先停入口，再移除建議服務；保留已發布關聯資料 |
| 不安全或未接線的舊 IP resolver | 來源 IP 信任鏈不安全、僅靠公開 organization 字段假定公司 | 以正式 NetworkObservation／Provider Adapter 取代；刪的是舊實作，不是公司辨識能力 |
| Legacy／dead UI、route、service | `rg`、route registry、bundle、測試、telemetry 均證明無依賴 | 按標準退場流程刪除 |

#### 不得列入刪除的項目

- 公司辨識產品能力。
- 聯絡人補全產品能力。
- 個人化外聯產品能力。
- Inbound reply 與真人接手。
- 意圖評分本身。
- 租戶隔離、同意、抑制、退訂、權限、稽核與冪等。
- RFQ、SLA、outcome 與歸因資料。

---

## 6. 目標架構：沿用現況，不重建整套系統

```text
Web Tracker
  └─ Visitor + TrackingEvent + Consent
       └─ Rule/Facet Intent Scoring
            └─ OperationalJob: company_identify
                 ├─ NetworkObservation
                 ├─ Provider Adapter(s)
                 ├─ CompanyIdentification
                 └─ IdentificationReview
                      └─ OperationalJob: contact_enrich
                           ├─ ContactCandidate
                           └─ ProviderUsage / verification
                                └─ JourneySnapshot + OutreachMessage(draft)
                                     └─ Human approval
                                          └─ OperationalJob: outreach_send
                                               ├─ Existing ESP adapter
                                               ├─ EmailDeliveryEvent
                                               └─ OutreachEvent
                                                    └─ InboundReply
                                                         └─ SalesHandoff
                                                              └─ Existing RFQRequest
                                                                   └─ Outcome / Revenue Attribution
```

### 6.1 應直接重用的現有資產

- `Visitor`：匿名訪客主體，不另造第二套匿名 ID。
- `TrackingEvent`：旅程和意圖證據來源。
- 現有 intent score／facets／rules：公司辨識觸發條件。
- `Contact`：人工確認或已知身分後的正式聯絡人；不直接塞入未確認候選人。
- `NurtureSequence`／`NurtureEnrollment`：培育流程與已知聯絡人序列。
- `NurtureOutbox`：可保留做 nurture 排程及人工審核入口，但需連到新的穩定訊息記錄。
- `EmailDeliveryEvent`／`EmailSuppression`：保留原始 provider 事件與安全抑制。
- `OperationalJob`：承載公司辨識、補全、草稿、寄送、回覆分類等非同步工作。
- `RFQRequest`：北極星成交工作台，不另建第二套商機案件。
- 現有通知、SLA、Copilot、Dynamic CTA、feature entitlement 與 tenant 權限。

### 6.2 不應直接硬改成其他用途的現有資產

- 不應把 `TrackingEvent.ip_address` 直接當作公司名稱。
- 不應把 provider 回傳的 organization 字串直接宣稱為訪客公司。
- 不應把 `ContactCandidate` 直接當成實際訪客本人。
- 不應只用 `NurtureOutbox.subject` 和可變的 `NurtureStep` 充當外聯稽核紀錄。
- 不應只靠 `EmailDeliveryEvent.provider_message_id` 猜測 tenant 或商機歸屬。
- 不應把目前衍生的 ops task queue 當成可指派、可接受、可完成的持久 Sales Handoff。

---

## 7. 建議新增／擴充的資料模型

以下是領域責任，不強制每一項都獨立一張表；實作前可依查詢量與 migration 成本合併，但不可失去稽核欄位。

### 7.1 `NetworkObservation`

用途：保存公司辨識所需、經信任鏈處理後的網路觀測，不污染一般 tracking event。

最低欄位：

- `id`, `tenant_id`, `visitor_id`, `session_id`
- `source_event_id`
- 正規化 IP 或隱私化表示；明確資料保留期
- `ip_source`、trusted proxy chain metadata
- `is_private`, `is_bot`, `is_vpn`, `is_proxy`, `is_hosting`
- `country`, `asn`, `asn_org`
- `observed_at`, `expires_at`
- `consent_state`, `policy_version`
- `dedupe_key`

### 7.2 `CompanyIdentification`

用途：保存「推測公司」的候選、信心和證據，不宣稱確定身份。

最低欄位：

- `id`, `tenant_id`, `visitor_id`, `network_observation_id`
- `company_name`, `domain`, `provider_company_id`
- `provider`, `confidence`, `confidence_band`
- `evidence_json`, `match_method`, `source_freshness`
- `status`: `shadow`, `candidate`, `confirmed`, `rejected`, `expired`, `conflict`
- `reviewed_by`, `reviewed_at`, `review_note`
- `created_at`, `expires_at`

### 7.3 `IdentificationReview`

用途：留下人工確認、否決、修正與模型／provider 品質回饋。

最低欄位：

- `tenant_id`, `company_identification_id`
- `decision`, `corrected_company_name`, `corrected_domain`
- `reason_code`, `note`
- `reviewed_by`, `reviewed_at`

### 7.4 `ContactCandidate`

用途：保存公司中可能相關的公開聯絡窗口；和正式 `Contact` 分開。

最低欄位：

- `id`, `tenant_id`, `company_identification_id`
- `full_name`, `title`, `department`, `seniority`, `location`
- `business_email_encrypted` 或受控保存方式、`email_hash`, `email_masked`
- `email_verification_status`, `verification_provider`, `verified_at`
- `source_provider`, `source_url`／來源證據、`source_freshness`
- `relevance_score`, `relevance_reasons_json`, `confidence`
- `status`: `candidate`, `approved`, `rejected`, `converted`, `expired`, `do_not_contact`
- `converted_contact_id`
- `created_at`, `expires_at`

### 7.5 `ProviderUsage`

用途：管理公司辨識、聯絡人補全及驗證供應商的成本與可靠度。

最低欄位：

- `tenant_id`, `provider`, `operation`
- `request_key`, `request_at`, `response_status`, `latency_ms`
- `units`, `estimated_cost`, `cache_hit`
- `error_class`, `retry_count`
- 不保存不必要的 provider 原始個資 payload；必要資料另做加密和 TTL。

### 7.6 `JourneySnapshot`

用途：將產生外聯當下的旅程與產品興趣固定下來，避免後續事件改變當時判斷。

最低欄位：

- `tenant_id`, `visitor_id`, `company_identification_id`
- `intent_score`, `intent_stage`, `intent_facets_json`
- `top_products_json`, `top_pages_json`, `downloads_json`, `cta_events_json`
- `summary`, `evidence_event_ids_json`
- `generated_at`, `policy_version`

### 7.7 `OutreachMessage`

用途：成為個人化外聯的穩定主記錄。這是補上現況斷點的關鍵模型。

最低欄位：

- `id`, `tenant_id`
- `visitor_id`, `company_identification_id`, `contact_candidate_id`, `contact_id`
- `journey_snapshot_id`
- 可選 `nurture_sequence_id`, `nurture_enrollment_id`, `nurture_outbox_id`
- `purpose`, `channel`, `language`
- `to_email_hash`, `to_email_masked`，必要的受控寄送地址
- `subject_snapshot`, `html_snapshot`, `text_snapshot`
- `personalization_evidence_json`
- `knowledge_version`, `prompt_version`, `policy_version`
- `generation_model`, `generated_at`
- `status`
- `approved_by`, `approved_at`, `approval_note`
- `scheduled_at`, `sent_at`
- `provider`, `provider_message_id`
- `idempotency_key`, `last_error`
- `created_at`, `updated_at`

設計原則：寄送後不得覆寫內容快照；修改應產生新 revision 或新 message。

### 7.8 `OutreachEvent`

用途：將 provider 原始事件正規化並連回 tenant／message。

最低欄位：

- `tenant_id`, `outreach_message_id`
- `email_delivery_event_id`（若來自現有 ledger）
- `event_type`, `provider`, `provider_event_id`
- `occurred_at`, `metadata_json`
- `(provider, provider_event_id)` unique 或等效冪等約束

建議保留 `EmailDeliveryEvent` 作隱私最小化原始帳本，新增 tenant／message 關聯可採擴充欄位或 `OutreachEvent` 映射表；不得只靠收件人 email 反查歸屬。

### 7.9 `InboundReply`

用途：保存對方回覆與 thread 關係。

最低欄位：

- `tenant_id`, `outreach_message_id`, `contact_id`, `contact_candidate_id`
- `provider`, `provider_event_id`, `provider_message_id`, `thread_id`
- `from_email_hash`, `from_email_masked`
- `subject`, 受控正文／摘要、附件 metadata
- `classification`, `classification_confidence`, `classification_reasons_json`
- `status`: `received`, `classified`, `needs_review`, `handed_off`, `closed`
- `received_at`, `processed_at`
- 冪等鍵及原始 payload 的短期／加密保存政策

### 7.10 `SalesHandoff`

用途：把有價值回覆轉為真人可接手的持久任務。

最低欄位：

- `tenant_id`, `inbound_reply_id`, `outreach_message_id`
- `visitor_id`, `company_identification_id`, `contact_id`
- `priority`, `reason`, `summary`
- `owner_id`, `status`: `open`, `accepted`, `in_progress`, `converted_to_rfq`, `closed`
- `due_at`, `accepted_at`, `completed_at`
- `rfq_request_id`, `outcome_note`

### 7.11 `AttributionLink` 或 RFQ 擴充欄位

用途：記錄閉環來源。

至少需能保存：

- `rfq_request_id`
- `visitor_id`, `company_identification_id`
- `outreach_message_id`, `inbound_reply_id`, `sales_handoff_id`
- `attribution_type`: `direct`, `assisted`, `unknown`, `manual`
- `confidence`, `evidence_json`, `created_at`

---

## 8. Feature flags 與啟用階段

現有 catalog 已有 `company_identification`，目前 `configurable: false`、`status: awaiting_provider` 且固定關閉，這符合尚未完成 POC 前的安全狀態。

建議新增或拆分以下 entitlement：

- `company_identification`
- `contact_enrichment`
- `journey_personalization`
- `outreach_review`
- `outreach_send`
- `inbound_reply`
- `sales_handoff`
- `closed_loop_attribution`

每項能力應有 runtime mode，不只 boolean：

```text
OFF
  → SHADOW
  → REVIEW_ONLY
  → APPROVAL_SEND
  → CONTROLLED_AUTO
```

- `OFF`：不呼叫 provider、不產生資料。
- `SHADOW`：背景辨識／評分但不顯示、不聯絡，用於品質驗證。
- `REVIEW_ONLY`：顯示候選與草稿，只能人工確認，不能寄送。
- `APPROVAL_SEND`：每封外聯都必須人工核准後寄送。
- `CONTROLLED_AUTO`：只對符合信心、同意、頻率、品質和租戶政策的案例自動寄送。

不得由 `SHADOW` 直接跳到 `CONTROLLED_AUTO`。

---

## 9. 依現況的實作步驟

### Phase 0：固定產品契約、指標與護欄

#### 目標

在寫 provider runtime 前，先讓「公司」、「聯絡候選」、「訪客本人」、「外聯」、「回覆」的語意及權限不可混淆。

#### Backend

1. 建立本文件所需的狀態 enum／常數與資料保留政策。
2. 在 feature catalog 加入拆分後的核心缺口 flags，全部預設關閉。
3. 定義 tenant policy：可否辨識、可否補全、可否產草稿、可否寄送、每日 quota、quiet hours、允許國家／地區。
4. 定義信任代理和來源 IP 解析規則；淘汰將公開 organization 字串直接等同公司身份的路徑。
5. 定義跨服務 idempotency key 格式與 correlation id。
6. 定義 PII encryption、hash、mask、TTL、刪除與匯出政策。

#### Admin／產品

1. 統一用語：
   - 「推測公司」而非「已辨識訪客公司」。
   - 「公司相關聯絡窗口候選」而非「這位訪客的聯絡人」。
2. 顯示信心、證據、來源時間及資料用途。
3. 在啟用設定中明示 provider、資料類型、保留期與寄送模式。

#### 測試

- Feature 關閉時不得呼叫 provider 或顯示候選。
- 租戶不可讀取他租戶的 observation／candidate／message。
- Forged forwarding headers 不得改變解析結果。
- 私人網段、bot、VPN／hosting 判斷有測試基準。

#### Exit gate

- 產品、法務／隱私、工程共同確認名詞、資料流與預設關閉策略。
- 所有新能力可以由平台管理者和 kill switch 即時關閉。

### Phase 1：公司辨識資料基礎與 Shadow Mode

#### 目標

只完成「可信的公司候選」，不找人、不寄信。

#### Backend

1. 新增 `NetworkObservation`、`CompanyIdentification`、`IdentificationReview`、`ProviderUsage` migrations 與 models。
2. 新增 provider-neutral interface，例如：
   - `identify_company(observation) -> CompanyCandidate[]`
   - `healthcheck()`
   - `estimate_cost()`
3. 先實作 mock adapter 及一個 POC provider adapter；不得把 provider schema 滲入核心模型。
4. 以現有 `OperationalJob` 新增 `company_identify` job handler。
5. 觸發條件只限：
   - 已取得適用 consent。
   - visitor 達設定 intent threshold。
   - IP 不是 private／bot／VPN／proxy／hosting，或依 tenant policy 容許。
   - 相同網路和時間窗沒有有效 cache。
6. 實作 TTL cache、dedupe、quota、retry、backoff、circuit breaker 與 cost guard。
7. 保存 provider 衝突，不用最後寫入者覆蓋其他候選。

#### Admin

1. Shadow report：match rate、high-confidence rate、provider latency、cost、unknown、conflict。
2. Review queue：確認、否決、修正、原因。
3. 訪客旅程暫不對一般租戶顯示公司名稱，直到 Shadow gate 通過。

#### 測試

- Adapter contract tests。
- Cache、quota、timeout、429、5xx、malformed response、重送與 circuit breaker。
- 同一 job 重放不得產生重複 identification。
- Cross-tenant、PII logging 及 provider payload retention tests。

#### Exit gate

- Shadow Mode 至少 30 天或達到預先約定的足夠樣本數。
- 「高信心且被發布的公司候選」人工抽查 precision 至少 90%。
- Match rate 和 precision 分開報告；不得為提高 match rate 降低發布門檻。
- 單次及每租戶成本可預估、可封頂。

### Phase 2：聯絡窗口補全與人工確認

#### 目標

從已確認／高信心公司找出相關公開商務窗口，但不假定其為訪客本人。

#### Backend

1. 新增 `ContactCandidate` model／migration。
2. 建立 contact provider adapter 及 email verification adapter。
3. 新增 `contact_enrich` OperationalJob。
4. 依 tenant ICP／persona 設定職能，例如採購、工程、營運或管理職；不得無限制抓取所有人。
5. 以公司 domain、職稱、部門、地區、產品興趣計算 relevance score。
6. 對 email 執行格式、domain、provider verification；明確區分 verified、risky、catch-all、unknown、invalid。
7. 實作候選 TTL、去重、do-not-contact、source freshness 與轉為 `Contact` 的人工動作。

#### Admin

1. 公司候選詳情與聯絡窗口候選清單。
2. 顯示 relevance 原因、來源、驗證狀態、資料新鮮度。
3. Approve／reject／convert to Contact；拒絕需原因以支援品質回饋。

#### 測試

- 同公司同 email 去重。
- Candidate 不得在未核准時進入一般 nurture auto enrollment。
- Invalid／suppressed／do-not-contact 不得進草稿或寄送。
- Provider 原始個資不應出現在一般 log。

#### Exit gate

- 針對目標 persona 的候選相關度達成內部人工抽查門檻。
- Verified／risky／unknown 狀態能正確阻擋不合格寄送。
- 候選轉 Contact 的來源與決策可完整稽核。

### Phase 3：旅程摘要與個人化草稿（只審核、不寄送）

#### 目標

把現有旅程、產品與知識基礎轉成可審核信件，先驗證內容品質。

#### Backend

1. 新增 `JourneySnapshot` 與 `OutreachMessage`。
2. 建立 `journey_summarize`／`outreach_draft` job handlers。
3. 從 `TrackingEvent` 聚合：
   - 高互動頁面與產品。
   - 下載、比較、CTA、聊天與 RFQ 草稿。
   - 時間衰減、重複訪問與意圖 facets。
4. 建立 evidence pack，只引用已發布內容及有效事件。
5. 產生 subject／HTML／text 快照，保存 knowledge／prompt／policy version。
6. 建立硬性內容檢查：
   - 不虛構價格、規格、交期、客戶關係。
   - 不說「我們看到你本人瀏覽了……」。
   - 不揭露敏感追蹤細節。
   - 每封信只有一個清楚 CTA。
7. 產生後狀態固定為 `draft`／`pending_review`。

#### Admin

1. Review inbox 顯示公司、窗口、旅程摘要、引用事件、產品證據和信件預覽。
2. 支援編輯、核准、拒絕、重新生成；保存人工 edit diff 和理由。
3. 顯示風險提示：身份推測、信箱品質、抑制狀態、內容主張。

#### 測試與評估

- Golden journey cases：同一輸入生成內容必須符合政策與產品事實。
- Unsupported claim rate 必須為 0 才可進寄送階段。
- 租戶語系、產品與知識不得交叉。
- 記錄 approval rate、reject reasons、edit distance、人工處理時間。

#### Exit gate

- 草稿核准率與修改量達到產品團隊設定門檻。
- 所有寄送內容可由 snapshot 還原，不依賴後來被修改的 `NurtureStep`。
- 尚未啟用任何自動寄送。

### Phase 4：受控寄送、追蹤、退訂與抑制

#### 目標

在逐封人工核准模式下寄送，建立完整事件與安全閉環。

#### Backend

1. 將核准後 `OutreachMessage` 轉成 `outreach_send` OperationalJob。
2. 寄送前重新檢查：
   - tenant feature 與全域 kill switch。
   - approval、recipient verification、suppression、do-not-contact。
   - frequency cap、quiet hours、每日 quota。
   - message revision、idempotency key。
3. 使用現有 ESP adapter；保存 provider message id。
4. 擴充 delivery webhook 映射至 tenant／OutreachMessage。
5. 新增 `OutreachEvent` 或等效 FK，支援 delivered／opened／clicked／bounced／complained／unsubscribed。
6. 建立簽名退訂 token 與 tenant／global suppression 政策。
7. Bounce、complaint、unsubscribe 立即停止排程中的後續訊息。
8. `NurtureOutbox` 若繼續使用，需指向 `OutreachMessage`，不可再由 live step 重新渲染已核准信件。

#### Admin

1. 寄送佇列、核准者、預定時間、狀態與事件 timeline。
2. Retry／cancel 必須有權限及稽核；已 sent 不可重送同一 idempotency key。
3. 顯示 bounce／complaint／unsubscribe 原因與停止狀態。

#### 測試

- Webhook signature、replay、out-of-order event、unknown message id。
- 雙重點擊核准、worker crash、provider timeout 不得重複寄送。
- Suppressed recipient 於任何入口都不可寄送。
- Unsubscribe link 和 suppression 端到端測試。

#### Exit gate

- 只開 `APPROVAL_SEND`，不開 `CONTROLLED_AUTO`。
- Delivery ledger 能由任何 message 回查全部事件。
- Bounce、complaint、unsubscribe 率在租戶及全域門檻內。

### Phase 5：Inbound reply 與真人業務接手

#### 目標

收到回覆後能可靠停止自動化、分類並交給真人。

#### Backend

1. 建立 inbound webhook／mailbox adapter 與簽名驗證。
2. 新增 `InboundReply`、`SalesHandoff`。
3. 用 message-id、references、thread id 關聯 `OutreachMessage`；關聯不明的進人工 review。
4. 清理 HTML、限制附件、掃描危險內容；原始 payload 依最短必要 TTL 保存。
5. 先以規則處理 unsubscribe、auto-reply、bounce，再用分類器判斷 positive／question／RFQ／wrong-person／not-now／negative。
6. 任何真人回覆先暫停該聯絡人序列，避免機器繼續追信。
7. Positive／question／RFQ 建立 `SalesHandoff` 與 SLA、owner、通知。
8. 提供一鍵建立／關聯 `RFQRequest`。

#### Admin

1. Reply inbox 和 thread timeline。
2. 顯示原始外聯、旅程摘要、公司與候選來源。
3. Accept、assign、reply externally、create RFQ、wrong person、unsubscribe、close。
4. 所有狀態變更留 audit trail。

#### 測試

- Thread 關聯、重複 webhook、轉寄、auto-reply、out-of-office、多語回覆。
- Prompt injection／惡意 HTML 不得影響後台或 Copilot 權限。
- Reply 後 nurture／outreach 停止。
- Cross-tenant inbound event 不得被錯配。

#### Exit gate

- 有價值回覆能在 SLA 內進入可指派佇列。
- 100% unsubscribe／complaint 正確抑制。
- 不確定分類進人工 review，不自動丟棄。

### Phase 6：RFQ／成交閉環與成果面板

#### 目標

證明北極星帶來可追溯的 RFQ 與成交，而不是只報告寄信數或開信率。

#### Backend

1. 新增 `AttributionLink` 或擴充 RFQ 關聯欄位。
2. 建立 outreach → reply → handoff → RFQ → outcome chain。
3. Attribution 至少分 direct、assisted、unknown、manual。
4. outcome 變更時更新聚合指標，保留原始事件和人工 override。
5. 提供 funnel query／export，所有結果均 tenant scoped。

#### Admin

1. 北極星 funnel：
   - 可追蹤訪客。
   - 高意圖訪客。
   - 公司候選／高信心公司。
   - 合格窗口。
   - 已核准／已寄送。
   - delivered／replied／positive reply。
   - handoff／RFQ／won。
2. 每一步顯示 conversion、drop-off、樣本數、成本與 SLA。
3. 可從成交回查公司辨識證據及所有人工決策。

#### Exit gate

- 至少一個 pilot tenant 完成完整鏈路。
- 指標可由資料庫原始記錄重算。
- 不把沒有因果證據的成交誤標為 AI direct attribution。

### Phase 7：Controlled Auto 與規模化

#### 前提

只有前六階段穩定，才評估有限自動寄送。

#### 啟用條件

- 公司 high-confidence precision 達門檻且持續穩定。
- 聯絡候選 relevance／verification 達門檻。
- Unsupported claim 為 0。
- Bounce／complaint／unsubscribe 低於風險門檻。
- Approval history 顯示某些模板／情境具有穩定低修改率。
- Tenant 明確 opt-in，且適用地區與用途經審查。
- 每租戶／每天／每公司／每聯絡人的頻率與成本上限已生效。

#### Controlled Auto 範圍

- 先只允許白名單 tenant、白名單 persona、白名單模板及高信心案例。
- 保留抽樣人工 review、即時 kill switch 和自動降級回 `APPROVAL_SEND`。
- 任何異常率超標即停，不以重試掩蓋品質問題。

---

## 10. 建議 API 範圍

以下為領域 API 草案，路徑可依現有 v1 router 命名調整。

### Company identification

- `GET /v1/company-identifications`
- `GET /v1/company-identifications/{id}`
- `POST /v1/company-identifications/{id}/review`
- `POST /v1/company-identifications/{id}/recheck`
- `GET /v1/company-identifications/metrics`

### Contact enrichment

- `GET /v1/company-identifications/{id}/contact-candidates`
- `POST /v1/contact-candidates/{id}/approve`
- `POST /v1/contact-candidates/{id}/reject`
- `POST /v1/contact-candidates/{id}/convert-to-contact`
- `POST /v1/contact-candidates/{id}/verify-email`

### Outreach

- `POST /v1/outreach/drafts`
- `GET /v1/outreach/messages`
- `GET /v1/outreach/messages/{id}`
- `POST /v1/outreach/messages/{id}/regenerate`
- `POST /v1/outreach/messages/{id}/approve`
- `POST /v1/outreach/messages/{id}/reject`
- `POST /v1/outreach/messages/{id}/send`
- `POST /v1/outreach/messages/{id}/cancel`
- `GET /v1/outreach/messages/{id}/events`

### Replies and handoff

- `POST /v1/webhooks/{provider}/inbound`
- `GET /v1/replies`
- `GET /v1/replies/{id}`
- `POST /v1/replies/{id}/classify`
- `POST /v1/replies/{id}/handoff`
- `GET /v1/sales-handoffs`
- `POST /v1/sales-handoffs/{id}/accept`
- `POST /v1/sales-handoffs/{id}/assign`
- `POST /v1/sales-handoffs/{id}/convert-to-rfq`
- `POST /v1/sales-handoffs/{id}/close`

### Metrics

- `GET /v1/growth-funnel`
- `GET /v1/growth-funnel/costs`
- `GET /v1/growth-funnel/quality`
- `GET /v1/rfqs/{id}/attribution`

所有清單 API 必須有 tenant scope、分頁、時間範圍及最小必要欄位；敏感 email 只回 masked 值，取得明文寄送地址需受控權限。

---

## 11. 後台介面優先順序

1. **公司辨識 Shadow／Review**：先解決品質，不急著做華麗 profile。
2. **聯絡候選 Review**：來源、職能、信箱品質、approve／reject。
3. **Outreach Review Inbox**：旅程證據、信件快照、編輯、核准與風險提示。
4. **Message Timeline**：draft、approval、send、delivery、reply、suppression。
5. **Reply／Sales Handoff Inbox**：owner、SLA、thread、建立 RFQ。
6. **North Star Funnel**：最後才在資料完整後提供可信的漏斗與成本。

不可先做會暗示「知道訪客本人」的 UI，再補資料與合規；畫面語意本身就是產品風險。

---

## 12. 指標與驗收

### 12.1 觀察與意圖

- Consent 後 tracking coverage。
- 有效 Visitor／Session 比例。
- 事件遺失率、重複率與延遲。
- 高意圖人工合理性抽查。
- 分數原因可解釋率。

### 12.2 公司辨識

- Eligible observation 數。
- Match rate。
- High-confidence publish rate。
- High-confidence precision，目標至少 90%。
- Unknown／conflict／expired 比例。
- Provider latency、error、cache hit、cost per identification。

### 12.3 聯絡窗口

- 每家公司合格候選數。
- Persona relevance 人工通過率。
- Verified／risky／unknown／invalid 比例。
- 候選過期率、重複率、do-not-contact 命中率。
- Candidate → Contact conversion。

### 12.4 草稿與寄送

- Draft approval／reject rate。
- 人工 edit distance 與主要 reject reason。
- Unsupported claim rate：必須為 0。
- Approval turnaround time。
- Send／delivery／open／click；open 只作參考，不作單一意圖依據。
- Bounce、complaint、unsubscribe、suppression。
- 成本／封、成本／有效回覆。

### 12.5 回覆與成交

- Reply rate、positive reply rate、RFQ reply rate。
- Reply → handoff 建立時間。
- Handoff acceptance／first-action SLA。
- Handoff → RFQ conversion。
- RFQ → won conversion、assisted revenue。
- 每個歸因類型的數量與信心。

所有比率必須同時顯示分母與樣本數，避免小樣本誤導。

---

## 13. 安全、隱私與合規最低門檻

- 僅在適用 consent／合法用途和 tenant policy 下進行辨識與外聯。
- 公司候選不等於個人身份；聯絡候選不等於實際訪客。
- 僅使用商務目的所需的最少資料。
- IP、email、provider payload、回覆正文與附件設明確 TTL。
- 敏感欄位加密；查詢和事件使用 hash／masked 值。
- Provider key 只能在 server-side secret store。
- Webhook 必須驗簽、限流、冪等、限制大小並處理 replay。
- 日誌不得寫入完整 email、IP、回覆正文或 provider 原始 PII。
- 提供 unsubscribe、do-not-contact、suppression、資料刪除和匯出流程。
- Complaint／unsubscribe 優先於任何 nurture 或 sales automation。
- 自動生成內容不可宣稱監控個人行為，也不可洩露追蹤細節。
- 每個自動決策保存版本、輸入證據、輸出、人工決策與時間。
- 進入新市場或新增 provider 前，須重新審查適用規範與契約；本文件不替代法律意見。

---

## 14. 測試矩陣

### Unit

- IP／proxy normalization。
- Intent threshold 與 trigger eligibility。
- Confidence band、relevance、verification 與 suppression rules。
- Journey aggregation、evidence selection、content policy checks。
- Reply classification precedence。
- Attribution rules。

### Integration

- Provider adapter success／timeout／429／5xx／malformed／partial data。
- OperationalJob retry、lease、crash recovery、idempotency。
- Draft → approve → send → webhook → reply → handoff → RFQ。
- Nurture 與 OutreachMessage 內容快照一致性。
- Suppression 對 RFQ auto-reply、nurture、outreach 所有寄信入口均生效。

### Security

- Tenant A 不可取得 Tenant B 的公司、候選、信件、事件或回覆。
- SSRF／forged headers／webhook spoofing／replay。
- HTML sanitization、附件限制、prompt injection。
- 權限提升、crafted feature override、未核准寄送。
- Secret／PII log scan。

### Data migration

- Upgrade／downgrade migration。
- 舊 NurtureOutbox 與 provider message id backfill 策略。
- 可重跑 backfill，不重複建 message／event。
- Legacy nullable tenant rows 的處理與隔離。

### E2E

- 匿名高意圖訪客完整走到 RFQ。
- 公司 unknown，不呼叫 contact provider。
- 多家公司衝突進 review。
- 聯絡信箱 invalid／suppressed，無法核准寄送。
- 寄送後 bounce／complaint／unsubscribe。
- Positive reply 建 handoff 和 RFQ。
- Wrong person／not now／auto-reply 的正確處理。

### Production verification

- Synthetic visitor 與 synthetic mailbox smoke test。
- Provider sandbox／測試收件箱。
- Metrics、trace、structured log、alert、dead-letter queue。
- Kill switch 演練和 provider outage 降級。

---

## 15. 類別四的安全刪除流程

任何可刪除候選都必須依序處理：

1. **建立清單**：route、service、model、migration、UI、feature flag、env、tests、docs。
2. **依賴稽核**：使用 `rg`、route registry、imports、bundle、DB FK、job type、telemetry 查找引用。
3. **關閉入口**：feature flag 預設 off，移除導航及新租戶入口。
4. **觀察期**：至少 30 天；高風險或客戶可見能力建議 60 天。
5. **資料處置**：匯出、封存、TTL、回復方案；不得直接丟失客戶資料。
6. **API deprecation**：若曾公開使用，先回應 deprecation 訊息並通知使用者。
7. **移除執行碼**：先 UI／worker／route，再清理服務與設定。
8. **Migration 原則**：保留既有 migration 歷史；新增向前 migration 移除資料表／欄位，不修改已執行版本。
9. **驗證**：API、web、admin type-check、相關測試、啟動與 migration smoke test。
10. **回復窗口**：保留可回復 branch／tag、資料備份與決策記錄。

刪除判斷應以使用證據和依賴為準，不能只因為目前不是北極星就刪除。

---

## 16. 建議執行順序與依賴

```text
Phase 0 契約／護欄
  ↓
Phase 1 公司辨識 Shadow
  ↓ precision gate
Phase 2 聯絡候選與驗證
  ↓ relevance/verification gate
Phase 3 旅程個人化草稿
  ↓ content quality gate
Phase 4 人工核准寄送與事件
  ↓ delivery/safety gate
Phase 5 Inbound reply 與真人接手
  ↓ SLA/handling gate
Phase 6 RFQ／成交歸因
  ↓ closed-loop evidence
Phase 7 有限 Controlled Auto
```

可平行進行但不可提前啟用的工作：

- 在 Phase 1 同時設計 `OutreachMessage` migration，但不能寄送。
- 在 Phase 2 同時建立 reply provider sandbox，但不能對外開放。
- 在 Phase 3 同時準備 dashboard query，但必須等事件鏈完整才呈現正式成效。
- 類別四的 telemetry／依賴稽核可和核心開發平行進行，實際刪除需單獨變更集。

---

## 17. 第一批工程 Backlog

### P0：先做

- [ ] 將本文件的北極星與四分類加入正式產品決策記錄。
- [ ] 定義 company／contact candidate／outreach／reply／handoff 的狀態機。
- [ ] 拆分 feature flags 並保持預設 OFF。
- [ ] 建立 `NetworkObservation`、`CompanyIdentification`、`IdentificationReview`、`ProviderUsage` models／migrations。
- [ ] 建立 provider adapter contract、mock adapter、OperationalJob handler。
- [ ] 完成 trusted proxy／IP eligibility／privacy tests。
- [ ] 完成 Shadow metrics 與人工 review queue。

### P1：公司辨識 Gate 通過後

- [ ] 建立 `ContactCandidate` 與 verification adapter。
- [ ] 建立 persona／relevance policy 與候選 review UI。
- [ ] 建立 `JourneySnapshot` 和 evidence pack。
- [ ] 建立不可變 `OutreachMessage` 快照。
- [ ] 將 Copilot／Nurture 草稿改為產生或連結 `OutreachMessage`。
- [ ] 建立內容事實檢查與 draft evaluation suite。

### P2：草稿 Gate 通過後

- [ ] 建立 `OutreachEvent`／delivery mapping。
- [ ] 完成退訂、tenant／global suppression 和 frequency cap。
- [ ] 建立人工核准寄送 E2E。
- [ ] 建立 inbound webhook、`InboundReply`、reply classification。
- [ ] 建立 `SalesHandoff`、通知、SLA 和一鍵轉 RFQ。

### P3：閉環與規模化

- [ ] 建立 AttributionLink／RFQ 擴充。
- [ ] 建立 North Star funnel、成本與品質 dashboard。
- [ ] 完成 pilot tenant 端到端驗收。
- [ ] 定義 Controlled Auto 白名單與自動降級門檻。
- [ ] 完成類別四候選的 30／60 天使用稽核與個別刪除決策。

---

## 18. 完成定義（Definition of Done）

ForgeBase 的北極星能力只有在以下條件全部成立時，才可稱為「完整交付」：

- 匿名訪客在適用同意下被追蹤並獲得可解釋意圖分數。
- 達門檻的訪客可產生有證據與信心的公司候選。
- 高信心公司辨識 precision 達至少 90%，且 match rate 分開呈現。
- 能找到相關但不冒充訪客本人的聯絡窗口候選。
- 寄送地址通過政策、驗證、抑制及人工／自動化門檻。
- 個人化信件只使用固定旅程快照及已發布知識，無不實主張。
- 每封信有不可變內容快照、核准者、寄送冪等鍵及 provider message id。
- Delivery、bounce、complaint、unsubscribe、reply 均可回連同一訊息及 tenant。
- 對方回覆會停止不當自動化，並進入可指派的真人接手流程。
- 真人可從回覆建立 RFQ，RFQ outcome 可回溯整條證據鏈。
- 有 production monitoring、dead-letter、kill switch、成本上限與資料刪除流程。
- 端到端、安全、多租戶、webhook replay、migration 和 provider outage 測試通過。

若只做到公司名稱、寄出一封信或顯示開信率，仍不能稱為完成北極星。

---

## 19. 當前決策記錄

### DR-NS-001：北極星定義

採用「匿名訪客 → 行為追蹤 → 意圖評分 → 推測公司 → 聯絡窗口 → 個人化信件 → 寄送追蹤 → 回覆 → 真人接手 → RFQ／成交」作為產品及工程優先級基準。

### DR-NS-002：公司辨識等能力的分類

公司辨識、聯絡人補全、個人化外聯、回覆與接手屬「核心未完善」，不得再以實驗性為由排除產品主線。

### DR-NS-003：ML 的定位

意圖評分為核心；規則與 facets 是現階段主路徑。ML runtime／UI 可維持預設關閉，待資料、標籤、評估與 owner 成熟後再決定是否上線。

### DR-NS-004：外聯的啟用順序

外聯依 OFF → SHADOW → REVIEW_ONLY → APPROVAL_SEND → CONTROLLED_AUTO 漸進，不允許未經品質與合規 gate 直接自動寄送。

### DR-NS-005：現有寄信元件的處置

保留 Nurture、ESP event、suppression 和 OperationalJob；新增穩定 `OutreachMessage`、回覆與接手領域模型，避免重建已存在的可靠能力。

### DR-NS-006：刪除原則

刪除的是無使用、無依賴或不安全的實作，不刪除北極星產品能力；任何刪除都需停用、觀察、資料處置、向前 migration 與回復方案。

### DR-NS-007：A／B 的 Build vs. Buy 邊界

ForgeBase 自建匿名旅程、意圖、觸發、信心、證據、Persona 排序、個人化、寄送、回覆、RFQ 與歸因；全球 IP／公司、商務聯絡人及深度 Email 驗證資料採購自可替換的外部供應商。不得把一般自用 API 帳號直接用於多租戶下游展示，必須取得適用的 OEM／Reseller／Solution Provider 書面權利。

### DR-NS-008：供應商中立與暫定 POC 組合

正式架構不依賴 HubSpot 或任何單一 CRM。A 暫以 IPinfo 作網路品質過濾，Leadfeeder 與 People Data Labs 作公司辨識 POC；B 暫以 Apollo Data Reseller 與 People Data Labs 作聯絡窗口 POC，Hunter 作 Email 驗證候選。這是 POC 名單，不是正式採購結論；最終選擇必須通過資料品質、APAC 表現、單位經濟、合規及下游授權 Gate。

---

## 20. 現況證據索引

主要現有程式碼位置：

- `api/app/models/visitor.py`
- `api/app/models/tracking_event.py`
- `api/app/models/tracking_session.py`
- `api/app/models/contact.py`
- `api/app/models/rfq_request.py`
- `api/app/models/rfq_event.py`
- `api/app/models/rfq_note.py`
- `api/app/models/nurture.py`
- `api/app/models/email_delivery.py`
- `api/app/models/operational_job.py`
- `api/app/services/capability_access.py`（2026-08-27 已由舊 subscription 語意重構為單一產品能力治理）
- `api/app/services/operational_outbox.py`
- `api/app/services/email_governance.py`
- `api/app/services/ml_intent.py`
- `api/app/services/copilot/action_tools.py`
- `api/app/api/v1/endpoints/events.py`
- `api/app/api/v1/endpoints/visitors.py`
- `api/app/api/v1/endpoints/nurture.py`
- `api/app/api/v1/endpoints/webhooks.py`
- `api/app/api/v1/endpoints/rfqs.py`
- `api/app/api/v1/endpoints/esp.py`

2026-08-26 稽核時的驗證摘要：

- API 全測試收集 226 項：156 passed、70 skipped；skipped 主要因執行環境未設定 OS `DATABASE_URL`。
- 北極星相關第二輪測試：53 passed、3 skipped。
- `web` TypeScript type-check 通過。
- `admin` TypeScript type-check 通過。

上述結果證明現有前後段基礎可重用，但不能替代尚未存在的公司辨識、候選聯絡人、外聯訊息快照、inbound reply、handoff 及閉環歸因實作。

---

## 21. 下一次逐項討論順序

建議依下列順序逐項定案，避免先討論 UI 或 provider 名稱而失去產品主線：

1. 確認四分類清單是否有需要調整的功能。
2. 確認 Phase 0 的語意、資料使用政策與啟用模式。
3. 定案公司辨識 provider POC 和 Shadow Mode 樣本／成本門檻。
4. 定案目標公司與聯絡 persona。
5. 定案個人化信件的內容政策、審核責任與語氣。
6. 定案寄送 provider、退訂、頻率及租戶策略。
7. 定案 inbound reply mailbox 和真人接手 SLA。
8. 定案 RFQ／成交歸因及 North Star dashboard。
9. 最後審查類別四候選，逐項決定保留、停用或刪除。

---

## 22. Build vs. Buy 與供應商選擇策略

### 22.1 決策摘要

ForgeBase 足以自建 A、B 的產品判斷與轉換引擎，但不應在現階段全自建全球公司及聯絡人資料庫。

```text
ForgeBase 自建
  ├─ 匿名訪客與旅程
  ├─ 意圖與觸發條件
  ├─ 公司辨識信心、證據與人工回饋
  ├─ Persona／窗口相關度
  ├─ 個人化內容與審核
  ├─ 寄送、回覆與真人接手
  └─ RFQ／成交歸因

外部資料供應商
  ├─ IP／ASN／VPN／Proxy／Hosting 情報
  ├─ IP 對應公司候選
  ├─ 公司基本資料
  ├─ 商務聯絡窗口候選
  └─ Email 查找與深度驗證
```

外部供應商只提供可替換的候選資料，不擁有 ForgeBase 的北極星流程，也不直接決定是否辨識、聯絡、寄送或歸因。

### 22.2 自建與採購邊界

| 能力 | 決策 | 原因 |
|---|---|---|
| 匿名 Visitor／Session | ForgeBase 自建 | 已有正式模型與第一方旅程 |
| TrackingEvent 與內容興趣 | ForgeBase 自建 | 是個人化及歸因的第一方核心資料 |
| 意圖評分與 facets | ForgeBase 自建 | 必須依租戶產品及轉換結果持續調整 |
| 何時觸發公司辨識 | ForgeBase 自建 | 控制 consent、成本、品質和頻率 |
| Trusted proxy／IP 正規化 | ForgeBase 自建 | 屬安全邊界，不能交由結果供應商決定 |
| ASN／VPN／Proxy／Hosting 情報 | 外部資料＋ForgeBase 規則 | 全球網路情報需持續更新 |
| 全球 IP → 公司候選 | 外部資料 | 需要長期維護企業網段與公司映射 |
| 公司信心、證據、衝突與 Review | ForgeBase 自建 | 是產品可信度與可解釋性的核心 |
| ICP／Persona／窗口相關度 | ForgeBase 自建 | 必須結合租戶產品及訪客旅程 |
| 全球商務聯絡人候選 | 外部資料 | 需要持續維護任職、職稱、來源與 opt-out |
| Candidate → Contact 審核 | ForgeBase 自建 | 決定資料是否能進正式工作流程 |
| Email 格式、domain、MX、suppression | ForgeBase 自建 | 基本安全與治理能力 |
| Catch-all／Mailbox 深度驗證 | 外部服務 | 自建大量 SMTP probe 的可靠度和聲譽成本不合理 |
| 個人化信件與事實約束 | ForgeBase 自建 | 是第一方旅程與產品知識的差異化能力 |
| 寄送、回覆、Handoff、RFQ | ForgeBase 自建 | 北極星閉環不可交由 CRM 或資料商控制 |
| CRM 同步 | 選配整合 | HubSpot、Salesforce 或其他 CRM 均不可成為必要依賴 |

### 22.3 為什麼不全自建公司資料

自行撰寫 IP resolver 並不等於擁有可用的公司辨識能力。若要全自建，還必須長期維護：

- IPv4／IPv6 網段、ASN 與企業關係。
- ISP、VPN、Proxy、Tor、雲端主機、行動網路及共享網路分類。
- 公司搬遷、改名、合併、網域及網段變更。
- 遠端工作、企業 VPN 和共享辦公室造成的錯配。
- 不同國家、產業和公司規模的辨識覆蓋。
- 人工真值、錯誤修正、資料更新及全球 opt-out／刪除要求。

只用 ASN organization、WHOIS 或 reverse DNS，容易把訪客誤判為 ISP、AWS、Cloudflare、VPN 或網路代管商。ForgeBase 應自建信任鏈、過濾、信心和回饋，不應把基礎 organization 字串包裝成確定公司身份。

### 22.4 為什麼不全自建聯絡人資料

自行爬取公開頁面或猜測 Email 不能形成可靠產品。全自建還需要處理：

- 全球員工任職、轉職、離職、職稱和部門變動。
- 公司、法人、品牌和 domain 的關聯。
- 商務 Email 來源、驗證、過期與 catch-all。
- 資料來源條款、保存期限、opt-out、刪除及跨境處理。
- 台灣、日本、歐美等不同市場的資料覆蓋與語系。
- 持續反退信、申訴、錯誤窗口和資料品質回饋。

ForgeBase 應自建「誰與此次商機最相關」的判斷；外部供應商負責提供「這家公司目前有哪些商務窗口候選」。

### 22.5 暫定供應商架構

| 層級 | 主要 POC 候選 | 對照／備援 | 在 ForgeBase 的用途 |
|---|---|---|---|
| 網路品質 | IPinfo | 可由公司辨識商的 privacy flags 補充 | ASN、VPN、Proxy、Hosting、ISP 過濾，不直接作最終公司身份 |
| A 公司辨識 | Leadfeeder API | People Data Labs IP Enrichment | IP → 公司候選、公司資料、信心與來源比較 |
| B 聯絡窗口 | Apollo Data Reseller API | People Data Labs Person Search | 依公司、部門、職稱、資歷與地區尋找候選 |
| Email 查找／驗證 | Hunter API | Apollo／PDL 既有 Email 結果加內部規則 | Finder、Verifier、寄送前品質 Gate |
| CRM | 不指定 | HubSpot、Salesforce、其他 CRM | 選配同步，不承擔 ForgeBase 北極星主流程 |

#### 官方能力依據

- [Leadfeeder API](https://docs.leadfeeder.com/api/public) 提供公司、聯絡人、網站訪客、IP enrichment 與 workflow 資料存取，適合作 A 的專用 POC。
- [People Data Labs IP Enrichment API](https://docs.peopledatalabs.com/docs/reference-ip-enrichment-api) 可由 IP 查詢公司相關資料；其 Person／Company／IP API 採 credit 計價，適合做 API 型對照測試。[PDL Pricing & Credits](https://support.peopledatalabs.com/hc/en-us/articles/25794271805211-Pricing-credits)
- [IPinfo API](https://ipinfo.io/developers/ipinfo-api) 提供 ASN、匿名化、VPN、Proxy、Hosting、Mobile 等網路情報，定位為 eligibility／風險過濾，而非唯一公司真值。
- [Apollo API](https://docs.apollo.io/) 支援 People／Organization Search、Enrichment 與 Email 等資料；若向非 Apollo 使用者展示或嵌入資料，必須使用適用的客製或 Reseller 合約。[Apollo Data Reseller](https://www.apollo.io/partners/api-reseller)
- [Hunter API](https://hunter.io/api) 提供 Domain Search、Email Finder 及 Email Verifier，適合作查找／驗證層，不單獨負責 Persona 排序。

這些名稱是截至 2026-08-26 的 POC 候選，不是永久技術依賴或已完成的採購決定。

### 22.6 為什麼 HubSpot 不作必要依賴

HubSpot 可作選配 CRM、Buyer Intent 或 enrichment 整合，但不作 ForgeBase A、B 的唯一核心來源，原因如下：

- 會和 ForgeBase 第一方 tracking／journey 產生重疊。
- 每個 ForgeBase 租戶可能需要自己的 HubSpot 方案、權限和 credits。
- 使用其他 CRM 或完全沒有 CRM 的客戶會被排除。
- Contact enrichment 和「由公司發現 net-new 相關窗口」不是完全相同的能力。
- 北極星資料、寄送和歸因若只存在 HubSpot，ForgeBase 將失去產品控制與可替換性。

正確定位：HubSpot 可以是 CRM destination、同步來源或個別租戶選用的外部能力，不是系統成立的前提。

### 22.7 OEM／Reseller／資料權利 Gate

技術 API 可呼叫，不代表有權把資料提供給 ForgeBase 的多租戶客戶。任何正式 POC 升級為 production 前，必須取得書面確認：

- 是否允許嵌入 SaaS 產品並向下游客戶顯示。
- 是否需要 OEM、Reseller、Solution Provider 或 Data License。
- 每個 tenant 是否要有獨立帳號／OAuth，或可由 ForgeBase 統一採購。
- 可顯示哪些欄位、可保存多久、是否只能顯示給一名 End User。
- 能否保存衍生分數、候選理由、人工決策及歷史快照。
- 合約終止後哪些資料必須刪除、哪些衍生資料可保留。
- 是否允許把資料用於 AI prompt、ranking、evaluation 或模型訓練。
- 是否能將結果同步到客戶 CRM、Email service 或其他處理者。
- DPA、SCC／跨境傳輸、subprocessor、資料落地與 breach 通知。
- Data subject request、opt-out、suppression 及刪除同步方式。
- Rate limit、超額費率、最低承諾、credits 到期及價格調整。
- SLA、版本變更、API deprecation、資料正確性及責任限制。

[People Data Labs 的服務合約](https://privacy.peopledatalabs.com/policies?name=services-subscription-agreement)允許在特定 Data License 下向自有產品的 End Users 顯示資料，但同時限制轉售、保存和競爭性用途；實際權利必須寫入 ForgeBase Order Form。Apollo 也明確要求，向非 Apollo 使用者分享、展示或轉售資料需要客製合約，而非一般 API 帳號。

任何未通過本 Gate 的供應商，即使技術與價格評分最高，也不得成為 production 供應商。

### 22.8 A 公司辨識 POC 設計

#### 測試資料

- 使用已取得適用同意、可建立人工真值的第一方樣本。
- 優先涵蓋台灣、日本、北美及歐洲目標客群。
- 分開企業辦公網路、遠端工作、VPN、行動網路、ISP、Hosting 和 Bot。
- 不用單一市場或 ForgeBase 自己辦公室的結果代表整體品質。
- 真值可來自已知測試公司、後續表單自我識別、人工確認或既有客戶對照；不能拿另一家供應商結果當唯一真值。

#### 同批平行測試

```text
相同 eligible IP／NetworkObservation
  ├─ IPinfo eligibility／risk
  ├─ Leadfeeder company candidate
  └─ PDL company candidate
       ↓
正規化 domain／company
       ↓
人工 blind review
       ↓
Precision、Coverage、Conflict、Cost、Latency
```

#### A 評分權重

| 指標 | 權重 | 說明 |
|---|---:|---|
| 高信心公司 Precision | 35% | 發布的公司候選是否正確；最低門檻 90% |
| Eligible traffic Coverage | 20% | 只計可合理辨識的企業流量，不含 ISP／VPN 等排除流量 |
| 台灣、日本及目標市場表現 | 15% | 不能以美國資料表現代替 ForgeBase 市場 |
| OEM／隱私／下游資料權利 | 15% | 必須通過，否則直接淘汰 |
| 每個正確公司成本 | 10% | 不是每 API call 成本，而是每個正確可發布結果成本 |
| API、延遲、失敗與可觀測性 | 5% | 包含 bulk、rate limit、retry、版本和 support |

#### A 硬性 Gate

- 高信心 Precision 至少 90%。
- Match rate 與 precision 分開呈現。
- VPN／ISP／Hosting 不得為追求 coverage 被包裝成公司。
- 支援 tenant quota、cache、TTL、重試與刪除。
- OEM／下游展示權利通過。

### 22.9 B 聯絡窗口 POC 設計

#### 測試資料

- 只從已確認或 A 高信心公司開始。
- 每個租戶先定義 ICP、目標部門、職稱、seniority、地區及排除條件。
- 台灣、日本、北美及歐洲分開計算覆蓋與品質。
- 人工 reviewer 不先知道供應商來源，減少品牌偏見。

#### 同批平行測試

```text
同一批 confirmed company domain＋Persona policy
  ├─ Apollo People／Organization Search
  └─ PDL Person Search
       ↓
ForgeBase relevance ranking
       ↓
Hunter／供應商 Email verification
       ↓
人工 approve／reject
       ↓
Relevance、Verified Email、Freshness、Cost
```

#### B 評分權重

| 指標 | 權重 | 說明 |
|---|---:|---|
| Persona／職能相關度 | 25% | 是否真的是此次產品商機的合理窗口 |
| Verified business email | 25% | 可寄送、非無效、非個人信箱，狀態可解釋 |
| 台灣、日本及目標市場覆蓋 | 20% | 需分市場報告，不只看全球總筆數 |
| OEM／資料保存與展示權利 | 15% | 必須通過，否則直接淘汰 |
| 每位人工核准窗口成本 | 10% | 包含 search、reveal、enrich、verify 全部成本 |
| API、資料新鮮度與刪除能力 | 5% | 包含 source freshness、opt-out、rate limit |

#### B 硬性 Gate

- Candidate 必須保留來源、新鮮度、relevance reason 和 verification status。
- 不得把候選窗口宣稱為實際匿名訪客。
- Invalid、suppressed、do-not-contact 不得進入外聯。
- 未經核准不得自動轉成正式 `Contact`。
- OEM／下游展示與外聯用途權利通過。

### 22.10 單位經濟計算

不得只比較月費或單次 API credit。正式決策使用：

```text
A 每個正確公司成本
= 公司辨識費＋網路過濾費＋無效查詢成本
  ÷ 人工確認後可發布的正確公司數

B 每個核准窗口成本
= 公司查詢＋People Search＋Email Reveal＋Verification
  ÷ 人工核准且可聯絡的窗口數

每個有效回覆成本
= A＋B＋草稿＋寄送＋人工審核成本
  ÷ 有效真人回覆數

每個 RFQ／成交成本
= 整條北極星成本
  ÷ 可合理歸因的 RFQ／Won 數
```

Provider usage 必須以 tenant、operation、cache hit、結果狀態和 estimated cost 記錄，才能在正式環境持續比較供應商，而不是只在採購前做一次 POC。

### 22.11 正式環境的供應商數量

POC 可平行測試多家，但正式第一版預計收斂為：

```text
1 家主要公司辨識供應商
＋ 1 家網路品質來源（可由主要供應商兼任）
＋ 1 家主要聯絡資料供應商
＋ 1 家 Email 驗證供應商（可由聯絡供應商兼任）
```

不建議為了理論上的 fallback 在早期同時長期付費五家。只有在以下情況加入第二 production provider：

- 主要供應商在重要市場有明確覆蓋缺口。
- 第二來源能顯著提高 precision／verified email，而不是只增加重複資料。
- Outage 造成的收入風險高於第二供應商成本。
- 合約允許正規化、比較與保存必要衍生結果。

### 22.12 ForgeBase 的自有資料飛輪

外部供應商擁有廣泛資料，但不擁有 ForgeBase 每個租戶的第一方產品旅程與成交結果。真正的長期優勢來自：

```text
外部公司／聯絡候選
  → ForgeBase 旅程與意圖排序
  → 人工確認／否決／修正
  → 個人化外聯與人工修改
  → Delivered／Reply／Positive Reply
  → 真人 Handoff
  → RFQ／Won／Lost
  → 回饋公司信心、Persona、內容與觸發策略
```

ForgeBase 應保存的自有衍生資料：

- 哪類訪客事件對特定產品最有商機價值。
- 哪種公司候選在各市場最常被確認或否決。
- 哪些 Persona／職稱被業務接受並產生正向回覆。
- 哪些產品證據、CTA 和信件內容被人工保留或刪改。
- 哪些外聯形成 RFQ、成交或錯誤窗口。
- 各 provider 在市場、公司規模及產業的實際品質和成本。

不得把供應商原始資料直接拿來訓練或建立競爭性資料產品，除非合約明確允許。優先累積 ForgeBase 自己的事件、人工決策、衍生分數與成果標籤。

### 22.13 最終選擇規則

目前已定案的是架構和決策方法，不是供應商品牌。最終選擇依下列順序：

1. OEM／Reseller／Solution Provider、資料保留與外聯用途合法可行。
2. ForgeBase 實際目標市場的 blind POC 品質通過。
3. A 高信心 precision、B persona relevance／verified email 通過硬性 Gate。
4. 單位經濟可被產品售價和 tenant quota 支撐。
5. API、刪除、觀測、支援與故障模式可投入 production。
6. 才比較開發便利、UI 完整或品牌知名度。

任何供應商若未通過前四項，即使試用介面最好或資料庫宣稱最大，也不應成為 ForgeBase 的正式依賴。
