# ForgeBase Master Roadmap：全套計畫執行總表

> [!WARNING]
> **舊 roadmap，已不再是唯一執行總表。** 本文保留 2026-08-03 的 ContentFlow 與五階段工作線背景；目前產品北極星、四分類、完成度與剩餘 Gate，請以 `FORGEBASE_NORTH_STAR_CORE_GAP_IMPLEMENTATION_PLAN_2026-08-26.md`、`FORGEBASE_FUNCTION_MODULE_COMPLETENESS_AUDIT_2026-08-15.md` 及 `FORGEBASE_DOCUMENT_AUTHORITY_INDEX_2026-08-28.md` 為準。

文件日期：2026-08-03  
狀態：FB 範圍 Phase 1/3/4/5 完成；Phase 2a（FB 接收端）完成；待 CF 端開工與部署

---

## 0. 本文件目的

我們過去產生了多份策略與計畫文件，各自涵蓋一部分。**本文件是唯一的執行總表**：把三份計畫收斂成五條工作線、五個階段、每階段的可驗收里程碑，讓任何人打開這一頁就知道「全套計畫做到哪、下一步是什麼」。

原則：

1. **每階段都上線**，不憋大招——避免「做三個月沒人用到」的最大風險。
2. **A 地基是所有線的鎖**，未完成前其餘線不動資料庫。
3. 各子文件保留細節；本文件只追蹤階段、里程碑、狀態。

---

## 1. 文件地圖

```
DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md  ← 主策略（北極星：每月 Qualified RFQ）
└─ FORGEBASE_MASTER_ROADMAP.md（本文件）   ← 執行總表
    ├─ FORGEBASE_SPRINT_TICKETS_P0_SPEED.md      ← 線 A＋B 工程票（T1–T11）
    ├─ CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md  ← 線 C 串接計畫（Phase 0–4）
    │   └─ CF_FB_PUBLISH_CONTRACT.md              ← 線 C 發佈 API 契約
    ├─ FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md      ← 線 D＋E 設計依據（P0–P5）
    ├─ FORGEBASE_SPRINT_TICKETS_PHASE3_INTENT.md   ← Phase 3 票（T3.1–T3.6）
    ├─ FORGEBASE_SPRINT_TICKETS_PHASE4_OUTCOMES.md ← Phase 4 票（T4.1–T4.6）
    ├─ FORGEBASE_SPRINT_TICKETS_PHASE5_DEEPENING.md← Phase 5 票（T5.1–T5.5）
    ├─ FORGEBASE_DEPLOY_SETUP.md                   ← 部署／環境變數／回填／營運設定
    └─ FORGEBASE_REPAIR_OPTIMIZATION_PLAN.md      ← 線 A 的完整修復清單
```

---

## 2. 五條工作線

| 線 | 內容 | 細節文件 | 粗估工期（1–2 名工程師） |
|----|------|----------|--------------------------|
| **A. 地基** | migration 鏈、tenant 隔離、secrets | Sprint 票 T1–T4 | 1–2 週 |
| **B. 接住商機** | 首回速度、自動回覆、時區 SLA、品質分數 | Sprint 票 T5–T11 | 1–2 週 |
| **C. 帶來流量** | CF↔FB 串接（契約→發佈→歸因→學習） | 串接計畫 Phase 0–4 | 4–8 週 |
| **D. 看懂買家** | Intent facets、Dynamic CTA、信任內容標準 | 實效計畫 §4 | 2–3 週 |
| **E. 成果與閉環** | 回覆品質、客戶儀表板、成交漏斗、顧問工作台、P5 深化 | 實效計畫 §5.4–§8 | 4–6 週 |

---

## 3. 相依關係

```
A 地基 ──┬──> B 接住商機 ──> E 成果與閉環
         ├──> C CF 串接（FB 端要加欄位、開 endpoint）
         └──> D 看懂買家（分數欄位要動 DB）

C 可與 B／D 平行（C 的大部分工作在 ContentFlow 端）
D 可與 C 平行
E 依賴 B（SLA／品質分數資料）與 C Phase 3（內容歸因）
```

