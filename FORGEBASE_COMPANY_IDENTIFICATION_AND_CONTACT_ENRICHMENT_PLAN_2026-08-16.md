# ForgeBase 公司辨識與相關聯絡人候選方案

**文件日期**：2026-08-16\
**文件狀態**：架構、接洽時點與測試方向均已確認；待第一階段上線、供應商資格確認與 Shadow Mode 實測\
**目前優先序**：第二優先（正式外部測試安全與觀測封板之後）\
**對應功能模組**：模組 10「IP／公司辨識與聯絡人 enrichment」\
**目前模組完整度基準**：15%（依 `FORGEBASE_FUNCTION_MODULE_COMPLETENESS_AUDIT_2026-08-15.md`）

> 名稱說明：本文件的「第二優先」是 2026-08-16 起的下一階段執行排序。舊版完整度稽核曾將同一能力列為「第四優先且擱置」，兩者指的是不同時間點的工作排序，不是不同功能。

---

## 一、決策摘要

ForgeBase 採用以下產品與技術方向：

> ForgeBase 自有訪客追蹤與意圖核心\
> ＋ IP／網路品質分類\
> ＋ 可替換的企業辨識供應商\
> ＋ 依已辨識企業搜尋相關聯絡人候選\
> ＋ 多租戶用量、成本、資料來源與信心治理。

這是目前最適合 ForgeBase 的架構方向，但主供應商不能在實測前預先認定。最終選擇必須同時通過：

1. 多租戶 SaaS／白標／終端客戶展示授權。
2. 30 天真實流量 Shadow Mode 的準確率與覆蓋率門檻。
3. 成本、SLA、資料保存、刪除及退出條款。
4. 台灣、亞洲、歐洲、北美等目標市場的分區結果。

第一輪候選池如下。候選池不是預先承諾全部購買；每個階段可保留 2～3 個選項接洽或自測，再依授權、準確率、區域覆蓋與成本淘汰：

| 能力 | 第一輪候選 | 定位 |
|---|---|---|
| 網路品質與排除 | IPinfo；IP2Location 為候補 | 分類 ASN、ISP、VPN、Proxy、Hosting 等，不直接認定公司 |
| 公司辨識 | People Data Labs、Albacross、Snitcher IP-to-Company | 並行競測的主要 Adapter；優先保留 ForgeBase 自有追蹤 |
| 進階白標／辨識率對照 | Snitcher Radar | 比較 session／fingerprinting 能否顯著提高 match rate；不預設取代 ForgeBase 自有追蹤核心 |
| 聯絡人候選搜尋 | People Data Labs、Hunter Domain Search | PDL 作結構化 Persona 主測；Hunter 作網域聯絡窗口對照與補找 |
| Email 驗證 | Hunter | 驗證候選企業 Email；不得把驗證結果冒充訪客本人身份 |
| 外部效果基準 | Leadfeeder／Dealfront、Lead Forensics | 人工或商務 POC 比較；未取得 OEM 權利前不作核心依賴 |
| Waterfall 實驗 | Clay | 只用於短期資料源驗證，不作正式執行核心 |
| 人物級訪客辨識 | 不啟用 | RB2B、Vector 等不納入第一版 |
| 自動外聯 | 不啟用 | 本階段不得自動寄信或建立已確認 Lead |

### 已確認的接洽時點

供應商接洽不在產品仍只有概念時進行，也不延後到公司辨識已全部完成後才進行。正式時點為：

> ForgeBase 第一階段已公開上線且可操作，NorthForge 參考網站可承接真實流量，供應商中立的 Adapter／資料模型／Shadow Mode 底層已就緒，但尚未綁定單一供應商。

採此時點的原因：

- 供應商可以直接查看已上線產品、後台與參考網站。
- ForgeBase 能提出具體 POC 網站、期間、事件量與未來租戶模式。
- 不會在產品尚未成形時只靠概念詢價。
- 不會在未確認授權與 API 前，先寫死特定供應商實作。
- 能以多家並行候選維持技術替換能力與議價空間。

