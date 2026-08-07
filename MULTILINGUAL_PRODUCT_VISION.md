# ForgeBase 多語產品構想與可行性評估

**狀態：** **v1 實作完成（英文母語自動同步）**。導覽／頁尾 JSON 自動同步仍排除於第一期。  
**記錄日期：** 2026-08-07  
**相關討論：** 三組選單閉環驗證後，盤點現有多語並對照產品想像；其後開工實作。

---

## 1. 白話產品定義（客戶聽得懂的版本）

### 1.1 現況比較像什麼（實作前）

英文版官網做好了，中文要再一頁一頁自己補。AI 可以幫忙起草，但系統不會主動告訴你「哪裡還沒翻、哪裡原文改了中文卻還是舊的」，也**不會**在你改完母語後自動更新其他語言並上線。

### 1.2 產品負責人想像的「全套」（目標方向）

1. **全站範疇** — 不只商品頁，關於我們、FAQ、導覽等凡是官網上的文字都進多語。
2. **單一語系為基準** — **已拍板：以英文（`en`）為母語**；後台改英文內容後，LLM 同步新增或修正繁中（`zh-tw`）對應頁。
3. **後台欄位可切語系** — 同一內容維護畫面可切換語系手動編輯；發現 LLM 翻錯時，直接進該語系該欄位修改。
4. **不要術語庫當必填、不要「按過才上線」審核** — 採自動同步上線；錯了再事後手動改。

> 一句話：後台用**英文**維護全站；存檔後 AI 自動更新繁中並上線；每個欄位可切語系微調；不靠術語庫門檻，也不靠上架審核關卡。

### 1.3 UX 決策（已拍板）：拒絕厚重審核，保留無感防呆

**產品顧慮（合理）：** 審核機制若做成「待審清單／核准退回／多層狀態」，會明顯增加不值得的 UI／UX 負擔。

**已同意的原則：**

| 不要做（審核 UX） | 要做（幾乎無感的防呆） |
|---|---|
| 待審翻譯選單、核准／退回流程 | 存檔即同步、直接上線 |
| draft → review → approved 狀態機當主流程 | 手動改過的欄位靜默標記，下次自動同步**跳過該格** |
| 上線前強制人按一次 | 僅同步**失敗**時打 log／輕量提示；成功則安靜完成 |
| 術語庫當必填入場券 | 術語表可選 |

### 1.4 v1 已實作範圍

| 項目 | 狀態 |
|---|---|
| 母語 `en` → 目標 `zh-tw` 自動同步 | 已做（Professional `multilingual`） |
| 存檔觸發（product／category／page／application／faq／cert／capability／comparison／cta） | 已做 |
| `content_field_locks` 人工欄位勿覆蓋 | 已做 |
| Locale 正規化（前台 `zh-TW` → DB `zh-tw`） | 已做 |
| Product `model_number` 改為含 locale 唯一 | 已做 |
| FAQ `variant_key` 跨語系配對 | 已做 |
| Admin 假語系選項移除；LocaleSwitcher 文案與同頁切換 | 已做 |
| 導覽／頁尾 JSON 自動同步 | **未做（第一期排除）** |
| 日文等其他語系 | **未做** |

---

## 2. 關鍵程式入口

| 區域 | 路徑 |
|---|---|
| Locale 正規化 | `api/app/core/locale.py`、`web/src/lib/contentLocale.ts`、`admin/src/lib/i18n.ts` |
| 自動同步服務 | `api/app/services/locale_sync.py` |
| 翻譯白名單 | `api/app/services/translator.py` |
| 掛點 | `content_crud.py`、`products.py`、`categories.py` |
| Migration | `0059_locale_sync_v1`（locks／FAQ variant／model_number）+ `0060_drop_global_slug_unique_indexes`（同 slug 多語列） |
| 人工鎖定模型 | `api/app/models/content_field_lock.py` |
| LocaleSwitcher | `admin/src/components/ui/LocaleSwitcher.tsx` |

---

## 3. 覆蓋策略（已拍板）

- 人工改過的外文欄位：下次母語變更時**不得**被自動同步覆蓋。
- **不做**待審清單、核准／退回、上線前強制確認。

---

## 4. 刻意不納入（本想像／v1）

- Admin 後台介面本身多語化
- 無限語系一次承諾
- 術語庫當必填
- 上架前審核佇列／待審中心
- 導覽／頁尾自動同步（手維 JSON；讀取同時接受 `zh-TW`／`zh-tw`）
- Celery 級持久佇列（與 revalidate 相同用 in-process task）

---

## 5. 變更紀錄

| 日期 | 說明 |
|---|---|
| 2026-08-07 | 初版：記錄現況盤點、產品想像、可行性與分期建議；標記未開工 |
| 2026-08-07 | 補 UX 決策：拒絕厚重審核 UI；保留「人工欄位勿覆蓋」無感防呆 |
| 2026-08-07 | 母語定案英文；開工 v1：自動同步、locks、locale 統一、FAQ variant_key、Admin UX |
