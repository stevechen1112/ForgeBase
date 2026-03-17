# ForgeBase Demo 網站逐頁破綻盤點

更新日期：2026-03-16

本文件的目標不是評論設計風格，而是用「一位真實手工具採購 / 進口商 / 私標品牌客戶」的視角，盤點 NorthForge demo 網站目前哪些地方已經足夠擬真，哪些地方仍會讓人出戲，進而降低信任、降低詢價意願、降低對談意願。

判斷標準只有一個：

- 這個頁面是否足以讓一位手工具買家覺得「這家公司懂我、做得到、值得我提交 RFQ 或主動聯絡」

---

## 1. 總結判斷

整體結論：

- 這個 demo 的內容骨架、產業語境、產品架構、應用場景與 OEM 敘事，已經明顯高於一般樣板站或假資料 demo。
- 但前台實際頁面仍混有不少「generic 製造商網站」殘留內容，部分文字甚至直接跨產業錯置，會讓真正的手工具採購在關鍵時刻產生疑問。
- 目前最大問題不是「沒有內容」，而是「內容不夠完全一致」。只要買家在不同頁面間來回看，會發現品牌敘事、產品範圍、服務能力、產地與公司規模有輕微到中度的不一致。

如果以成交前信任來看，目前站點狀態可評為：

- 擬真度：高
- 一致性：中
- 成交說服力：中高
- 真正能讓買家放心送 RFQ 的程度：尚未到位，但已非常接近

---

## 2. 最關鍵的出戲點

以下是最需要優先修掉的問題，因為它們不是細節，而是會直接傷害信任的破綻。

### P0：跨產業殘留文案

目前仍可看到與 NorthForge 手工具定位不符的 generic 文案，例如：

- 首頁仍出現 `precision hardware, fasteners, and industrial components` 的泛工業說法
- About 頁年表出現 `precision fastener exports`
- RFQ 頁與 `/rfq` 頁 metadata 仍出現 `OEM seals, custom gaskets`

這類字眼會讓買家立刻懷疑：

- 你們到底是做手工具，還是做五金零件，還是做密封件？
- 這網站是不是從別的產業模板改來的？
- 如果文案都對不齊，RFQ 需求會不會也被錯誤理解？

這是目前全站最優先要清乾淨的問題。

### P0：首頁與 About 頁的公司定位仍偏 generic

NorthForge 的 demo 母稿其實很強，定位是：

- 台灣 OEM/ODM 手工具外銷製造商
- 強項是 torque consistency、documentation discipline、private label execution、mixed-SKU flexibility

但實際首頁與 About 頁仍保留大量 generic 全球製造商口吻，例如：

- 40+ countries served
- 500+ product SKUs
- 280+ team members
- Germany and Australia offices

問題不是這些數字本身不能存在，而是它們目前沒有被 demo 母稿支撐，反而稀釋了 NorthForge 原本更可信的「中型、專業、流程穩」設定。

### P0：RFQ 頁的內容沒有完全站在手工具採購角度發問

目前 RFQ 表單本體可用，但語氣仍偏 generic 工業詢價頁，像是：

- specifications placeholder 還在講 dimensions、materials、pressure ratings
- 信任側欄沒有強化手工具買家真正關心的資訊

手工具買家更在意的是：

- MOQ 與 mixed-SKU 彈性
- OEM logo / packaging scope
- 扭力精度、材料、表面處理
- VDE / REACH / RoHS / 文件支援
- 樣品流程與量產一致性

如果 RFQ 頁沒有把這些問題問對，買家即使願意詢價，也會覺得這家公司沒有真正理解手工具採購流程。

### P1：部分頁面過於乾淨，像資料架但不像商業頁

幾個頁面已經有資料，但頁面內容層次仍偏少，例如：

- Capabilities 列表 / 詳頁
- Certifications 列表 / 詳頁
- Applications 列表
- Docs / Dealers / Careers

這些頁面目前像「可點開的資料頁」，但還不像「能建立商業信任的銷售頁」。

---

## 3. 逐頁盤點

以下依「核心成交路徑」優先排序，而不是單純依網站導航排序。

---