第一階段上線不代表公司辨識已完成；它是開始接洽、取得測試額度與啟動供應商 Adapter 的前置門檻。

---

## 二、產品承諾與正確資料語意

ForgeBase 要實現的核心承諾是：

> 從匿名訪客行為與網路訊號推測可能所屬企業，再依該企業搜尋最相關的公開商務聯絡人候選。

ForgeBase **不承諾**：

- 確認某位自然人曾造訪網站。
- 找到的聯絡人就是當初進站者。
- 每次訪問都能辨識公司。
- 辨識出的公司或聯絡人已經是 Lead。
- 自動寄信後一定會收到回覆或 RFQ。

資料關係必須表達為：

```text
匿名訪客／工作階段
    ↓ 根據 IP、網路與供應商證據推測
企業候選
    ↓ 根據公司、產業、職務與地區搜尋
相關聯絡人候選
```

禁止表達為：

```text
匿名訪客 IP → 已確認公司 → 某位聯絡人就是進站本人
```

### 名詞定義

| 名稱 | 定義 | 是否為 Lead |
|---|---|---:|
| 匿名訪客 | 尚未主動提交身分的網站訪客 | 否 |
| 企業候選 | 供應商根據 IP／網路訊號推測的可能企業 | 否 |
| 高意圖企業 | 行為分數達門檻且具有可信企業辨識結果的 Account signal | 否 |
| 相關聯絡人候選 | 依企業、職務與地區找到的可能商務窗口 | 否 |
| Inbound Lead | 主動提交 RFQ、表單或明確聯絡需求者 | 是 |
| Outbound Reply | 經合法且核准的外聯後主動回覆者 | 可進一步判定 |
| Qualified Lead | 經人工確認需求、適配性與後續處理資格者 | 是 |

因此，不得按「辨識出的聯絡人數」宣稱產生 Leads，也不應直接按此數量收取成功 Lead 費。

---

## 三、現況與必要修正

目前 ForgeBase 已具備第一方訪客追蹤、工作階段、事件、意圖分數、分群及高關注名單基礎，但公司辨識仍不是成熟產品能力。

目前主要缺口：

1. `api/app/services/ip_resolver.py` 使用基礎 IP 查詢結果，並可能從 `org` 推導 `company_name`。
2. `org` 多半代表 ISP、ASN 或網路營運者，不等於訪客任職公司。
3. 尚無獨立的公司辨識證據模型、provider abstraction、信心等級、到期時間與人工覆核狀態。
4. 尚無正式的聯絡人候選來源、Email 驗證狀態與「非進站本人」資料界線。
5. 尚無供應商使用量帳本、租戶額度、成本熔斷及查詢快取。

在任何公司辨識結果對外顯示前，必須先停止把基礎 IP `org` 直接寫成「已辨識公司」。既有欄位若需暫時保留，只能以 `network_owner` 或「網路組織」語意呈現。

---

## 四、目標架構

```text
第一方網站事件
    ↓
ForgeBase Visitor／Session／Intent Score
    ↓
本地快取與查詢去重
    ↓
網路分類：ASN／ISP／VPN／Proxy／Hosting／Bot
    ↓ 僅合格流量
Company Identification Provider Adapter
    ↓
統一公司候選、來源、信心與證據
    ↓ 達到顯示／意圖門檻
Contact Candidate Search
    ↓
企業 Email 補找與驗證
    ↓
後台人工確認、否決、標註與後續處理
```

### 核心設計原則

- 第一方事件、意圖分數與租戶資料歸 ForgeBase 管理。
- 所有供應商呼叫由後端非同步執行；前端不得持有供應商金鑰。
- 供應商結果統一正規化，UI 不直接綁定任何供應商格式。
- 同一 IP、網段、公司或網域在 TTL 內不得重複付費查詢。
- 只有合格網路流量才進入付費公司辨識。
- 只有高意圖且達信心門檻的企業才搜尋聯絡人。
- 所有資料都必須保存 tenant、site、provider、confidence、取得時間與到期時間。
- 供應商故障不得影響公開網站、RFQ 或既有訪客追蹤。