---

## 4. 五個階段與里程碑

### Phase 1（第 1–2 週）：地基＋接住商機 — 線 A＋B

- 範圍：Sprint 票 T1–T11 全數。
- **里程碑**：高品質詢價 1 分鐘內推到業務手機；買家 5 分鐘內收到專業確認；SLA 以買家時區計時；Admin 列表依品質×SLA 排序。
- **Gate**：`FORGEBASE_SPRINT_TICKETS_P0_SPEED.md` 驗收總表全勾。
- 狀態：**開工中（T1）**。

### Phase 2（第 3–6 週）：CF↔FB 串接打通 — 線 C（可與 Phase 3 平行）

- 範圍：串接計畫 Phase 0–2（契約落實、tenant 對接、發佈流程、HTML 消毒、快取失效）。
- **里程碑**：ContentFlow 文章正式發佈進 ForgeBase 客戶網站並通過線上驗證。
- **Gate**：串接計畫 §6 技術 Gate 相關項。

### Phase 3（第 5–8 週）：看懂買家 — 線 D

- 範圍：Intent Score 2.0 facets、facet→CTA、AI Product Advisor 收斂為「問出可詢價需求」、信任內容標準回饋 CF brief。
- **里程碑**：Admin 能依 facet 篩出「信任驗證高但尚未 RFQ」名單；系統能說出訪客「為何 Hot」。
- **Gate**：實效計畫 §4.5 驗收項。

### Phase 4（第 7–10 週）：成果與閉環 — 線 E 前半

- 範圍：回覆品質輔助（§5.4）、客戶儀表板（§6.1）、成交漏斗（§6.3）、顧問工作台（§7）。
- **里程碑**：客戶首屏五項上線；漏斗從流量追到成交；顧問一個入口清「今日必處理」。
- **Gate**：實效計畫 §6.4、§7.3 驗收項。

### Phase 5（第 11 週起）：深化與規模化 — 線 C 後半＋E 後半

- 範圍：串接 Phase 3–4（內容→RFQ 歸因、學習迴路）、E2E／契約測試、Managed Add-on 定價、成交原因回寫 intent 權重。
- **里程碑**：系統能回答「哪種內容帶來會成交的單」，並反哺內容策略。
- **Gate**：實效計畫 §11、串接計畫 §6 全表。

---

## 5. 總時程與誠實前提

- **樂觀 3 個月、務實 4 個月**（小團隊、Phase 2 與 3 平行）。
- 三個會拖慢的現實：CF 跨產品協調、多租戶既有資料遷移（T2）、現有客戶營運併行。
- **第 1 階段投資報酬率最高**：即使後續暫停，A＋B 已讓現有詢價回得快、接得準。後續階段是放大器。

---

## 6. 進度追蹤