## 4. 首頁 Home

對應實作：

- `web/src/app/page.tsx`
- `demo/handtool-company/content/07-homepage-source.md`

### 目前好的地方

- 有 hero image，整體視覺不廉價
- 有產品分類、應用場景、認證與 CTA 主線
- 已有 NorthForge demo 圖資支援分類與首頁 hero
- 對第一次造訪者來說，第一印象已經明顯像一家真的出口製造商

### 破綻

1. 首頁 metadata 與主文案仍是 generic 製造商語氣，不是 NorthForge 母稿語氣。
2. STATS、WHY_US、TESTIMONIALS 是靜態 generic 文案，沒有完全對齊手工具產業與 NorthForge 設定。
3. Featured Products 區塊使用 `/products/${product.slug}`，不是正式的 `/products/{categorySlug}/{productSlug}` 結構，容易造成路徑不一致與可信度下降。
4. featured product 卡片還用抽象占位符 `⬡`，沒有充分利用現有 demo 圖片。
5. 首頁文案出現 `fasteners`、`industrial components`，會直接削弱手工具專注感。
6. testimonial 目前像寫得不錯的樣板評論，但還不夠像真實採購語境，少了採購場景、SKU、樣品、包裝、文件等具體細節。

### 對買家的負面影響

- 首頁會讓人覺得專業，但細看會發現不是一間「手工具專業廠」，而是一間泛工業站。
- 如果買家是高意圖採購，會立刻開始尋找產品可信證據；目前首頁證據夠多，但不夠聚焦。

### 建議修正

1. 全面用 `07-homepage-source.md` 內容替換首頁主文案與 metadata。
2. 把 stats 改成與母稿一致，例如：20+ years、30+ core catalog SKUs、40+ countries、98% documentation readiness。
3. featured product 卡片改用真實產品圖，不要再顯示 `⬡`。
4. testimonial 改成採購語境版本，至少包含：角色、地區、市場、採購痛點、合作成果。
5. 加一段真正能打動採購的首頁證據區塊：MOQ flexibility、OEM packaging、documentation support、sample-to-production control。

---

## 5. About 頁

對應實作：

- `web/src/app/about/page.tsx`
- `demo/handtool-company/content/08-about-source.md`

### 目前好的地方

- 頁面結構完整，有 hero、story、values、timeline、team、capabilities、certifications
- 有工廠 hero image，整體氛圍比一般樣板站更像真實公司

### 破綻

1. About 頁的大部分敘事是 generic 公司史，不是 NorthForge 母稿裡那種「為了解決樣品到量產落差與文件混亂而成立」的故事。
2. 年表出現 `precision fastener exports`，與手工具 demo 不一致。
3. `Germany and Australia offices`、`280+ team members` 這種設定目前沒有在 demo 其他頁面或內容系統裡被支撐。
4. Leadership team 是純靜態英文姓名與縮寫球，沒有真實照片、職責故事或對採購者有意義的角色分工。
5. 核心價值是企業通用詞，不夠像手工具出口廠。

### 對買家的負面影響

- 這頁本來應該是建立「這家公司值不值得信任」的關鍵頁，現在結構很好，但讀完後記不住 NorthForge 的差異化優勢。

### 建議修正

1. 以 `08-about-source.md` 重寫 Company Overview、Founder Story、Manufacturing Philosophy、Operational Strengths。
2. 年表改成與手工具產品線擴張、扭力驗證、OEM kit assembly 更相關的里程碑。
3. Team 區塊改為「出口買家會接觸到的人」，例如 Sales Director、OEM Project Coordinator、QA Lead、Packaging Program Manager。
4. 把 values 改為更實務的 buyer promise：repeat-order consistency、packaging accuracy、document clarity、engineering review discipline。
5. 若無法支撐海外 office 設定，寧可收斂為「台中 / 台灣生產基地 + 出口市場覆蓋」，不要誇大。

---

## 6. Products 總覽頁

對應實作：

- `web/src/app/products/page.tsx`

### 目前好的地方

- 有 category grid，能快速導向分類頁
- 有簡潔 CTA，結構清楚
- 已接上分類圖

### 破綻

