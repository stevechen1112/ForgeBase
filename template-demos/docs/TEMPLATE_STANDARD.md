# ForgeBase 靜態產業範本規格

版本：1.0\
適用範圍：`template-demos/` 內所有未串接 ForgeBase 後端的產業網站展示範本

## 1. 目的

靜態範本用來證明 ForgeBase 網站「可以長什麼樣子」，不是用來證明後端功能已經完成。現階段只有手工具參考網站完整串接 ForgeBase；其他產業範本一律使用本地假資料，不呼叫正式 API、不蒐集訪客資料，也不送出表單。

本規格約束資料映射、轉換意圖、品質基線及未來串接方式，不限制視覺風格、資訊架構、版面密度或產業敘事。

## 2. 三層彈性模型

| 層級 | 約束程度 | 規範內容 |
|---|---:|---|
| 資料契約 | 高 | Site、Product、Application、Capability、Certification、FAQ、CTA、RFQ 的欄位語意 |
| 功能與品質 | 中 | 響應式、SEO、可及性、CTA 意圖、假表單攔截及 Demo 標示 |
| 視覺與版面 | 低 | Header、Hero、字體、色彩、區塊順序、產品呈現、動畫及資訊密度 |

範本可以擁有自己的 Header、Hero、Product Card、Footer 與產業專屬區塊。不得為了共用元件而把所有範本做成同一版型換色。

## 3. 技術規格

- Next.js、React、TypeScript。
- 樣式使用 Tailwind CSS 或範本自己的 CSS；禁止依賴正式 ForgeBase 前台的 runtime。
- 所有展示資料存放於範本自己的 `data/` 或型別安全的資料檔。
- 必須可執行靜態輸出，不得依賴 server action、資料庫、登入狀態或 runtime API。
- 每個範本必須以 manifest 註冊，不得靠路由中的硬編碼判斷。
- 共用的是 contracts、SEO／可及性基線與 Demo 安全元件；視覺元件預設由各範本自行持有。

## 4. 標準資料實體

範本可選擇使用以下實體，但使用時必須符合 `template-demos/src/contracts/forgebase.ts`：

- `SiteProfile`
- `ProductCategory`
- `Product`
- `Application`
- `Capability`
- `Certification`
- `FAQItem`
- `CTA`
- `RFQField`

產業專屬欄位放在 `attributes` 或 RFQ 的自訂欄位，不得擅自改變標準欄位原意。例如精密加工的材料、公差、表面處理可放入 `Product.attributes`，未來再映射至 ForgeBase 規格資料。

## 5. CTA 意圖

畫面文案可以自由變化，但 CTA 必須標記為下列其中一種意圖：

- `view_product`
- `request_quote`
- `contact_sales`
- `download_spec`
- `request_sample`
- `book_meeting`
- `ask_question`

例如「Send Your Drawing」與「Request Manufacturing Review」都可以映射到 `request_quote`。

## 6. 路由語意

範本不必實作所有路由，但若實作相同實體，應沿用以下語意：

```text
/
/products
/products/[slug]
/categories/[slug]
/applications/[slug]
/capabilities/[slug]
/certifications/[slug]
/about
/contact
/rfq
```

導覽顯示名稱可以依產業修改，例如 `Capabilities` 可顯示為 `Manufacturing`、`Engineering` 或 `Production`。

## 7. Demo 安全規則

每個靜態範本都必須：

1. 在固定且清楚的位置顯示 `Template Preview` 或同等說明。
2. 使用明確的示意公司、示意產品及示意數據。
3. 不使用可能被誤認為真實的法人編號、客戶背書或證書編號。
4. Contact／RFQ 表單不得送出網路請求；提交後只顯示 Demo 說明。
5. 不安裝訪客追蹤、公司辨識、廣告像素或聊天服務。
6. 不寄信、不建立聯絡人、不保存表單資料。
7. 預設加入 `noindex, nofollow`，除非未來另有可索引的範本展示策略。

## 8. 影像品質與來源規格

高品質產業影像是範本完成度的一部分，不是最後才補的裝飾。所有標記為 `ready` 的範本至少必須具備：

- 1 張能建立產業情境的首頁主視覺；
- 1 張真實呈現製程、設備或服務方法的能力影像；
- 1 張支撐品質、檢驗、團隊或信任敘事的影像；
- 1 組產品、零件、應用或成果影像。

影像必須產業正確、構圖適合實際版位、桌機與手機裁切後仍可使用。禁止以漸層方塊、灰色 placeholder、低品質素材或與產業無關的通用商務照，把範本標記為完成。

每套範本須維護資產清單，至少記錄：

