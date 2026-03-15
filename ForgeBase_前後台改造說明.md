# ForgeBase 前後台改造評估（程式碼實查版）

> 本文件基於 ForgeBase 程式碼實際審查結果撰寫，不是基於想像中的「現狀」。
>
> 核心問題：如果 ForgeBase 要定位成「B2B growth site」，前後台到底要改多少？

---

## 一、結論：改動量比預期小很多

上一版文件把前台描述成「完整型錄官網思維」，把後台描述成「純內容管理後台」，然後提出大量改造方案。

**但程式碼告訴我們的事實不是這樣。**

ForgeBase 的前台已經不是傳統企業官網，後台也不是純 CMS。大部分 growth site 需要的底層能力已經存在，真正缺的東西可以在 2-3 週內補完。

---

## 二、前台現狀：比想像中更接近 growth site

上一版文件說「首頁要重做」「導覽列要重做」「RFQ 要補信任訊號」。但程式碼顯示：

### 首頁（web/src/app/page.tsx）

已經具備的：
- Hero 區塊 + 明確價值主張
- 6 個信任訊號（ISO 認證、物流網絡、OEM、客戶經理、快速打樣、透明報價）
- 客戶見證（含姓名/職稱/公司/引述）
- 數據區塊（40+ 國家、500+ SKU、20+ 年、98% 滿意度）
- 直接導向產品與 RFQ 的 CTA

**結論：首頁結構已經是 campaign landing page 形式，不需要重做。需要的是調內容（放對產品、寫對文案），不是改結構。**

### 導覽列（web/src/components/layout/Header.tsx）

目前的導覽：Products → Applications → Certifications → About → Contact

右側有兩個突出的 CTA 按鈕：「詢價」+「聯絡我們」

**結論：這已經是產品導向的導覽，不是傳統企業的「公司介紹/董事長的話/部門介紹」。不需要推翻，如果要加主角產品入口，在現有 nav 裡加一個 item 就好。**

### RFQ 頁（web/src/app/rfq/page.tsx, request-quote/page.tsx）

已經具備的：
- Trust sidebar（6 項信任利益點）
- SLA 承諾（1-2 個工作天回覆）
- 草稿自動存到 localStorage
- URL 預帶 product_id / application_id 參數
- 表單追蹤事件
- 成功確認頁含 RFQ 編號

**結論：上一版文件說要補信任訊號、減阻設計 — 這些已經存在。可以小幅改善（加 MOQ 提示、可詢價範圍說明），但不是「要強化」的等級。**

### 其他已就位的前台能力

| 能力 | 現狀 |
|---|---|
| 應用頁 | 完整 challenge/solution 敘事結構 + 關聯產品 + FAQ |
| 比較頁 | /comparisons/[slug] 已建置 |
| 規格下載 | DownloadGateModal 門檻式下載已建置 |
| CTA 追蹤 | 所有 CTA 都有 trackCTAClick() |
| SEO 基礎 | 結構化資料、canonical URL、hreflang、noindex 控制 |
| 多語系 | locale 欄位貫穿 Product / Application / Certification |

---

## 三、後台現狀：不是純 CMS

上一版文件把後台描述成「上內容、改頁面、看資料」的純 CMS。程式碼顯示後台已經有：

### Dashboard（admin/src/app/(dashboard)/dashboard/page.tsx）

6 個 KPI 卡片：月 RFQ 數（含趨勢）、活躍訪客、產品目錄量、轉換率、全球買家數、預估成交金額。加上最近 RFQ 列表與狀態標示。

### RFQ 管理

- 狀態機：new → assigned → in_progress → quoted → won / lost / expired
- 優先級：normal / high / urgent
- 指派給業務 + 指派通知
- 24 小時提醒 / 48 小時升級時間戳
- HubSpot deal 同步

### Analytics

- 頁面級：views、unique visitors、日期篩選
- 實體級（產品/應用）：views + rfq_start + rfq_submit + spec_download + cta_click
- Content strategy map（頁面類型 × 語系分布）

### 其他已就位的後台能力