---

## 五、Provider Adapter

建議介面：

```text
CompanyIdentificationProvider
├── PDLProvider
├── AlbacrossProvider
├── SnitcherIpToCompanyProvider
├── SnitcherRadarProvider（進階 POC／OEM 對照）
└── FutureProvider
```

Adapter 最低責任：

- 輸入標準化 IP、網站、租戶與請求追蹤 ID。
- 回傳統一公司候選格式。
- 保留原始 provider response 的安全摘要或可稽核參照。
- 對 timeout、rate limit、無匹配、低信心與服務失敗做明確區分。
- 回報查詢成本、credits、cache hit 與延遲。
- 支援 feature flag、Shadow Mode、熔斷與 provider 切換。

禁止由 Adapter 直接：

- 建立 Lead。
- 改寫 RFQ。
- 觸發外寄。
- 將聯絡人綁定為特定 visitor 身分。
- 未經門檻與覆核直接在客戶後台宣稱「已確認」。

---

## 六、建議資料模型

### 1. NetworkObservation

保存網路事實，不代表企業身分：

- tenant_id、site_id、visitor_id／session_id
- IP 的安全化參照或加密值
- ASN、network owner、ISP
- 國家、區域、城市
- residential／business／mobile／hosting
- VPN／Proxy／Tor／Relay／Bot
- provider、observed_at、expires_at

### 2. CompanyIdentification

保存公司推測及證據：

- normalized company name
- normalized domain
- country／location
- industry、employee range、revenue range
- provider、provider record ID
- provider confidence、ForgeBase normalized confidence
- evidence summary
- status：possible／high_confidence／confirmed／rejected／expired
- identified_at、reviewed_at、expires_at
- reviewer、rejection reason

### 3. ContactCandidate

保存公司相關聯絡人候選：

- company_identification_id
- full name、title、department、seniority、location
- business email、email verification status
- provider、source timestamp、expires_at
- relevance score
- status：suggested／accepted／rejected／stale
- `is_visitor` 必須固定為 false 或完全不建立此欄位

### 4. ProviderUsage

保存多租戶成本與額度：

- tenant_id、site_id、provider
- operation type
- request count、matched count、credits
- cache hit／miss
- estimated cost、billing period
- rate-limit／failure counts

### 5. IdentificationReview

保存人工判定：

- 原始候選與變更前後狀態
- reviewer、time、reason、notes
- confirmation source
- 不可變更的 audit trail

---

## 七、供應商定位

### IPinfo／IP2Location

只作網路品質、ASN、ISP、Hosting、VPN／Proxy 等分類，以及企業辨識的輔助證據。不得單獨用 network owner 產生「已辨識公司」。

### People Data Labs

作為第一版端到端技術基準：

- IP Enrichment 支援 IPv4／IPv6。
- 公司結果包含 confidence。
- IP 查詢的 person return 維持關閉。
- 聯絡人使用獨立 Person Search，依公司、職能與地區查找。

### Albacross

作為主要公司辨識競測來源：

- Reveal／Data API 的產品定位適合嵌入 ForgeBase。
- 目前 IPv4 限制必須獨立統計，不能掩蓋在整體 match rate。
- 正式採用前須取得 SaaS 展示、保存與多租戶報價書面條款。

### Snitcher IP-to-Company

作為主要公司辨識競測來源之一：

- ForgeBase 已有訪客 IP 與自有追蹤時，可直接呼叫 IP-to-Company API，不必先採用 Radar。
- 可回傳公司、網域、產業、規模、位置、社群資料及 business／ISP 等網路類型。
- 屬於獨立商業方案，不包含在一般 Snitcher 零售方案，須洽談測試額度、用量與 SaaS 資料展示權。
- 優點是整合邊界單純，不會先把 ForgeBase 事件追蹤核心交給第三方。