1. Hero 與 highlights 仍偏 generic catalogue page，不像 NorthForge 的手工具採購入口頁。
2. `500+ SKUs`、`Fast Shipping` 等字樣過於泛化，削弱 demo 的中型專業感。
3. 各分類說明目前多半只做摘要，缺少 buyer-facing 篩選語言，例如 distributor program、OEM starter range、utility buyer、aftermarket service 等。

### 建議修正

1. Hero copy 改成手工具採購導向：standard range、OEM/private label、service kits、utility tools。
2. 在分類卡上增加更像採購邏輯的標記，例如：for distributors、for OEM/private label、for workshop service。
3. 增加「Not sure where to start?」導引，把買家導到 Applications 或 Contact。

---

## 7. Category 分類頁

對應實作：

- `web/src/app/products/[categorySlug]/page.tsx`

### 目前好的地方

- 已有 hero 圖
- 已有產品搜尋與產品卡
- 結構清楚、實用

### 破綻

1. 分類頁主要是 listing，但缺少一段真正解釋「這一類產品是替哪種買家解決什麼問題」的 buying-context 文案。
2. 缺少 category-level trust blocks，例如常見應用、常見認證、常見 OEM 需求、常見 MOQ 問題。
3. 產品卡雖然可看，但若 fallback 到分類圖，會讓多個 SKU 長得很像，削弱 SKU 真實性。

### 建議修正

1. 每個 category page hero 下方新增 buyer-oriented intro：典型採購場景、典型品項結構、OEM 支援與文件支援。
2. 增加 category FAQ 精選與相關 certifications 縮圖。
3. 對沒有單獨產品圖的 SKU，至少增加更明顯的型號、規格短標籤、應用標籤，降低重複感。

---

## 8. Product 詳頁

對應實作：

- `web/src/app/products/[categorySlug]/[productSlug]/page.tsx`

### 目前好的地方

- 是目前整站最接近成交頁的頁型之一
- 有產品圖、型號、產品概述、規格表、FAQ、Applications、Certifications、CTA、Download Gate、ChatWidget
- 對高意圖買家已具備實際閱讀價值

### 破綻

1. 若產品沒有專屬圖，fallback 仍不足以支撐「這是不同 SKU」的感受。
2. 頁面少了更像採購頁的內容區塊，例如：typical buyers、OEM options、available packaging formats、compliance note。
3. 沒有明確區分「已確認資訊」與「需 RFQ 確認資訊」，容易讓買家不知道哪些可直接判斷，哪些要再問。
4. Certifications 區塊欄位名稱有舊欄位殘留跡象：使用 `badge_icon_url`、`issuing_body`，而目前 repo memory 記錄真正公開 payload 用的是 `badge_image_url`、`issuer`。這會導致資料顯示不完整或不一致。

### 建議修正

1. 每個 product detail 增加「Best fit for」與「OEM / private label options」小節。
2. 加一個 `What to confirm before RFQ` 區塊，直接引導買家想下一步。
3. 對沒有單獨產品圖的 SKU，追加局部細節圖或包裝圖，不要只靠分類 hero 代替。
4. 修正 certification 顯示欄位對應，避免證書資訊顯示斷裂。

---

## 9. Applications 總覽頁

對應實作：

- `web/src/app/applications/page.tsx`

### 目前好的地方

- 已經有 application cards 與圖片支撐
- 對買家導購價值高

### 破綻

1. metadata 文案仍寫 `from automotive to electronics to construction`，不符合 NorthForge 的應用地圖。
2. 頁首說明過於 generic，不像手工具解決方案入口頁。
3. 若採購是從應用角度找供應商，這一頁目前還不夠強化「你們懂我的使用場景」。

### 建議修正

1. 改寫成以 demo 既有六個應用場景為核心的文案，不再提 electronics / construction 這些未完整支撐的範疇。
2. 在列表頁加入一句話說明：每個頁面會告訴你常見工具組合、常見採購痛點與對應的 NorthForge 產品族群。

---

## 10. Application 詳頁

對應實作：

- `web/src/app/applications/[applicationSlug]/page.tsx`

### 目前好的地方