| 能力 | 現狀 |
|---|---|
| Segments | 規則型分群（intent_stage / score / event_count / tag / country），AND/OR 邏輯 |
| Nurture | 後端模型完整（sequence + step + enrollment），觸發類型支援 intent_stage / segment / download_gate / manual |
| CTA 管理 | cta_key / type (banner/inline/popup/sticky_bar) / action (open_rfq/link/download) / locale / sort_order |
| 下載門檻 | 門檻式資產管理 + 下載請求記錄 |
| A/B 測試 | 後端完整（deterministic bucketing），admin 有管理頁 |
| 外部整合 | HubSpot / Google Ads / LinkedIn / Meta Conversions / Resend+SendGrid |

---

## 四、上一版文件不該做的建議

以下是上一版文件提出但**現階段不應該執行**的項目：

### 1. GrowthSite / 多站模型

上一版建議建立 Site / Campaign / Theme 管理層級。

**問題：** 你們連一個站都還沒用來成功獲客。在未驗證單站效果前就做多站管理架構，是 premature abstraction。先用一個站跑出成績再說。

### 2. 首頁重做

上一版說首頁要改成 campaign landing page。

**問題：** 首頁已經是了。Hero + 信任訊號 + 見證 + 統計 + CTA — 結構完整。要改的是內容策略（放哪個產品當主角），不是頁面架構。

### 3. 導覽列重做

上一版說導覽要從企業資訊架構改成獲客優先順序。

**問題：** 導覽已經是 Products → Applications → Certifications，不是傳統企業官網。

### 4. 內容模板重構

**問題：** 產品頁/應用頁/比較頁/FAQ 的頁面型態已經足夠。

### 5.「Growth Operations 後台」大概念

上一版用了大量篇幅描述後台要從「內容管理」升級成「成長營運」。

**問題：** 這是行銷包裝語言，不是技術需求。實際上要做的就是加幾個欄位和一個漏斗圖表。

---

## 五、真正需要做的事（完整清單）

以下是比對程式碼後，確認真正缺少且值得做的項目：

### 第一優先：主角產品概念（1-2 天）

**現狀：** Product model 沒有 `is_featured` 或任何優先級欄位，所有產品平等存在。

**要做的：**
- Product model 加 `is_featured: bool` 欄位
- Admin 產品管理頁加勾選
- 首頁加一個「主推產品」區塊，用 `is_featured` 過濾顯示
- （可選）Product model 加 `display_priority: int` 做排序

**不需要做的：** 不需要建立 Hero Product Set 管理模型、不需要多站關聯。

### 第二優先：RFQ 銷售跟進補完（1 天）

**現狀：** RFQ 狀態機本身完整（new→assigned→quoted→won/lost），但缺乏銷售實務欄位。

**要做的：**
- RFQRequest model 加 `first_response_at: datetime` — 業務首次回覆時間
- RFQRequest model 加 `quote_sent_at: datetime` — 報價發出時間
- RFQRequest model 加 `lost_reason: str` — 未成交原因
- Admin RFQ 詳情頁顯示這些欄位，讓業務可以填寫

**不需要做的：** 不需要重建 lead management console，現有 RFQ 管理頁加欄位即可。

### 第三優先：CTA 意圖分層（2-3 天）

**現狀：** CTA model 已有 type / action / sort_order，但沒有意圖階段欄位。所有訪客看到一樣的 CTA。後端 `dynamic_cta.py` 已有根據 intent stage 選 CTA 的基礎邏輯。

**要做的：**
- CTA model 加 `target_intent_stage: str` 欄位（cold / warm / hot / any）
- Admin CTA 管理頁可設定目標意圖階段
- 前台根據 visitor 的 intent_stage 顯示對應 CTA
- 確保 `dynamic_cta.py` 的邏輯被前台真正使用

**不需要做的：** 不需要重建 CTA 系統，不需要成效比較 dashboard（先做分層，有數據後再分析）。

### 第四優先：漏斗 Dashboard（3-5 天）

**現狀：** Analytics API 已有 page_views、unique_visitors、spec_downloads、rfq_submit、cta_click。但只以列表/表格呈現，沒有漏斗視圖。

**要做的：**
- 新增一個 admin dashboard 頁面，把現有指標串成漏斗：
  - Visitors → Warm（intent_stage=warm 的 visitor 數）→ Hot → RFQ submitted → Quoted → Won