### Snitcher Radar

作為進階白標／OEM 與較高辨識率對照，而非第一版必要依賴：

- 可為每位客戶產生獨立 tracker。
- 支援自有網域代理、Operator API 與 webhook。
- 可使用 session lookup／fingerprinting 與單純 IP lookup 比較 match rate。
- 會與 ForgeBase 現有事件追蹤部分重疊，第一階段不直接取代自有追蹤核心。
- Radar 是獨立商業方案，一般 Snitcher 零售價不能用來估算正式 SaaS 成本。

只有在 Shadow Mode 證明 Radar 的辨識率提升足以補償額外成本、依賴與重複追蹤後，才評估把它列為正式選配。

### Hunter

負責企業聯絡窗口 Domain Search、Email 補找與驗證，作為 PDL Person Search 的第一輪對照來源：

- 不負責判斷哪位聯絡人曾造訪。
- Domain Search 只接受已確認公司網域，並限制個人型企業信箱、Persona 條件與每次最多 10 筆，以符合 Free 帳號測試邊界。
- ForgeBase 自行計算旅程與 Persona relevance；Hunter confidence 只作供應商資料品質訊號。
- 正式採用前確認資料展示、保存、匯出與 SaaS 使用權。

### 暫不採用

- RB2B、Vector 等人物級訪客辨識。
- Coffee 作為網站訪客識別來源。
- SyncGTM 或其他外聯自動化核心。
- Warmly 作為 ForgeBase 底層一站式替代品。
- 未取得書面資料授權的 Apollo 資料嵌入。

### 各階段保留選項

| 階段 | 首選接洽／自測 | 備選或對照 | 本階段不做 |
|---|---|---|---|
| 網路分類 | IPinfo | IP2Location＋IP2Proxy | 直接用 ISP 名稱認定公司 |
| 公司辨識 | PDL、Albacross、Snitcher IP-to-Company | KickFire；Leadfeeder／Lead Forensics 人工基準 | 一次正式整合所有候選 |
| 進階辨識率 | Snitcher Radar POC | 先維持純 IP Adapter | 人物級訪客揭露 |
| 聯絡人搜尋 | PDL Person Search | Hunter Domain Search | 將聯絡人認定為進站本人 |
| Email 驗證 | Hunter | 經授權的第二驗證來源 | 未驗證即進入外聯 |
| Waterfall | ForgeBase Adapter；Clay 短期實驗 | 手動樣本比較 | 長期把 Clay 當正式核心 |

進入付費 POC 前，應至少取得兩個可比較的公司辨識來源；最多同時接三個，避免工程與測試成本失控。

聯絡窗口第一輪只比較 PDL Person Search 與 Hunter Domain Search；Apollo 保留為兩者皆無法達標時的第三候選，不申請、不購買，也不在 production 啟用。

---

## 八、多租戶與成本模型

正式 SaaS 不應替每個租戶購買一套單站零售工具，而應談：

> 平台／OEM 基本費＋全租戶彙總用量＋超額費用。

```text
每月第三方資料成本
= OEM／平台基本費
+ 網路分類 API 用量
+ 公司辨識成功量或查詢量
+ 聯絡人搜尋 credits
+ Email 驗證 credits
+ 超額與支援費用
```

成本會隨總流量與有效辨識量增加，但不應機械化地等於「單站價格 × 租戶數」。

### 成本控制規則

1. 同一 IP／網路於 TTL 內只查一次。
2. 同一公司於 enrichment TTL 內不重複補齊。
3. VPN、Hosting、ISP、Bot 等低價值流量不進昂貴查詢。
4. 未達意圖門檻不搜尋聯絡人。
5. 每個租戶與方案都有月額度、告警與 hard limit。
6. 平台保留全域熔斷，避免程式錯誤產生大量付費請求。
7. 用量帳本必須能對帳供應商帳單。