- challenge / solution 結構正確
- 有 related products、FAQ、CTA、ChatWidget
- 已經很接近「顧問式銷售頁」

### 破綻

1. hero image 目前依賴 `application.hero_image_url`，但沒有使用集中式 demoAssets fallback；若資料端未補齊，會直接弱掉。
2. related products 區塊只有文字卡，少了圖與規格短摘要，說服力不足。
3. CTA 太 generic，應該更像 `Discuss your assortment`、`Plan OEM/private-label scope`、`Request application-specific quote`。
4. 頁面缺少「buying criteria」或「common sourcing concerns」區塊，這正是應用頁最能打動採購的內容。

### 建議修正

1. 加入 demoAssets 的 application 圖片 fallback。
2. 讓 related products 顯示小圖、型號、1-2 個關鍵規格。
3. 在 solution 後方新增 `What buyers usually need to confirm` 區塊。
4. 將 CTA 改為更像採購前會點的文案。

---

## 11. Capabilities 列表頁

對應實作：

- `web/src/app/capabilities/page.tsx`

### 目前好的地方

- 架構乾淨、功能正常

### 破綻

1. 頁首過短，看起來像資料索引頁，不像服務能力頁。
2. 沒有任何視覺支撐，商業分量感不足。
3. 採購方最在意的能力，例如 OEM packaging、torque verification、documentation support，沒有被排序或強調。

### 建議修正

1. 補上 capabilities hero 與引言。
2. 分組展示能力：engineering / quality / packaging / export。
3. 在列表卡片上補 `Why it matters to buyers` 一句話。

---

## 12. Capability 詳頁

對應實作：

- `web/src/app/capabilities/[slug]/page.tsx`

### 目前好的地方

- 有 detail 與 snapshot，基礎資訊完整

### 破綻

1. detail 區塊過於平鋪直敘，頁面像 CMS 內容頁，不像商業頁。
2. 沒有案例、流程圖、圖像或 buyer outcome。
3. 沒有 CTA，缺少承接動作。

### 建議修正

1. 每頁加入 `What this means for buyers` 區塊。
2. 對 OEM / packaging / torque inspection 等能力頁補流程圖或現場圖。
3. 頁底補 `Talk to us about this capability` CTA。

---

## 13. Certifications 列表頁

對應實作：

- `web/src/app/certifications/page.tsx`

### 目前好的地方

- 有 badge grid
- 有簡單信任敘事

### 破綻

1. 頁面說法仍偏 generic 國際品質頁，不像出口手工具文件支援頁。
2. 沒有強調買家真正在乎的是：哪些文件可提供、何時提供、哪些是 selected products only。
3. certification page 若只講認證，不講文件提供邏輯，採購感受會偏空。

### 建議修正

1. 改寫為 `Certifications & Documentation Support`。
2. 明確標示哪些是系統認證、哪些是材料 / 法規支援、哪些需依 SKU / market 確認。
3. 補一個 `Request documentation` 區塊說明需要哪些資料才可快速回覆。

---

## 14. Certification 詳頁

對應實作：

- `web/src/app/certifications/[slug]/page.tsx`

### 目前好的地方

- 結構完整，資訊呈現方式清楚

### 破綻

1. detail 頁缺少「適用哪些產品 / 哪些市場 / 哪些情境」說明。
2. 若 badge image 或 document 沒有，頁面會顯得過空。
3. 沒有導向具體產品或 FAQ 的內連，少了採購下一步。

### 建議修正

1. 每張認證加入 `Relevant products`、`Typical buyer questions`。
2. 補齊 badge 與 document 圖資。
3. 加入 `Need this document for your RFQ?` CTA。

---

## 15. FAQ 頁

對應實作：

- `web/src/app/faq/page.tsx`

### 目前好的地方

- 結構清楚
- 有 tag 與 FAQ schema
- ChatWidget 放置合理

### 破綻

1. 頁首文案仍偏 generic，沒有明確寫出這些 FAQ 是圍繞手工具 OEM / MOQ / packaging / compliance。
2. FAQ 列表若題目不夠具體，會看起來像樣板 FAQ。
3. 沒有加上 `Still need a specific answer?` 類型的強收斂 CTA。

