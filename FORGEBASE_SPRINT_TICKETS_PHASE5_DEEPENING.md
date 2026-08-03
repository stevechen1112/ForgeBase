# ForgeBase Phase 5 Sprint 票：深化與規模化（Deepening & Scale）

> 對應文件：`FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md` §8（P5 中期深化）、串接計畫 Phase 3–4 接縫
> Roadmap 階段：Phase 5「深化與規模化」（線 C 後半＋E 後半）
> 執行日期：2026-08-03 ｜ 狀態：**FB repo 範圍完成**（CF 端與商業定價見「未涵蓋」）

---

## 票務總表

| 票 | 內容 | 實效計畫 | 狀態 |
|----|------|---------|------|
| T5.1 | 內容→成交歸因 API（`GET /tracking/attribution/content`） | §6.2 深化／串接 Phase 3 | ✅ |
| T5.2 | 成交原因回寫 intent（`GET /tracking/intent/outcome-feedback`，observational） | §8.3 | ✅ |
| T5.3 | E2E 成長迴路測試＋跨租戶污染測試 | §8.1 | ✅ |
| T5.4 | Managed Growth Add-on 定價與承諾 | §8.2 | ⏸ 待商業決策（見下） |
| T5.5 | 票文件＋Roadmap 收尾 | — | ✅ |

---

## 實作明細

### T5.1 內容→成交歸因（回答「哪種內容帶來會成交的單」）

`GET /tracking/attribution/content?days=90`：

- 期間內有 `source_page` 的 RFQ，依 slug 子字串對照 `pages` 表
- 依 **page_type 聚合**：rfq／qualified_rfq／quoted／won＋won_rate_pct（依成交排序）
- 對照不到的來源頁獨立一桶 `__unmatched__`（外部或直接輸入 URL），數字誠實呈現
- CF 串接完成後，blog_post 桶即直接回答「這批 SEO 文章帶來幾件會成交的單」

### T5.2 成交原因回寫 intent（§8.3，observational）

`GET /tracking/intent/outcome-feedback`：

- 取所有連結訪客的 RFQ，比較「成交單訪客」vs「全體 RFQ 訪客」的四 facet 平均值
- 每 facet 輸出 **won_lift**（成交組為全體的幾倍）；lift ≥ 1.5 提示「可考慮提高權重」
- **明確標記 observational：不自動修改評分權重**，調整需人工確認（誠實原則：相關≠因果）

### T5.3 E2E＋租戶污染測試（§8.1）

`api/tests/test_e2e_growth_loop.py::test_full_growth_loop_end_to_end` 一條完整迴路：

1. 內容頁（blog_post）建立
2. 訪客事件（認證頁 ×3＋規格下載）→ facets 累積＋「為何 Hot」解釋
3. RFQ 送出（帶 visitor_id＋source_page）→ 品質 ≥70＋SLA 計時
4. 狀態機 new→assigned→quoted→negotiation→won(原因) → 首回／報價時間自動記錄
5. outcomes（Qualified 計數＋來源頁）、funnel（won≥1、negotiation 歸零）、
   attribution（blog_post 桶 won≥1）、outcome-feedback（won 樣本≥1）、task-queue（已結案不卡 SLA）全部反映
6. **跨租戶污染**：tenant B 在 outcomes/funnel/attribution/feedback/task-queue/reply-assist 全部為空或 404

### T5.4 Managed Growth Add-on 定價（§8.2）— 待商業決策

包裝素材已齊（可量化的承諾點）：合格 RFQ 數、首回 SLA 達成率、內容上線數（CF）、驗證通過率（CF）。
但**定價金額與承諾門檻屬商業決策**，需要你（經營者）拍板，不應由工程端編造數字。
建議決策項目：月費級距、合格 RFQ 承諾下限、未達標補償條款、與 CF 訂閱的綑綁方式。

---

## 驗證

- 新增 1 E2E test 通過；Phase 4+5 合計 10 tests 通過
- 全量回歸 **136 passed**（既有環境性失敗 2 個：`agent_platform` 模組缺失，與本次無關）

## 未涵蓋

- **CF 端（ContentFlow repo）**：串接 Phase 3–4 的 CF 側工作（歸因資料回傳、學習迴路消費 `trust-check`／`outcome-feedback`）
- **Managed Add-on 定價**：待商業決策（T5.4）
- **intent 權重自動調整**：刻意不做（observational 原則）；未來若要自動化，需另立票並加人工確認閘門