### 客戶方案原則

ForgeBase 第一層網站工具仍以固定月費為主；第二層公司辨識與聯絡人能力宜採：

- 方案內含公司辨識額度。
- 方案內含聯絡人查找／驗證額度。
- 超額用量計費。
- 不以未確認的企業或聯絡人候選冒充「成功 Leads」計費。

---

## 九、30 天 Shadow Mode 實測

### 測試網站

第一階段指定現有 **NorthForge Tools 完整動態手工具網站**作為主要參考網站，原因是它已具備產品、應用、能力、文件、AI Product Advisor、CTA、RFQ 與 ForgeBase 後台串接，能測量完整的 B2B 瀏覽與轉換行為。

- `pcbrm.tw` 維持 ForgeBase 產品官網，不作 NorthForge 首頁。
- NorthForge 應使用獨立正式網域或明確的專屬子網域。
- 正式測試 URL、品牌揭露方式與隱私文字須在引流前確認。
- 其他靜態產業範本只作產品展示，不混入第一輪公司辨識成效樣本。

### 流量與曝光選項

測試必須同時包含兩種流量，且報表分開：

| 流量組 | 目的 | 首選方式 | 備選方式 |
|---|---|---|---|
| 已知公司控制組 | 驗證 company precision | 經同意、已知任職公司的受測者從公司網路進站 | 合作廠商、顧問或不同地區已知公司樣本 |
| 真實市場流量 | 驗證 match rate、意圖與實際成本 | Google Search Ads 導向產品／應用落地頁 | LinkedIn 精準廣告、產業內容曝光 |
| 自然搜尋流量 | 驗證中長期可持續流量 | 產品、應用、規格與比較頁 SEO | Search Console 索引與查詢優化 |

第一輪以 Google Search Ads 作可控流量來源，自然搜尋同步累積；LinkedIn 只在需要補足特定職能或地區樣本時加入。不得為增加流量而建立虛假法人、證書、客戶案例或產業名錄身分。

引流前必須完成：

- Google Ads 帳號、付款與測試預算。
- Search Console 網域驗證；GA4 可作外部對照但不是 ForgeBase 追蹤的必要依賴。
- UTM、campaign、keyword、landing page 與 visitor／session 的歸因保存。
- Bot、內部測試、控制組、付費流量與自然流量標記。
- 流量不足、錯誤率、成本超標與不當 RFQ 的暫停門檻。

### 運作方式

- 同一批合格流量並行送至候選供應商。
- 結果只進內部測試資料，不顯示給一般租戶。
- 不建立 Lead、不產生外聯、不影響公開網站流程。
- 透過自有測試公司、已知合作方或經同意樣本建立 ground truth。
- 每筆人工驗證都留下方法與證據，避免憑感覺判斷。
- 控制組用來計算準確率，真實市場流量用來計算辨識率與商業行為；兩者不得合併成單一成功率。

### 必測指標

| 指標 | 說明 |
|---|---|
| Company precision | 可確認結果中，公司判定正確的比例 |
| Match rate | 合格流量中可回傳公司候選的比例 |
| Domain accuracy | 公司正規化網域的正確率 |
| Regional coverage | 台灣／亞洲／歐洲／北美分別統計 |
| IPv4／IPv6 coverage | 不能只看合併數字 |
| Network false positive | ISP、VPN、Hosting、共享辦公室誤判率 |
| Contact relevance | 職能、職級、地區是否符合目標買家 |
| Verified business email rate | 可驗證企業 Email 的比例 |
| Cost per accepted account | 每個人工接受企業候選的實際成本 |
| Cost per usable contact | 每個可用相關聯絡人候選的實際成本 |
| Latency／failure rate | API 延遲、timeout、rate limit、錯誤率 |

### 發布門檻

