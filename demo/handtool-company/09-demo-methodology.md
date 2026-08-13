# NorthForge Tools — Demo Company 建構方法論

> 本文件記錄 NorthForge Tools Co., Ltd. 這家 Demo 公司從零開始建構的完整方法論，  
> 供未來建立其他 Demo 垂直行業時複製、調整使用。

---

## 一、核心原則

### 為什麼要建構「極度真實」的 Demo 公司？

一個好的 SaaS Demo 最大的弱點是「一看就假」— 使用 lorem ipsum、假名字、假數字，  
或者產品類別過度通用（「Product A、Product B」）。  
當潛在客戶看到這種 Demo，他們很難代入自己的業務，轉換率低。

NorthForge 的建構原則是：**設計成像一家真實存在的台灣外銷五金工具廠**，  
讓目標受眾（外銷製造商採購者、品牌代工廠經理）在看到 Demo 時說「這就是我們公司」。

### 四個「真實感」指標

1. **行業術語正確**：使用 VDE、OEM/ODM、MRO、SKU、torque wrench 等業內詞彙
2. **公司規模可信**：不過度誇張（不是蘋果），有限定範圍（mid-sized export manufacturer）
3. **產品型號有邏輯**：`NFT-TW380`（NorthForge Torque Wrench, 3/8 inch drive）
4. **價值主張明確**：「不是最便宜，競爭於信任和文件管理能力」

---

## 二、五層建構架構

NorthForge 的建構遵循嚴格的「由上而下」順序，每一層都依賴上一層。  
跳過任何一層都會導致後面的內容不一致。

```
Layer 1: 公司藍圖（Company Blueprint）
         ↓ 確立定位、客群、產品柱、競爭策略
Layer 2: 企業簡介（Corporate Profile）+ 內容地圖（Content Map）
         ↓ 展開品牌敘事、確定網站每頁的核心訊息
Layer 3: 產品目錄（Product Masterlist）+ 應用場景（Applications）
         ↓ 用真實的型號、規格、用途填充資料庫
Layer 4: 視覺系統（Brand Visual System）+ 圖片腳本（Shot List）
         ↓ 為 AI 圖片生成制定一致的視覺語言
Layer 5: 行為資料（Page Briefs、CTAs、Nurture Sequences）
         ↓ 讓行銷功能（Analytics、Lead Capture）有實際內容展示
```

---

## 三、Layer 1 — 公司藍圖（Company Blueprint）

**目標**：在任何 UI 或文案動筆前，先回答「這是一家什麼公司」。

### 必須定義的六個維度

| 維度 | NorthForge 的答案 |
|------|------------------|
| 核心產品 | 扭力工具、絕緣電工具、敲擊工具、汽車服務工具、客製工具套組 |
| 地理定位 | 台灣外銷製造商（針對歐美市場採購者）|
| 市場定位 | 中高階，非最低價；以品質一致、文件完整為賣點 |
| 理想客戶 | 進口商、私標品牌、汽車零件商、工業 MRO 採購者 |
| 競爭差異 | OEM/ODM 彈性、包裝客製、出口文件管理 |
| 公司規模指標 | 中型（非大型集團、非小型貿易商）：30+ 年、ISO 9001、自有生產線 |

### 關鍵命名決策

- **公司名稱**：`NorthForge Tools Co., Ltd.`  
  「North」暗示台灣北部製造中心；「Forge」呼應金屬鍛造加工；「Co., Ltd.」符合台灣法人格式
- **品牌代號**：`NFT-` 前綴（NorthForge Tools）+ 品類縮寫 + 規格數字  
  例：`NFT-TW380`（Torque Wrench, 3/8 inch drive）、`NFT-ID006`（Insulated Driver, 6-piece set）

---

## 四、Layer 2 — 內容架構（Content Map + Corporate Profile）

**目標**：確立網站每個頁面要傳達的核心訊息。

### 內容地圖（Content Map）的作用

`02-site-content-map.md` 定義了以下內容的**期望清單**：
- 首頁（Homepage）：Hero 標語、Feature 區塊、CTA、客戶 logo 佔位
- 關於頁（About）：公司歷史、製造能力、品質指標
- 產品頁（Products）：分類架構、每個分類的核心賣點
- 應用場景頁（Applications）：行業別的解決方案
- 聯絡頁（Contact）：詢價流程、表單欄位

### 企業簡介的作用

`04-corporate-profile.md` 提供品牌敘事的原文，  
可以直接貼入 AI 寫手（Claude、GPT 等）作為公司背景，  
確保生成的行銷文案不至於偏離設定。

**重要做法**：在 `03-content-model-map.md` 中定義哪個 DB 欄位對應哪個 UI 區塊，  
這樣 seed 資料撰寫者和前端開發者之間不會有認知落差。

---

## 五、Layer 3 — 產品與應用場景資料（Catalog + Applications）

**目標**：用有邏輯的真實資料填充資料庫，而非亂填。

### 產品目錄的設計原則

