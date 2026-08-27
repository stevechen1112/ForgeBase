# Custom Packaging Manufacturing

- Status：`ready`
- Buying motion：結構評估、尺寸與材質配置、MOQ、打樣、印刷與報價
- Buyer roles：Packaging engineer、Brand operations manager、Procurement manager
- Core promise：在報價前把產品、結構、材質、印刷、數量與打樣決策放進同一份 Packaging Brief。

## Site map

`/`、`/products`、`/products/[slug]`、`/applications`、`/capabilities`、`/about`、`/rfq`

三個 package-system detail routes：`/products/ship-s1-mailer`、`/products/fold-f2-carton`、`/products/present-r3-rigid-box`。

## Distinctive experience

- 鮮明鈷藍、番茄紅、亮黃色與奶油紙張，版面像包裝打樣工作桌。
- 首屏是組裝盒、展開刀模與紙材插頁，不採工廠或型錄構圖。
- Pack Builder 即時整理結構、紙材、印刷、數量與適合的樣品階段。
- Capability 依結構設計、打樣／校樣、production handoff 的順序敘事。
- CTA 是 configuration-led Packaging Brief，不是單純聯絡表或材料樣品表。

## Assets

包裝系統 Hero、瓦楞郵寄盒、彩印折疊盒、精裝盒、打樣現場與社群預覽均已建立，詳見 `ASSETS.md`。

## ForgeBase gaps proved

尺寸、材質、印刷、表面處理、MOQ 與樣品階段可映射到 Product.attributes 和 RFQ custom fields；真正由尺寸生成製造刀模仍需受控結構庫或 parametric dieline service，不屬於靜態 Demo。