1. 高信心顯示層的 company precision 目標至少 90%。
2. Match rate 與 precision 分開呈現，不得用低品質匹配灌高覆蓋。
3. 所有結果具備 provider、confidence、取得時間與到期時間。
4. IPv6、VPN、Hosting、ISP 的處理結果可獨立稽核。
5. UI 固定標示「推測企業」與「相關聯絡人候選」。
6. 沒有 OEM／SaaS 終端展示權的供應商直接淘汰。
7. 成本可被 ForgeBase 方案額度與毛利模型承受。

未達 90% 的結果不一定全部刪除，但不得進入「高信心」顯示層；可維持隱藏或標示為「可能企業」，供內部研究。

---

## 十、後台 UIUX 規格

傳產使用者不應看到供應商技術細節堆疊。主要畫面只呈現：

- 推測企業名稱與國家。
- 關注度與主要瀏覽產品／頁面。
- 辨識信心：高／中／待確認。
- 首次／最近造訪與訪問次數。
- 相關聯絡人候選及其職務。
- 接受、否決、稍後處理等簡單操作。

詳細來源、ASN、provider、原始 confidence、查詢歷程與成本，只放在展開明細或平台管理員畫面。

必須顯示的固定說明：

> 公司資訊為系統依網路與第三方資料推測；聯絡人是該企業的相關商務窗口候選，不代表該人曾造訪網站。

禁止 UI 文案：

- 「已找出這位訪客」
- 「這個人看過哪些頁面」
- 「已產生 X 個 Leads」（若只是公司／聯絡人候選）
- 「100% 確認公司」

---

## 十一、隱私、安全與資料治理

- 原始 IP 僅在必要期間內處理，保存方式、保留期限與刪除流程必須文件化。
- tenant_id 與 site_id 必須存在於所有辨識、聯絡人與用量紀錄。
- 供應商金鑰只存於後端祕密管理，不得寫入資料庫明文、前端 bundle 或 log。
- Log 不得輸出完整聯絡人資料、完整 provider response 或 API key。
- 支援資料刪除、到期、重新查詢及供應商退出後的歷史資料處理。
- 正式啟用前完成隱私政策、DPA、subprocessor、資料區域及跨境傳輸檢查。
- 聯絡人資料只能用於合法 B2B 業務目的；本階段外聯預設關閉。

---

## 十二、供應商商務詢價清單

每家候選供應商必須書面回答：

1. 是否允許 ForgeBase 多租戶 SaaS 嵌入與白標？
2. 是否允許把辨識結果顯示給 ForgeBase 終端客戶？
3. 依網站、租戶、API 次數、流量或成功辨識量何者計價？
4. 是否支援全租戶彙總額度與用量分帳？
5. 同一公司出現在不同租戶網站時如何計費？
6. 是否有平台最低月費、年度最低承諾或設定費？
7. 是否允許快取、保存、匯出、衍生評分與人工修正？
8. 聯絡人資料能否儲存在 ForgeBase？保存多久？
9. 是否提供 sandbox、測試額度與正式環境分離？
10. API rate limit、SLA、故障通知與支援時效為何？
11. 是否提供 DPA、subprocessor、資料區域、刪除與稽核機制？
12. 合約終止後，既有與衍生資料如何處理？
13. 是否會使用 ForgeBase 或客戶資料訓練模型或建立其他資料產品？
14. 是否支援 IPv4、IPv6、VPN、Proxy、Hosting 與行動網路分類？

任何只提供公開 API、但未明確允許終端客戶展示或再散布的方案，不得直接進入正式產品。

---

## 十三、分階段執行清單

### 階段總覽與第三方依賴