1. **每個分類有 5–8 個 SKU**（不多不少，夠展示分類功能但不誇大）
2. **型號有意義**：buyers 看到型號就能理解產品類型和規格
3. **規格嚴謹**：`specifications` JSON 欄位填入真實工程參數（驅動尺寸、扭矩範圍、材質）
4. **SEO 欄位完整**：每個產品有 `seo_title`、`seo_description`，展示 SEO 功能

### 五個產品分類（模型）

| 分類 slug | 中文說明 | 代表產品 |
|-----------|--------|---------|
| `torque-and-socket-tools` | 扭力工具與套筒 | NFT-TW380, NFT-SS094 |
| `insulated-electrical-tools` | 絕緣電工具 | NFT-ID006, NFT-EK018 |
| `striking-and-workshop-tools` | 敲擊與工地工具 | NFT-DH045, NFT-EH24 |
| `automotive-service-tools` | 汽車服務工具 | NFT-AMBC7, NFT-AMSP5 |
| `custom-toolkits-and-storage` | 客製套件與收納 | NFT-KTBC89, NFT-KTFM42 |

### 六個應用場景（行業別）

| 場景 slug | 目標行業 |
|-----------|---------|
| `automotive-aftermarket-service` | 汽車售後服務業 |
| `industrial-maintenance-and-mro` | 工業保養 MRO 採購 |
| `electrical-installation-and-utility-work` | 電力安裝與公用事業 |
| `workshop-assembly-and-repair` | 工廠組裝與維修 |
| `private-label-tool-programs` | 私標工具項目規劃 |
| `field-service-and-mobile-maintenance` | 現場維修與移動服務 |

### M2M 關聯設計

`relationships.json` 定義了應用場景 ↔ 產品的多對多關係，  
這讓「相關產品」功能在 Demo 中有真實的數據可展示。

---

## 六、Layer 4 — 視覺系統（Brand Visual System + Image Generation）

**目標**：確保 AI 生成的所有圖片遵循一致的視覺語言，而非每張圖都像不同公司。

### `01-brand-visual-system.md` 的核心內容

- **主色**：Deep Navy `#1B2A4A`（工業專業感）+ Steel Blue `#4A90D9`（科技感）
- **輔色**：Precision Orange `#E8651A`（行動按鈕）
- **排除清單**（反範例）：
  - ❌ 工人對著鏡頭笑（消費者風格）
  - ❌ 誇張的焊接火花（戲劇化）
  - ❌ 電影院風格打光（偽裝攝影棚）
  - ❌ 亮橘色安全帽（工地安全宣傳風）
  - ✅ 整潔的組裝台、有標籤的零件收納、可見的品管站

### AI 圖片生成流程

圖片使用 **Google Gemini API**（model: `gemini-2.0-flash-preview-image-generation`）生成：

1. `02-image-shot-list.md`：確定需要哪些圖（按功能分類：hero、category、product、capability）
2. `03-image-prompts.md`：為每種圖寫詳細的正向提示詞 + 負向提示詞指引
3. `generation-jobs.minimum-demo.json`：機器可讀的生成任務清單
4. `generate_demo_images.py`：呼叫 Gemini API 的腳本，支援 `--only`、`--limit`、`--dry-run`

### 生成的圖片存放位置

- 原始圖：`demo/handtool-company/assets/generated/*.png`
- 公開服務：複製到 `web/public/demo/handtool-company/assets/generated/`
- 前端引用：`web/src/lib/demoAssets.ts`（集中管理所有 Demo 圖片路徑）

### `demoAssets.ts` 的架構

```typescript
// 集中映射，避免散落在各 component 中
const CATEGORY_HERO_BY_SLUG: Record<string, string> = { ... }
const PRODUCT_IMAGE_BY_MODEL: Record<string, string> = { ... }
const APPLICATION_IMAGE_BY_SLUG: Record<string, string> = { ... }

export function getCategoryHeroImage(slug: string): string | null
export function getProductImage(product, categorySlug?): string | null
export function getApplicationImage(slug: string): string | null
```

---

## 七、Layer 5 — 行為與行銷資料（Page Briefs、CTAs、Nurture）

**目標**：讓 ForgeBase 的行銷功能（Content Hub、Lead Capture、Automation）有真實的範例資料。

### Page Briefs（8 筆）

| 頁面 | 狀態 | 用途展示 |
|------|------|---------|
| Homepage | `live` | 主力首頁 |
| About Us | `live` | 企業簡介 |
| Products | `live` | 產品目錄入口 |
| Applications（全）| `live` | 應用場景入口 |
| Automotive Detail | `live` | 應用場景詳情 |
| Contact / Request Quote | `live` | 詢價頁 |
| New Product Launch Draft | `draft` | 展示草稿狀態 |
| Old Promo Page | `archived` | 展示封存狀態 |

### CTAs（4 種類型）