### 建議修正

1. 頁首改成採購導向說法。
2. 將 FAQ tag 名稱調整得更商業化，如 MOQ & lead time、OEM/private label、certification support、sample & mass production。
3. FAQ 區塊後方增加 RFQ 或 Contact 引導。

---

## 16. Contact 頁

對應實作：

- `web/src/app/contact/page.tsx`
- `web/src/components/forms/ContactForm.tsx`

### 目前好的地方

- 表單好填、結構完整
- 有 office、response promise、contact chips

### 破綻

1. Office 資訊目前是很明顯的 demo 式靜態地址，若無法被其他公司資訊頁支撐，容易出戲。
2. `sales@forgebase.com` 與 `NEXT_PUBLIC_CONTACT_*` 預設值會破壞 NorthForge 品牌沉浸感。
3. ContactForm 欄位仍偏泛用詢問表，少了 buyer segmentation，例如 inquiry type、product family、OEM interest。
4. 頁面沒有強化「如果你還沒準備好 RFQ，也可以先談什麼」的心智。

### 建議修正

1. 把聯絡資訊全面切到 NorthForge 品牌域名與公司設定，避免 ForgeBase 母品牌穿幫。
2. contact reason 加入：distributor inquiry、OEM/private label、sample request、document request。
3. office 若無法完整支撐，改用 `Taiwan sales team / export support / OEM project desk` 類型資訊，比寫精確地址更可信。

---

## 17. RFQ / Request Quote 頁

對應實作：

- `web/src/app/request-quote/page.tsx`
- `web/src/app/rfq/page.tsx`
- `web/src/components/forms/RFQForm.tsx`

### 目前好的地方

- 這是目前最接近真實 B2B conversion page 的頁面之一
- 表單欄位完整、草稿保存、事件追蹤齊全

### 破綻

1. metadata 直接殘留 seals / gaskets，是全站最高優先級錯誤之一。
2. trust sidebar 仍是 generic B2B 製造商說法，不像手工具 RFQ 頁。
3. RFQForm placeholder 提到 `pressure ratings`，完全錯產業。
4. 缺少手工具採購真正關心的結構化欄位，例如：
   - OEM / standard supply
   - logo marking / packaging scope
   - target market
   - required compliance document
   - sample first or direct order
5. 缺少一個明確的採購協助文字：如果你不確定型號，也可以描述應用與目標市場。

### 建議修正

1. 立即清除 metadata 與 placeholder 的跨產業詞。
2. 新增 RFQ guidance 區塊：我們最需要你提供哪些資訊。
3. 表單欄位調整為更像手工具 RFQ：SKU / model、quantity per SKU、OEM scope、market、required packaging、document support。
4. trust sidebar 改成：ISO 9001、OEM/private label、mixed-SKU kits、sample-to-production alignment、documentation support。
5. 在表單頂部加入一句話：`Not sure which models fit best? Submit your application, target market, and packaging scope — our team can help shortlist.`

---

## 18. Comparisons 列表與詳頁

對應實作：

- `web/src/app/comparisons/page.tsx`
- `web/src/app/comparisons/[slug]/page.tsx`

### 目前好的地方

- 這類頁型本身很適合高意圖 SEO 與採購教育

### 破綻

1. 頁面目前仍偏 generic comparison hub，沒有凸顯 NorthForge 在 sourcing decision 上的顧問角色。
2. detail 頁只有 table 與 conclusion，缺少 buyer takeaway，例如何時選 A、何時選 B、何時該直接詢問工程支援。
3. 沒有把 comparison 內容導回產品頁、RFQ、應用場景頁，少了成交導流。

### 建議修正

1. comparisons 列表頁增加一句：`Built for buyers comparing durability, compliance, OEM fit, and total sourcing complexity.`
2. detail 頁補 `Recommended for`、`When to RFQ`、`Related products`。
3. 每篇比較文底部加 CTA。

---

## 19. 次要支撐頁面

### News

對應實作：

- `web/src/app/news/page.tsx`

判斷：