| 階段 | 可否在沒有第三方帳號時進行 | 主要產出 |
|---|---:|---|
| Phase 0～1 | 可以 | 安全語意、資料模型、Adapter、成本治理與自動化測試 |
| Phase 1.5 | 可以 | ForgeBase 第一階段公開上線、NorthForge 測試站與 Partner Brief |
| Phase 2 | 需要對外接洽 | 測試額度、API Key、OEM／資料權利與報價 |
| Phase 3 | 需要 API 與真實流量 | 30 天並行 Shadow Mode 與供應商比較 |
| Phase 4～5 | 需要已選定的供應商 | 受控 UI、商業、隱私與正式驗收 |

### Phase 0：語意與安全修正

- [ ] 停止以 IP `org` 直接產生已辨識公司。
- [ ] 將既有資訊重新命名為 network owner／網路組織。
- [ ] 加入功能開關，正式租戶預設不顯示未驗證公司。
- [ ] 確認既有資料是否需要重新分類或標記為低信心。

### Phase 1：共用架構

- [ ] 建立 NetworkObservation。
- [ ] 建立 CompanyIdentification。
- [ ] 建立 ContactCandidate。
- [ ] 建立 ProviderUsage 與 IdentificationReview。
- [ ] 建立 Provider Adapter contract。
- [ ] 建立快取、TTL、去重、rate limit、retry、熔斷與 cost guard。
- [ ] 補齊租戶／網站隔離測試與稽核紀錄。

### Phase 1.5：第一階段上線與接洽準備

- [ ] `pcbrm.tw` 的 ForgeBase 官網、後台入口、隱私與正式聯絡方式可公開使用。
- [ ] NorthForge 使用獨立網域／專屬子網域，整站、RFQ、AI與追蹤流程可操作。
- [ ] 公司辨識 UI 使用安全的未連線／Shadow Mode 狀態，不再展示 ISP 為公司。
- [ ] 建立一頁 Partner Brief：定位、目標市場、產品畫面、多租戶模式、POC 網站與預估用量。
- [ ] 準備 PDL、Albacross、Snitcher 各自專屬英文接洽信與統一商務問題表。
- [ ] 第一階段上線通過 Code Review、部署、瀏覽器與真人操作驗收後，才正式寄出供應商接洽信。

### Phase 2：供應商資格與 POC

- [ ] 完成 PDL 商務與授權確認。
- [ ] 完成 Albacross 商務與授權確認。
- [ ] 優先完成 Snitcher IP-to-Company 試用、用量與 SaaS 展示權確認。
- [ ] 另行詢問 Snitcher Radar OEM 與 session lookup POC，作進階 match-rate 對照。
- [ ] 完成 IPinfo 或 IP2Location 授權確認。
- [ ] 完成 Hunter SaaS 展示、保存與用量條款確認。
- [ ] 從 PDL、Albacross、Snitcher IP-to-Company 中至少選 2 個、最多選 3 個建立 POC Adapter。
- [ ] 只有通過商務資格的供應商能進入真實 POC；自助試用結果不能自動視為已取得正式 SaaS 授權。

### Phase 3：Shadow Mode

- [ ] 確認 NorthForge 測試網域、Google Ads、Search Console、UTM 與測試預算。
- [ ] 建立已知真實公司測試樣本與驗證 SOP。
- [ ] 並行執行 30 天供應商競測。
- [ ] 分區、分網路類型與 IPv4／IPv6 報告結果。
- [ ] 計算 accepted account 與 usable contact 單位成本。
- [ ] 完成主供應商、備援供應商與淘汰決策。
- [ ] 視純 IP 結果決定是否追加 Snitcher Radar session／fingerprinting 對照，不預設一定採用。

### Phase 4：受控 UI

- [ ] 後台顯示推測企業、信心、主要行為與來源時間。
- [ ] 顯示相關聯絡人候選及「非進站本人」說明。
- [ ] 支援接受、否決、理由、覆核與到期。
- [ ] 只對指定測試租戶啟用。
- [ ] 不啟用自動外聯。

### Phase 5：商業化前驗收