| 類型 | 行動呼籲 | 展示功能 |
|------|---------|---------|
| PDF 型錄下載 | "Download Product Catalog" | 資產下載追蹤 |
| 詢報價 | "Request a Quote" | 主要轉化 CTA |
| 展覽通知 | "Register for Trade Show" | 活動 CTA |
| 樣品請求 | "Request Sample Kit" | 中段轉化 |

### Nurture Sequences（2 組）

| 序列 | 觸發 | 目的展示 |
|------|------|---------|
| Welcome Series（4封）| 新訂閱者 | 自動化歡迎流程 |
| Re-engagement（3封）| 90天未開信 | 再行銷自動化 |

---

## 八、複製此方法論到新 Demo 垂直

### 替換項目 Checklist

建立新的 Demo 垂直（如：電子零件 / 食品加工設備 / 醫療器材）時，  
只需按以下順序替換內容：

```
[ ] 01-company-blueprint.md  → 替換行業、客群、產品柱
[ ] 02-site-content-map.md   → 調整頁面結構（如果行業需要不同頁面）
[ ] 04-corporate-profile.md  → 重寫企業敘事（保留結構，替換內容）
[ ] 05-product-master-catalog.md → 建立新行業的產品清單
[ ] 06-applications-and-capabilities.md → 替換客戶行業場景
[ ] 07-homepage-source.md    → 調整標語和 Feature 區塊
[ ] 08-about-source.md       → 調整沿革、數字指標
[ ] 01-brand-visual-system.md → 重新定義視覺色調（製造業 vs 醫療 vs 食品）
[ ] generation-jobs.*.json   → 撰寫新行業的圖片生成 Prompt
```

### 不需要替換的部分

- `web/` 前端：架構通用，只要 API 回傳正確資料就能自動呈現
- `api/` 後端：資料模型設計為通用，除非新行業需要特殊 schema 欄位
- `admin/` 後台：完全無需修改

### 時間估算

| 任務 | 預估時間（有詳細產業知識的情況下）|
|------|--------------------------------|
| Layer 1-2（藍圖 + 內容架構） | 2–3 小時 |
| Layer 3（產品 + 應用場景 seed data）| 4–6 小時 |
| Layer 4（視覺系統 + 圖片生成）| 2–3 小時 + Gemini API 生成時間 |
| Layer 5（行為資料）| 1–2 小時 |
| **合計** | **9–14 小時** |

---

## 九、已知限制與改進方向

### 目前已知的 Demo 畫面缺口

| 缺口 | 優先度 | 說明 |
|------|--------|------|
| 應用場景卡片無圖片 | 高 | `ApplicationCard.tsx` 未渲染 `hero_image_url` |
| 多數產品缺圖 | 中 | 只有 3 個型號有圖，其餘 29 個靠分類圖替代 |
| 管理後台缺乏完整 Demo 流程導覽 | 低 | 需要加入「Demo 導覽模式」功能 |

### 圖片服務架構

目前圖片放在 `web/public/demo/...` 目錄，由 Next.js 靜態服務，  
生產環境（`https://172.233.64.5`）需要在部署時將圖片一起同步。
未來改進方向：整合 Cloudflare R2 物件儲存，讓圖片可以獨立更新而不需重新部署。

---

## 十、相關檔案索引

| 檔案路徑 | 說明 |
|---------|------|
| `demo/handtool-company/content/00-index.md` | 所有 content 文件的目錄 |
| `demo/handtool-company/content/01-company-blueprint.md` | **Layer 1** 公司藍圖 |
| `demo/handtool-company/content/02-site-content-map.md` | **Layer 2** 網站內容地圖 |
| `demo/handtool-company/content/03-content-model-map.md` | DB 欄位對應 UI 說明 |
| `demo/handtool-company/content/04-corporate-profile.md` | **Layer 2** 企業簡介原文 |
| `demo/handtool-company/content/05-product-master-catalog.md` | **Layer 3** 產品目錄 |
| `demo/handtool-company/content/06-applications-and-capabilities.md` | **Layer 3** 應用場景 |
| `demo/handtool-company/content/07-homepage-source.md` | **Layer 2** 首頁文案原文 |
| `demo/handtool-company/content/08-about-source.md` | **Layer 2** 關於頁文案原文 |
| `demo/handtool-company/assets/01-brand-visual-system.md` | **Layer 4** 視覺系統規格 |
| `demo/handtool-company/assets/02-image-shot-list.md` | **Layer 4** 圖片需求清單 |
| `demo/handtool-company/assets/03-image-prompts.md` | **Layer 4** AI 圖片提示詞 |
| `demo/handtool-company/assets/generation-jobs.minimum-demo.json` | Gemini 生成任務清單（最小版）|
| `demo/handtool-company/assets/generation-jobs.full-demo.json` | Gemini 生成任務清單（完整版）|
| `demo/handtool-company/seed/generate_demo_images.py` | Gemini 圖片生成腳本 |
| `web/src/lib/demoAssets.ts` | 前端 Demo 圖片路徑集中管理 |
| `web/public/demo/handtool-company/assets/generated/` | 生產可用的圖片目錄 |