- 有內容，但目前更像靜態公告清單。
- 若要提升真實感，應加入實際產品線更新、展會、文件能力更新等訊息，並且至少有詳頁或圖片。

### Docs

對應實作：

- `web/src/app/docs/page.tsx`

判斷：

- 目前比較像占位頁，不像真正文件中心。
- 採購如果點進來，會期待看到文件類型、可取得條件、代表性文件樣本。

### Dealers

對應實作：

- `web/src/app/dealers/page.tsx`

判斷：

- 目前頁面較像簡單說明頁，沒有具體 dealer 模式、合作條件、地區支援邏輯。
- 若沒有真實 dealer program 內容，建議暫時不要主推這頁。

### Careers

對應實作：

- `web/src/app/careers/page.tsx`

判斷：

- 這頁本身不是成交主線，但目前內容非常模板化。
- 若對外展示完整公司感，可以保留；若重點是外銷成交，優先級可低。

---

## 20. 圖像層面的破綻

目前視覺基礎已不差，但仍有幾個影響真實感的點：

1. 多數頁面只有 hero 級圖像，缺少中段說服圖。
2. 很多 SKU 沒有專屬產品圖，只能靠分類圖 fallback。
3. 圖片雖然風格一致，但還缺少幾種最有說服力的 B2B 圖：
   - 包裝樣式圖
   - 工廠 QA / inspection 圖
   - kit assembly / EVA foam 圖
   - 文件或標示細節圖
4. capabilities / certifications / comparisons 這些頁面，視覺上仍偏像資料層，不像銷售內容層。

建議補圖優先順序：

1. 產品專屬主圖補齊前 12 個高價值 SKU
2. About / OEM / QA / packaging 類支撐圖
3. application detail 中段圖
4. docs / certification supporting visuals

---

## 21. 文字層面的破綻

目前不是沒有文字，而是文字有三個來源混在一起：

- NorthForge 專屬母稿
- generic 製造商樣板文案
- 其他垂直殘留文案

這會造成以下問題：

1. 採購無法快速抓住公司真正的差異化
2. 讀得越多，越容易感覺到品牌口徑不完全一致
3. 當頁面進入 RFQ / certification / about 這種高信任節點時，破綻會被放大

建議原則：

- 所有核心頁文字都應以 `demo/handtool-company/content/` 母稿為唯一敘事來源
- 所有 generic 製造商 copy 應視為待替換內容，不再沿用
- 所有跨產業殘留詞應一次性清除

---

## 22. 優先修正順序

### 第一階段：先修會直接傷害信任的破綻

1. 清除全站跨產業殘留詞：seals、gaskets、fasteners、industrial components
2. 重寫首頁文案與 stats，使其完全對齊 NorthForge 母稿
3. 重寫 About 頁文案與年表
4. 重寫 RFQ 頁 metadata、trust copy、表單提示文字

### 第二階段：補強高意圖頁的成交說服力

1. Product detail 增加 buyer-facing 區塊
2. Application detail 增加 buying criteria 與更精準 CTA
3. Category page 增加採購場景與 FAQ / certification 補強
4. Contact page 改成更符合出口買家聯絡邏輯

### 第三階段：補強支撐頁與視覺證據

1. Capabilities / Certifications / Comparisons 加入更像商業頁的區塊
2. Docs / Dealers / News 補成更有真實度的支撐頁
3. 補齊高價值 SKU 圖片與中段說服圖

---

## 23. 目標狀態

理想的修正完成狀態應該是：

- 一位手工具採購從首頁進來，不會覺得這是 generic 工業網站，而會立刻知道這是懂 OEM / private label / export execution 的手工具供應商。
- 一位 distributor buyer 看完 category、application、product detail 後，會覺得這家公司真的理解 assortments、MOQ、packaging、documentation。
- 一位高意圖買家進到 RFQ 頁時，會明顯感受到：這家公司知道要問什麼，也知道怎麼幫我把需求收斂清楚。
- 任一頁點開都不會冒出讓人懷疑「這是不是從別的行業模板改來的」字眼。

如果做到這個程度，這個 demo 站就不只是「看起來擬真」，而是真的會讓手工具採購人員產生偏好的程度。