- [ ] 確認方案額度、超額費用與成本熔斷。
- [ ] 完成隱私政策、DPA、subprocessor 與資料刪除驗收。
- [ ] 完成供應商故障與切換演練。
- [ ] 完成後台真人操作與傳產使用者可理解性測試。
- [ ] 更新功能完整度稽核分數，但只按已實作、測試及部署證據評分。

---

## 十四、完成定義

本項目不能因「已串上一個 API」就宣告完成。至少必須同時達成：

- 正確區隔網路營運者、企業候選、聯絡人候選與 Lead。
- Provider Adapter、統一資料模型、快取、用量與租戶隔離完成。
- 至少一個主供應商與一個可替換／對照來源通過實測。
- 高信心公司結果 precision 達到發布門檻。
- 相關聯絡人不被描述為進站者。
- 正式書面授權允許 SaaS 展示與必要資料保存。
- 成本能由 ForgeBase 方案額度涵蓋。
- Shadow Mode、Code Review、自動化測試、正式部署與瀏覽器操作驗收都有證據。

在完成上述條件前，本模組只能稱為「研究／POC／受控測試」，不能宣稱 ForgeBase 已能可靠辨識所有訪客公司或產生可計費 Leads。

---

## 十五、官方參考資料

- [People Data Labs IP Enrichment API](https://docs.peopledatalabs.com/docs/ip-enrichment-api)
- [People Data Labs IP Enrichment Reference](https://docs.peopledatalabs.com/docs/reference-ip-enrichment-api)
- [Albacross Data API](https://www.albacross.com/data-api)
- [Snitcher Radar Introduction](https://docs.snitcher.com/powered-by-snitcher/radar/introduction)
- [Snitcher Radar Installation](https://docs.snitcher.com/powered-by-snitcher/radar/installation)
- [Snitcher IP-to-Company Introduction](https://docs.snitcher.com/powered-by-snitcher/ip2company/introduction)
- [Snitcher IP-to-Company Quickstart](https://docs.snitcher.com/powered-by-snitcher/ip2company/quickstart)
- [Snitcher Pricing](https://www.snitcher.com/pricing)
- [IPinfo IP-to-Company](https://ipinfo.io/data/ip-company)
- [Hunter API for Data Plans](https://help.hunter.io/en/articles/12149400-hunter-api-for-data-plans)
- [Lead Forensics Data Compliance](https://www.leadforensics.com/compliance/data-compliance/)

---

## 十六、決策紀錄

| 日期 | 決策 |
|---|---|
| 2026-08-16 | 確認公司辨識與相關聯絡人候選為 ForgeBase 下一階段第二優先。 |
| 2026-08-16 | 確認不採用「辨識訪客本人」作為核心承諾。 |
| 2026-08-16 | 確認採 Provider Adapter 與多供應商 Shadow Mode，而非綁定單一平台。 |
| 2026-08-16 | 第一輪以 IPinfo、PDL、Albacross、Snitcher IP-to-Company、Hunter 為主要評估組合；Radar 改列進階辨識率對照。 |
| 2026-08-16 | 在供應商授權與實測完成前，外聯維持關閉，候選資料不得計為 Leads。 |
| 2026-08-16 | 確認先完成 ForgeBase 第一階段公開上線與供應商中立底層，再以已上線產品、NorthForge 測試站及 Partner Brief 對外接洽。 |
| 2026-08-16 | 確認 NorthForge 為第一輪真實流量測試站；Google Search Ads 為主要可控引流，自然搜尋與已知公司控制組同步執行。 |
| 2026-08-27 | 第一輪聯絡窗口 POC 定案為 PDL Person Search＋Hunter Domain Search／Email Verifier；Apollo 降為第三候選，只有前兩者無法達標才重新評估。 |
| 2026-08-27 | Resend、PDL、Hunter 免費帳號與 API 認證已完成無寄信健康檢查；免費帳號不等於已取得多租戶下游展示、保存或外聯授權，production 外部資料與寄送開關維持關閉。 |