| Phase | 狀態 | 完成日期 | 備註 |
|-------|------|----------|------|
| 1. 地基＋接住商機 | ✅ 完成（T1–T11 全數交付） | 2026-08-03 | migrations 0045–0048；92 tests passed；前端 tsc 通過；人工部署清單見 Sprint 票驗收總表 |
| 2. CF↔FB 串接 | 🔵 進行中（Phase 2a FB 接收端完成） | — | 2026-08-03：sanitize／meta-only／revalidate／idempotency／slug 查詢驗證，migration 0049，14 tests passed；CF 端（publisher adapter）待 ContentFlow repo 開工 |
| 3. 看懂買家 | ✅ 完成（T3.1–T3.6 全數交付） | 2026-08-03 | migration 0050；Intent facets＋解釋字串、facet 篩選 API＋前端、facet→CTA、Advisor 可詢價摘要、信任內容標準端點；126 tests passed；票文件見 `FORGEBASE_SPRINT_TICKETS_PHASE3_INTENT.md` |
| 4. 成果與閉環 | ✅ 完成（T4.1–T4.6 全數交付） | 2026-08-03 | migration 0051；狀態機 negotiation＋成交/流失原因必填、回覆品質輔助＋範本庫、outcomes 首屏五項 API、流量→成交漏斗、顧問任務佇列、前端 outcomes/tasks 頁＋RFQ reply-assist；136 tests passed；票文件見 `FORGEBASE_SPRINT_TICKETS_PHASE4_OUTCOMES.md` |
| 5. 深化與規模化 | 🔵 FB 範圍完成（T5.1–T5.3、T5.5） | 2026-08-03 | 內容→成交歸因 API、intent outcome-feedback（observational）、E2E 成長迴路＋跨租戶污染測試；全量回歸 136 passed（既有 2 個 agent_platform 環境性失敗檔案除外）；票文件見 `FORGEBASE_SPRINT_TICKETS_PHASE5_DEEPENING.md`；**待辦**：CF 端學習迴路（ContentFlow repo）、Managed Add-on 定價（商業決策） |

（每完成一階段更新此表；票級進度見 Sprint 票文件。）

---

## 7. 修訂紀錄

| 日期 | 內容 |
|------|------|
| 2026-08-03 | 初版：將三份計畫收斂為五線五階段總表；Phase 1（T1）開工。 |
| 2026-08-03 | Phase 1 全數完成：T1 migration 鏈修復、T2 租戶 email 隔離、T3 tracking 13 處隔離缺口、T4 secrets 止血、T5 即時推播（LINE＋品質 gate）、T6 自動確認信、T7 時區感知 SLA、T8 首回統計、T9 品質分數、T10 貿易欄位、T11 品質×SLA 列表。92 tests passed。 |
| 2026-08-03 | Phase 2a（FB 接收端）完成：依 `CF_FB_PUBLISH_CONTRACT.md` 落地 HTML sanitize（白名單，stdlib）、meta-only 端點（`PATCH /content/pages/{id}/meta`）、on-demand revalidate（FB→web `POST /api/revalidate`）、Idempotency-Key（migration 0049）、list 端點 auth tenant 覆寫（修復 CF slug 查詢盲點）。106 tests passed（全量回歸）。 |
| 2026-08-03 | Phase 3 完成：Intent Score 2.0 四 facets（migration 0050）＋「為何 Hot」解釋字串、Admin facet 篩選（API＋intent 頁）、facet→CTA 三規則、AI Advisor 可詢價 slots（用途/規格/交期）＋摘要寫入 RFQ prefill、信任內容標準 `trust-check` 端點。126 tests passed。 |
| 2026-08-03 | Phase 4 完成：狀態機加 `negotiation`＋成交/流失原因必填（migration 0051，`ck_rfq_status` 重建）、回覆品質輔助（checklist／Quote Readiness／`reply_templates` 範本庫＋`reply-assist` 端點）、`GET /tracking/outcomes` 客戶首屏五項、`GET /tracking/funnel` 流量→成交七層漏斗（含瓶頸層）、`GET /ops/task-queue` 顧問任務佇列、前端成果總覽／今日必處理頁＋RFQ 詳情 reply-assist 面板。136 tests passed。票文件：`FORGEBASE_SPRINT_TICKETS_PHASE4_OUTCOMES.md`。 |
| 2026-08-03 | Phase 5（FB 範圍）完成：`GET /tracking/attribution/content` 內容→成交歸因（page_type 聚合＋won_rate）、`GET /tracking/intent/outcome-feedback` 成交 facet lift（observational，不自動改權重）、E2E 成長迴路＋跨租戶污染測試（`test_e2e_growth_loop.py`）。全量回歸 136 passed。票文件：`FORGEBASE_SPRINT_TICKETS_PHASE5_DEEPENING.md`。待辦：CF 端學習迴路、Managed Add-on 定價（商業決策）。 |