- 加上各階段之間的轉換率
- （可選）按產品/應用篩選漏斗

**不需要做的：** 不需要市場/站點級聚合（沒有多站就不需要），不需要 campaign comparison 視圖。

### 第五優先：Nurture Admin UI（5-7 天）

**現狀：** 後端 NurtureSequence / NurtureStep / NurtureEnrollment model 和 API 都已建置，但 admin 前端只有資料夾存在，沒有完整操作介面。

**要做的：**
- Nurture sequence 列表頁（名稱、觸發類型、啟用狀態、已入列人數）
- Sequence 編輯頁（設定觸發類型與觸發值）
- Step 編輯介面（排序、延遲天數、email 主旨與內容）
- Enrollment 列表（哪些 contact 在哪個 sequence、進度到哪）

**不需要做的：** 不需要做進階的 orchestration 或跨 sequence 衝突管理。先讓基本功能可操作。

### 第六優先：Segment Builder UI 改善（2-3 天）

**現狀：** Segment 後端支援完整的 JSON 規則（type / op / value，AND/OR），但 admin 端的建立/編輯體驗不明。

**要做的：**
- 可視化的規則建置器（選 type → 選 operator → 填 value → AND/OR 組合）
- 預覽符合條件的人數
- 確認現有 segment 頁的 CRUD 操作完整

---

## 六、前台真正要動的只有兩件事

把上面的清單投射到前台，前台真正要改的只有：

### 1. 首頁加主角產品區塊

在現有 hero + trust signals 結構之間，插入一個「主推產品」區塊，從 `is_featured` 產品拉資料。

### 2. CTA 根據意圖階段切換

讓產品頁/應用頁的 CTA 區塊（目前的 ProductCTAButtons）能根據 visitor intent stage 顯示不同選項：
- Cold：「下載規格書」「看比較指南」
- Warm：「預約技術諮詢」「取得樣品」
- Hot：「立即詢價」

其他前台頁面（應用頁、比較頁、RFQ 頁、FAQ）不需要改結構。

---

## 七、時間與優先級總覽

| 順序 | 項目 | 預估工作量 | 前/後台 |
|---|---|---|---|
| 1 | Product 加 is_featured + 首頁主推區塊 | 1-2 天 | 前台 + 後端 + admin |
| 2 | RFQ 加銷售跟進欄位 | 1 天 | 後端 + admin |
| 3 | CTA 加 target_intent_stage + 前台動態切換 | 2-3 天 | 前台 + 後端 + admin |
| 4 | 漏斗 Dashboard | 3-5 天 | admin |
| 5 | Nurture Admin UI | 5-7 天 | admin |
| 6 | Segment Builder UI 改善 | 2-3 天 | admin |

**合計：約 2-3 週。**

---

## 八、跟上一版文件的差異

| 上一版說的 | 實查後的判斷 |
|---|---|
| 首頁要重做 | 首頁結構已是 landing page，調內容就好 |
| 導覽列要重做 | 導覽已是產品導向，不須推翻 |
| RFQ 要強化信任訊號/減阻 | 這些已經存在，小幅改善即可 |
| 前台要建立主角/配角/背景三層 | 加一個 is_featured 欄位就夠 |
| 後台要變成 Growth Operations 後台 | 加幾個欄位 + 一個漏斗圖 |
| 要建立 GrowthSite / Campaign 模型 | 目前不需要，先驗證單站 |
| 需要四個階段的中度產品重構 | 2-3 週可完成所有必要改動 |
| 前台 6 項結構調整 | 前台實際只需改 2 件事 |
| 後台 6 項能力新增 | 後台實際需要新增 4 項（其中 2 項是補 UI） |

---

## 九、最終判斷

ForgeBase 不需要「從官網系統改造成 growth site 系統」— 因為它從程式碼層面看，**本來就不是傳統企業官網系統**。

它已經有：tracking + intent scoring + RFQ 狀態機 + segment + nurture engine + CTA + analytics + 外部整合。這些就是 growth site 的底層。

真正缺的只是幾個欄位和幾個 UI 頁面。把這些補完，它就能跑。

**不要把「產品定位調整」當成「技術架構重構」。定位是 deck 和文案的事，不是程式碼的事。**

這會改很多，但不是全部重來。