- 檔名與用途；
- alt text；
- 來源為原創生成、授權素材或客戶提供；
- 若為生成影像，記錄最終 prompt／生成規格；
- 是否只適用於 Demo；
- 不得被解讀為真實工廠、真實設備所有權、實際客戶或真實證書的說明。

生成影像可以高度擬真，但必須使用虛構、無品牌的環境，不得加入法人名稱、Logo、證書號碼、客戶商標或不可證實的設備型號。客戶正式上線前，應以客戶提供或經客戶書面確認可使用的真實素材取代需要形成企業事實承諾的影像。

## 9. 範本最低完成標準

範本標記為 `ready` 前必須具備：

- 清楚的產業定位與買家角色。
- 完整首頁敘事，不是只有 Hero。
- 至少一種產品／能力呈現。
- 至少一個信任區塊。
- 至少一個明確 CTA。
- 符合影像品質規格的完整資產組，所有影像都有來源與用途紀錄。
- Demo RFQ 或 Contact 互動。
- 桌機及手機可用。
- 鍵盤可操作、合理色彩對比、表單有 label。
- 所有顯示資料符合共用 TypeScript contract。
- `npm run type-check`、`npm run lint`、`npm run build` 通過。

## 10. 未來產品化規則

客戶選定範本後，產品化分成兩層：

1. 保留範本視覺與頁面元件。
2. 以 adapter 將本地資料來源替換為 ForgeBase API。

```ts
// Demo
const products = precisionMachiningDemo.products;

// 正式客戶網站
const products = await forgeBaseAdapter.getProducts({ tenantId, locale });
```

若範本需要 ForgeBase 尚不存在的能力，必須標記為：

- 可映射至既有標準欄位；
- 可透過擴充欄位承載；或
- 需要客製開發／進入產品 Roadmap。

不得在未記錄差異的情況下，為單一客戶直接修改 ForgeBase 核心資料模型。

## 11. 範本審查清單

- [ ] 視覺不是既有手工具網站的換色版本。
- [ ] 與所有 `ready` 範本相比，首頁首屏、主要導覽及核心內頁的版面骨架均有明顯差異。
- [ ] 至少在資訊架構、內容密度、卡片／列表呈現、互動方式、CTA 流程五項中的三項採用不同設計策略。
- [ ] 不直接複製另一範本的 Hero、產品卡、規格區、信任區或 Footer 組合；共用元件只負責資料契約與 Demo 安全提示。
- [ ] 具備主視覺、製程／能力、品質／信任及產品／應用影像，不含 placeholder。
- [ ] 每張影像都有用途、alt、來源及 Demo 限制紀錄。
- [ ] 產業資訊架構符合該產業採購決策。
- [ ] manifest、資料與 CTA 意圖符合 contract。
- [ ] 沒有 API、資料庫、追蹤或外寄副作用。
- [ ] 所有假資料都有 Demo 性質，不冒充真實企業。
- [ ] 表單提交只在瀏覽器記憶體中處理。
- [ ] 手機版及鍵盤操作通過。
- [ ] 靜態建置通過。
- [ ] 已記錄未來 ForgeBase 串接映射。

## 12. 跨範本差異化規則

每套 Demo 都必須有自己的「設計指紋」，不能只替換品牌、配色、圖片或文案。開始製作前，Brief 必須先定義下列項目，並與現有 `ready` 範本交叉檢查：

1. **視覺語言**：字體性格、色彩邏輯、圖像比例、邊框／圓角、留白與動態節奏。
2. **首頁骨架**：Hero 結構、首屏資訊量、內容區塊順序及頁面節奏。
3. **導覽模式**：產品導向、應用導向、解決方案導向或資源導向，不固定套用同一組選單。
4. **核心瀏覽模式**：例如規格表、篩選型錄、系統架構圖、材料比較器、案例敘事或包裝配置器。
5. **轉換路徑**：Drawing RFQ、Equipment RFQ、Sample Request、Consultation、Datasheet 或 Configuration RFQ，依產業決策流程設計。
6. **證據呈現**：檢驗報告、性能資料、認證、案例、安裝流程、服務網絡等，選擇符合該產業信任機制的形式。

允許共用的是 ForgeBase 資料契約、CTA intent、無副作用表單機制、可及性要求與 Demo 揭露。最終視覺組件與頁面編排不得因共用 contract 而趨於同質化。

每套範本進入 `ready` 前，必須至少與前兩套已完成範本進行桌機首頁、手機首頁、產品／方案頁及 RFQ 頁的並排比較；若第一眼看起來像同一網站換皮，該範本不得通過驗收。
