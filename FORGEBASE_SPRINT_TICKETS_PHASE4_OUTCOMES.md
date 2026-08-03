# ForgeBase Phase 4 Sprint 票：成果與閉環（Outcome & Closed Loop）

> 對應文件：`FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md` §5.4、§6、§7（P3 客戶成果面＋P4 顧問工作台）
> Roadmap 階段：Phase 4「成果與閉環」（線 E 前半）
> 執行日期：2026-08-03 ｜ 狀態：**全數完成**

---

## 目標

讓「實效」成為產品：客戶不登入複雜 Admin 也能說出「本月幾件合格詢價、誰在跟」；漏斗從流量追到成交，行銷與業務無法互相推託；顧問一個入口清「今日必處理」。同時補上決定「進不進 shortlist」的第一封回覆品質輔助。

---

## 票務總表

| 票 | 內容 | 實效計畫 | 狀態 |
|----|------|---------|------|
| T4.1 | 漏斗狀態機延伸：`negotiation` 狀態＋成交／流失原因必填＋`won_reason` 欄位＋`ck_rfq_status` 約束更新 | §6.3 | ✅ |
| T4.2 | 回覆品質輔助：回覆前 checklist、Quote Readiness、範本庫（`reply_templates`）＋匹配 | §5.4 | ✅ |
| T4.3 | 客戶成果儀表板 API（首屏五項）＋流量→成交漏斗 API | §6.1／§6.2／§6.3 | ✅ |
| T4.4 | 顧問工作台任務佇列 API | §7.1 | ✅ |
| T4.5 | 前端：成果總覽頁、今日必處理頁、RFQ 詳情 reply-assist 面板＋狀態原因輸入 | §6.1／§7.1 | ✅ |
| T4.6 | 驗收測試＋全量回歸 | §6.4／§7.3 | ✅ |

---

## 實作明細

### T4.1 漏斗狀態機（§6.3）

- `VALID_STATUSES` 加入 `negotiation`（進入談判層）。
- `StatusUpdate` 新增 `reason` 欄位；狀態轉為 `won`／`lost` 時**原因必填**（422），寫入 `won_reason`（新欄位）或 `lost_reason`。
- 首次轉 `quoted` 自動記 `quote_sent_at`（漏斗「報價送出」層的資料源）。
- Migration `0051_rfq_outcome_and_templates`：`won_reason` 欄位＋`reply_templates` 表＋重建 `ck_rfq_status` 檢查約束（含 negotiation）。

### T4.2 回覆品質輔助（§5.4）

- 新服務 `app/services/reply_quality.py`：
  - `build_reply_checklist(rfq)` — 六項檢查（規格／圖面／包裝／認證／Incoterms／數量），每項附英文建議反問句。
  - `quote_readiness(rfq)` — 0–100 分，≥80 視為可報價，列出缺口。
  - `suggested_questions(rfq)` — 依缺口產生最多 4 題反問。
  - `match_templates()` — 依買家國家→產品線→語系排序範本。
- 新模型 `ReplyTemplate`（租戶隔離，依產品線／國家／語系維護）。
- 端點：
  - `GET /tracking/rfqs/{id}/reply-assist` — checklist＋readiness＋反問＋匹配範本（帶買家國家）。
  - `GET/POST /tracking/rfqs/templates`、`PATCH/DELETE /tracking/rfqs/templates/{id}`（CRUD，tenant 隔離）。

### T4.3 成果儀表板與漏斗 API（§6.1–§6.3）

新檔 `app/api/v1/endpoints/growth_ops.py`：

- `GET /tracking/outcomes` — 客戶首屏五項：
  1. 本月 Qualified RFQ（品質 ≥70）與上月比較
  2. 平均首回時間（小時）＋ SLA 達成率（買家時區計時）
  3. RFQ 狀態漏斗（8 狀態快照）
  4. 本月 RFQ 來源頁 Top 5（`source_page` 歸因最小版，§6.2）
  5. 下週建議 3 條（規則產生：SLA 逾期催辦／高品質未指派／報價 7 天未進談判）
- `GET /tracking/funnel?days=30` — 七層漏斗：流量(sessions)→高意圖訪客→RFQ→Qualified→報價送出→進入談判→成交；每層附對上層轉化率，並標出**瓶頸層**。

### T4.4 顧問任務佇列（§7.1）

- `GET /ops/task-queue` — 五類任務：
  - SLA 逾期 RFQ（未結案，前 5 筆明細）
  - Hot 訪客 72h 內活躍但未送 RFQ（附 intent_explanation）
  - 低品質 RFQ 待過濾（<40 分）
  - 待核准內容（草稿頁數）
  - 線上驗證異常 — **誠實標記 `available: false`**：需 CF 串接（Roadmap Phase 2 CF 端）後提供

### T4.5 前端

- `admin/.../dashboard/outcomes/page.tsx` — 成果總覽：五張指標卡＋業務漏斗橫條圖（瓶頸層紅色標示）＋狀態漏斗＋來源頁表＋下週建議。
- `admin/.../dashboard/tasks/page.tsx` — 今日必處理：五類任務卡，嚴重度徽章、明細連結直達 RFQ/訪客。
- `admin/.../dashboard/rfqs/[id]/page.tsx` — 新增「回覆前檢查（Quote Readiness）」面板（checklist 勾項、建議反問、匹配範本可展開）；狀態選單加 `negotiation`；選 won/lost 時顯示**必填原因輸入框**。
- Sidebar：AI 工作台加「今日必處理」，詢價中心加「成果總覽」。

### T4.6 驗收測試

`api/tests/test_growth_ops.py` 9 tests 全數通過：

- checklist 缺口標記與反問句產生（單元）
- Quote Readiness 完整 RFQ 得 100 分（單元）
- 範本國家優先匹配（單元）
- 狀態機：negotiation 合法／quoted 自動記時／won/lost 無原因 422、附原因通過
- 範本 CRUD＋跨租戶 404
- reply-assist 端點六項 checklist＋買家國家＋範本匹配
- outcomes 首屏五項齊全＋**source_page 可回溯到 RFQ（§6.4 驗收）**
- funnel 七層齊全＋轉化率可查（§6.4 驗收）
- task-queue 五類任務聚合（§7.3 驗收）

全量回歸 **136 passed**（既有 2 個 `agent_platform` 環境性失敗與本次無關）；admin `tsc --noEmit` 通過。

---

## 部署注意事項

1. `alembic upgrade head`（migration 0051：`won_reason`、`reply_templates`、`ck_rfq_status` 重建）。
   ⚠️ 若 0051 已套過舊版（無約束重建），需 `downgrade 0050_visitor_intent_facets` 後再 upgrade。
2. 無新環境變數。
3. 建議為各租戶預建 2–3 個回覆範本（`POST /tracking/rfqs/templates`），reply-assist 才有範本可配。

## 未涵蓋（後續階段）

- 線上驗證異常任務 — 待 CF 串接（Phase 2 CF 端）。
- 內容→RFQ 深度歸因（article ↔ page 對照、CF 關聯）— Phase 5（串接 Phase 3–4）。
- 成交／流失原因回寫 intent 權重 — Phase 5（§8，observational）。
- 客戶層 Leads inbox 獨立介面（§7.2）— 目前以 RFQ 列表＋成果總覽覆蓋主要場景。
