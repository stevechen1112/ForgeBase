# ForgeBase Sprint 票 — Phase 3「看懂買家」（Intent 層）

建立日期：2026-08-03
狀態：✅ 全部完成（T3.1–T3.6）
上位計畫：[FORGEBASE_MASTER_ROADMAP.md](./FORGEBASE_MASTER_ROADMAP.md) Phase 3、
[FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md](./FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md) §4（P1 Intent 層）

**目的**：讓系統從「有分數」進化到「像採購助理」——能說出訪客**為何 Hot**、依採購面向（facets）篩名單、
CTA 依訪客狀態推下一步、AI 顧問問出可詢價需求、信任內容有最低品質標準。

---

## T3.1 Intent Score 2.0 — 採購 Facets 引擎 ✅

對應：§4.1

| 項目 | 內容 |
|------|------|
| 新服務 | `api/app/services/intent_facets.py` |
| Facets | `product_interest`／`trust_validation`／`procurement_readiness`／`urgency` |
| 映射 | event_name 主映射＋`page_view` 依 page_type 歸屬；facet 分數以實際 score_delta 累積（沿用租戶自訂權重） |
| 解釋字串 | `build_intent_explanation()`：「48h 內 3 次認證／產能頁 + 下載規格表 + 進 RFQ 未送出」 |
| 模型 | `Visitor` 新增 4 個 facet 欄位（indexed）＋`intent_explanation` |
| Migration | `0050_visitor_intent_facets` |
| 接入 | `events.py` `_upsert_visitor` 每事件累積 facet；`receive_event` commit 前重建解釋字串（近期 50 事件，tenant 過濾） |

## T3.2 Admin facet 篩選 ✅

對應：§4.1 輸出要求、§4.5 驗收 1

| 項目 | 內容 |
|------|------|
| API | `GET /tracking/visitors` 新增 `facet`、`facet_min`、`has_rfq`、`sort` 參數；回應含 `facets` 與 `intent_explanation` |
| has_rfq | `tracking_events` EXISTS 子查詢（`rfq_submit`） |
| 詳情 | `GET /tracking/visitors/{id}` 同步帶 facets＋explanation |
| 前端 | `admin/.../dashboard/intent/page.tsx`：facet 篩選器＋has_rfq 篩選器＋「為何 Hot」欄（解釋字串＋facet badges）＋「信任驗證高但尚未 RFQ」提示徽章 |

## T3.3 facet → CTA 規則 ✅

對應：§4.2

| 項目 | 內容 |
|------|------|
| 實作 | `dynamic_cta.py` 新增 `facets` 參數與 `_facet_action_override()` |
| 規則 | 採購準備高（≥15）→ RFQ 優先；產品興趣高＋信任低 → download（補信任）；產品興趣高＋信任夠 → comparison 深化 |
| 個人化 | facet 訊號的 `headline_prefix`／`facet_reason` 覆寫 stage 預設 |
| 接入 | `ai_intelligence.py` dynamic-cta 端點從 visitor 讀 facets 傳入 |

## T3.4 AI Product Advisor 收斂為「問出可詢價需求」 ✅

對應：§4.3

| 項目 | 內容 |
|------|------|
| 新 slots | `use_case`（用途）、`spec_detail`（規格）、`lead_time`（交期），補齊既有 quantity／program_type／packaging／market |
| 追問順序 | 高意圖時：quantity → use_case → spec_detail → lead_time，逐一補齊 |
| 摘要 | `summarize_quotable_needs()`：結構化 slots＋quantity_hint（正規萃取數量）＋missing 清單＋可讀摘要句 |
| 寫入 RFQ | `chat_service.create_handoff`：摘要寫入 prefill `requirement_summary`（進 RFQ 草稿 URL）＋`chat_rfq_handoff` 事件 properties |

## T3.5 信任內容標準 ✅

對應：§4.4

| 項目 | 內容 |
|------|------|
| 新服務 | `api/app/services/trust_content_standards.py` |
| 認證頁 | 證書可下載（PDF 連結）、標示效期、具名發證機構 |
| 產能頁 | 實際數字（≥2 個含單位數值）、設備／檢驗設備清單 |
| 案例頁 | 具名國家、具名產業、問題→解決敘事 |
| 端點 | `GET /content/pages/{id}/trust-check`（editor 權限＋tenant 隔離），輸出逐項 checklist 與分數，可作 CF brief 輸入 |

## T3.6 驗收測試 ✅

對應：§4.5

- 檔案：`api/tests/test_intent_facets.py`，**20 tests passed**
- 單元：facet 映射、累積、解釋字串、CTA 覆寫三規則＋fallback、摘要萃取、slot 追問順序、信任 checklist 四類
- 整合：`test_facet_cta_rfq_path_end_to_end` — certification_view×3 → spec_download → cta_click → rfq_start → rfq_submit 完整事件鏈，驗證 facet 篩選、has_rfq 過濾、解釋字串、timeline 事件鏈
- 整合：trust-check 端點（滿分案例＋跨租戶 404）

---

## 驗收總表（§4.5）

| 驗收項 | 狀態 |
|--------|------|
| Admin 可依 facet 排序／篩選 visitor | ✅ API＋intent 頁篩選器 |
| 至少一條「facet → CTA → RFQ」路徑有事件與轉換紀錄 | ✅ `test_facet_cta_rfq_path_end_to_end` |
| 系統能說出訪客「為何 Hot」 | ✅ `intent_explanation` 逐事件重建，前端呈現 |
| 里程碑：篩出「信任驗證高但尚未 RFQ」名單 | ✅ `?facet=trust_validation&facet_min=10&has_rfq=false`＋前端一鍵組合 |

**全量回歸：126 passed（含 Phase 1/2 既有測試）；admin tsc 通過。**

## 人工／後續待辦

1. 部署執行 `alembic upgrade head`（migration 0050）。
2. 既有訪客的 facets 為 0（新事件起才累積）；如需補算，可用 `intent_facets.recompute_facets()` 寫一支 backfill script（未交付，需要時另開票）。
3. CF 側消費 trust-check：ContentFlow 產生認證／產能／案例 brief 時呼叫 `GET /content/pages/{id}/trust-check` 做品質門檻（CF repo 工作）。

## 修訂紀錄

| 日期 | 內容 |
|------|------|
| 2026-08-03 | T3.1–T3.6 全數交付；migration 0050；20 tests passed；全量回歸 126 passed |
