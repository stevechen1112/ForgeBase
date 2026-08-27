# Engineering Materials

- Status：`ready`
- Buying motion：材料選型、技術證據評估、文件審查、樣品與技術諮詢
- Buyer roles：Materials engineer、R&D engineer、Technical buyer
- Core promise：把溫度、負載、環境與加工條件轉成可檢視的候選材料與證據脈絡。

## Site map

`/`、`/products`、`/products/[slug]`、`/categories/[slug]`、`/applications`、`/certifications`、`/resources`、`/about`、`/rfq`

三個 grade detail routes 與三個 material-family routes 均由 ForgeBase-style data records 靜態生成。

## Distinctive experience

- 首屏是暖白材料樣本檔案桌，而不是工廠、設備或電子型錄。
- Material Lens 以熱、負載與設計優先條件重排候選材料。
- 主視覺採暖白紙張、深藍技術墨色、珊瑚橘選取記號與 Georgia 編輯字體。
- 等級頁以 property sheet 表達數值、條件與證據狀態。
- 樣品 CTA 保留應用、環境、供應形態與候選等級，而非一般 RFQ。

## Assets

材料檔案桌、性能聚合物、輕量合金、技術陶瓷、材料測試實驗室與社群預覽均已建立，詳見 `ASSETS.md`。

## ForgeBase gaps proved

材料等級與性能可映射至 Product.attributes；TDS、SDS、方法、條件與 revision history 仍需要受控文件 adapter，Material Lens ranking 也需要正式的 rule schema 才能進入 production。
