# ForgeBase 首頁切版技術文件 (溝田建築設計株式会社 風格)

## 1. 概述
本文件記錄了基於「溝田建築設計株式会社」網站首頁設計圖所開發的首頁 HTML 靜態切版技術細節。此切版主要作為版面結構、排版比例與視覺風格的參考原型，未來可進一步整併至 ForgeBase 的 Next.js / React 前端專案中。

## 2. 技術選型
* **標記語言**: HTML5
* **CSS 框架**: [Tailwind CSS](https://tailwindcss.com/) (原型階段透過 CDN 引入，以快速套用 Utility Classes)
* **字體服務**: Google Fonts
* **圖片佔位**: [Picsum Photos](https://picsum.photos/) (用於暫代原本設計圖中的實景照片)

## 3. 視覺設定 (Design Tokens)
為了還原日系建築網站的高級與沉穩感，在 Tailwind 的設定檔 (`tailwind.config`) 中擴充了以下主視覺參數：

### 3.1 顏色 (Colors)
* **`brand-brown` (`#574B42`)**: 深裸棕色。作為 Concept 區塊背景與部分強調文字，帶來溫潤且穩重的視覺感受。
* **`brand-beige` (`#F9F7F3`)**: 灰米黃色/珍珠白。作為全站預設背景色，降低純白的刺眼感，提升閱讀舒適度。
* **`brand-accent` (`#BA8354`)**: 橘棕色/駝色。主要用於「聯絡我們 (お問い合わせ)」這類需要強烈 CTA (Call To Action) 促使點擊的按鈕與電話號碼。

### 3.2 字體 (Typography)
* **主字體 (`font-serif`)**: [Noto Serif JP (思源宋體)](https://fonts.google.com/specimen/Noto+Serif+JP)。
    * **說明**: 有別於常見的黑體，此設計大量採用明體（Serif）以強調傳統、工藝與優雅。HTML 中全局套用此字型，並針對不同標題調整字重 (Light `300`, Regular `400`, Medium `500`, SemiBold `600`)。
* **字距調整**: 大量使用 Tailwind 的 `tracking-widest` 與 `tracking-[0.15em]`、`tracking-[0.3em]` 來增加字元間距，這是日系排版中營造「呼吸感」與「高級感」的重要技巧。

## 4. 區塊結構解析 (Section Breakdown)

### 4.1 頂部導覽列 (Header)
* **佈局**: 絕對定位 (`absolute top-0 w-full z-10`)，浮動於滿版 Hero 圖片之上。
* **特性**: 包含左側 Logo 標題、中間的兩大塊選單群組 ( lg 以上尺寸才顯示 )，以及右側的「聯絡我們」按鈕與漢堡選單。
* **無障礙/互動**: 按鈕具備透明框線到實心填色的 Hover 漸變效果。

### 4.2 主視覺區塊 (Hero Section)
* **佈局**: 滿版高度 (`h-screen`)，背景採用 CSS 線性漸層疊加圖片 (`linear-gradient` + `url`) 以確保即使圖片偏亮，白色的主標語依然清晰可讀。
* **特點**: 右下角壓著一個浮動卡片 (`absolute bottom-10 right-10`)，用於展示最新的一則「お知らせ (公告)」，製造版面的層次感。

### 4.3 設計理念 (Concept Section)
* **佈局**: 深色背景 (`bg-brand-brown`) 與白色文字的對比區塊，上下留有大量的留白 (`py-32`)。
* **排版**: 採用置中排版，行高設置較寬 (`leading-loose`)，讓文字像詩句般呈現。
* **裝飾**: 使用絕對定位配置了散落的植物、門面、茶具圖片（目前使用佔位圖代替），打破方正排版的僵硬感。

### 4.4 施工案例 (Case Section)
* **佈局**: CSS Grid 排版 (`grid-cols-1 md:grid-cols-2 lg:grid-cols-4`)。
* **卡片設計**: 白底卡片，包含 4:3 比例的圖片 (`aspect-[4/3]`)、標號、標題（設定固定高度 `h-14` 以防文字折行導致卡片高度不齊），以及標籤（Tag）系統（如 #平屋、#子育て世代）。

### 4.5 資訊與部落格 (Information & Blog Section)
* **佈局**: 左右雙欄佈局 (`lg:grid-cols-2`)。
* **列表設計**: 
    * 左側（公告）純文字列，帶有日期與分類標籤。
    * 右側（部落格）帶有左側小縮圖 (`w-24 h-24 object-cover`) 的圖文列表配置。
* 左下方皆具備帶有圓形箭頭風格的「一覧を見る (查看全部)」連結。

### 4.6 橫幅導覽 (Banners / About us & For sale)
* **佈局**: 並排的兩塊滿版圖片按鈕 (`md:grid-cols-2`)。
* **互動特效**: 利用 `group` 與 `group-hover:scale-105` 達成滑鼠懸浮時畫面微微放大的質感動效，表面均覆蓋 `bg-black/40` 以凸顯白色文字。

### 4.7 聯絡我們 (Contact Section)
* **佈局**: 左側為標題描述，右側為操作表單區塊 (`lg:col-span-2`)。
* **對比凸顯**: 使用 `bg-white` 白底卡片，搭配品牌強調色 `brand-accent` 來突顯表單按鈕與電話號碼。

### 4.8 頁尾 (Footer)
* **佈局**: 頂部帶有淺灰色分隔線 (`border-t border-gray-300`)。左側包含公司聯絡資訊、Instagram 連結，右側則為多欄目的網站地圖導覽 (Sitemap)。
* **細節**: 附有「回到頂部」的圓形箭頭按鈕，以及最底部的版權宣告列。

## 5. RWD 響應式策略
* 採用 **Mobile-First** (手機優先) 策略。
* 預設情況下（如不帶前綴的樣式），各個區塊為單欄堆疊。
* 透過 `md:` (平板, >768px) 與 `lg:` (桌機, >1024px) 斷點，將佈局展開為多欄或網格結構（例如施工案例區塊從 1 欄 -> 2 欄 -> 4 欄）。

## 6. 後續開發建議 (整合至 ForgeBase)
1. **元件化 (Componentization)**: 將 HTML 依據區塊拆分成獨立的 React/Next.js 元件 (如 `<Hero />`, `<Concept />`, `<CaseStudy />` 等)。
2. **樣式遷移**: 將 `<head>` 內的 Tailwind Config 提取並合併到工作區內的 `tailwind.config.ts`。全局樣式（如 Google Fonts）加入 `app/globals.css` 中。
3. **資料抽離**: 將施工案例、公告、部落格文章等寫死的靜態文字，改由 props 或 API 取得，甚至串接此專案既有的 SQLAlchemy / FastAPI 後端資料庫。
4. **圖片資源**: 將佔位用的 `picsum.photos` 連結替換為 Next.js `<Image />` 標籤，並導入正式的高畫質設計原圖。