# ForgeBase Sprint 工程票：P0 地基 ＋ 首回速度工程 ＋ Lead Quality Score

文件日期：2026-08-03  
母計畫：[FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md](./FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md) §9「最短實效路徑」

---

## 0. 本文件目的

把母計畫 §9「若只能先做三件」的前兩件（**P0 地基**、**首回速度工程＋Lead Quality Score**）拆成**可直接指派、可直接驗收**的工程票。每張票註明：目的（為什麼做）、檔案（改哪裡）、做法、驗收（怎麼算完成）、相依性。

**不追求一次做完母計畫全部內容**；本文件範圍外項目（Intent facets 前端、回覆品質輔助、客戶儀表板、顧問工作台）待本批驗收通過後再開下一批票。

### 兩週 Sprint 建議排程

| 週 | 票 |
|----|-----|
| W1 | T1（migration 鏈）→ T2（Contact tenant）→ T5（推播升級）、T9（品質分數後端） |
| W2 | T6（自動回覆）、T7（時區 SLA）、T8（首回統計）、T10（表單貿易欄位）、T11（Admin 排序） |
| 全程 | T3（tracking tenant filter）、T4（secrets）可平行由另一人處理 |

---

## P0 — 工程地基

### T1. Alembic migration 單一路徑 ✅（2026-08-03 完成）

- **目的**：乾淨 DB `alembic upgrade head` 一次到位；消除「測試手動補欄位」的隱性知識。
- **現況**：正式目錄 `api/app/db/migrations/versions/`（43 檔，head 為 `0041`）；`api/alembic/versions/` 另有 `0042–0044` 未掛入 `script_location`，且 `0044` 的 `down_revision` 與 `0043` 的 revision id 不一致。
- **已完成**：
  - `0042`、`0043` 原樣遷入正式目錄；`0044` 的 revision 改為 `0044_add_page_brief_agent_fields`、down_revision 改為 `0043_add_rfq_agent_draft_fields`（修復斷鏈）。
  - 孤兒目錄 `api/alembic/versions/` 三支檔案已刪除。
  - `api/tests/conftest.py` 的手動 ALTER TABLE 補丁已移除，改為 session 級 fixture 執行 `alembic upgrade head`。
- **驗證結果**：`alembic heads` 輸出單一 head（`0044_add_page_brief_agent_fields`）；新建乾淨 DB `upgrade head` rc=0，5 個 agent 欄位全部存在；臨時 DB 已刪除。
- **⚠️ 部署注意**：既有 dev／prod DB 若欄位是當年手動補的、`alembic_version` 停在 `0041`，直接 `upgrade` 會因欄位已存在而失敗。這些環境應先確認欄位存在後執行 `alembic stamp 0044_add_page_brief_agent_fields`，之後即回到正軌。

### T2. Contact email 改 tenant-scoped unique ✅（2026-08-03 完成）

- **目的**：多租戶下不同客戶可共用同一 email；防止跨租戶資料合併污染。
- **已完成**：
  - Model：`email` 移除全域 unique，新增 `UniqueConstraint("tenant_id", "email", name="uq_contacts_tenant_email")`。
  - Migration `0045_contacts_tenant_scoped_email`：drop `uq_contacts_email` → 建複合 unique；dev DB 已 `stamp 0044` + `upgrade head` 就位。
  - `contacts.py`、`rfqs.py` 的 dedup 查詢均改為 `email + tenant_id` 雙條件。
  - 新測試 `tests/test_contact_tenant_isolation.py`：跨租戶同 email 各自建檔、同租戶仍 dedup、Admin 列表隔離、RFQ upsert 同規則——**2 passed**。
- **⚠️ 部署注意**：其他既有環境需先 `alembic stamp 0044_add_page_brief_agent_fields` 再 `upgrade head`（同 T1 注意事項）。
- **相依**：T1 ✅。

### T3. Tracking／Visitor 聚合補 tenant filter ✅（2026-08-03 完成）

- **目的**：報表數字不被跨租戶污染（KPI 可信前提）。
- **審查方式**：子代理全面掃描 endpoints／services 中所有 Visitor／TrackingSession／TrackingEvent 查詢，區分「admin 可觸達需補」與「public 寫入／跨租戶背景 job 不需補」。
- **已修補（13 處）**：
  - `events.py`：`events_summary` 聚合補 tenant filter；`_upsert_session` 寫入 `tenant_id`（寫入端缺口，連帶修）。
  - `visitors.py`：`visitor_event_timeline`、`get_session_detail`（IDOR）、`assign_tag_to_visitor`、`remove_tag_from_visitor`（同類 IDOR 一併修）、`get_audience_members` 三處。
  - `segments.py`：`evaluate_segment` 基礎查詢＋event subquery。
  - `ml_scoring.py`：單筆預測補歸屬檢查；`_run_batch_scoring` 改為接收呼叫者 `tenant_id` 並過濾（原先任一租戶 admin 可掃全庫）。
  - `ai_intelligence.py`：content optimize 的 Visitor 二次查詢補防禦性 tenant filter。
- **測試**：完整套件 73 passed；5 個失敗皆為環境性既有問題（`agent_platform` 模組未安裝 ×2、`AGENTOSS_URL` 未設定 ×3），與本次修改無關。
- **相依**：T1 ✅。

### T4. Secrets 治理 ✅（2026-08-03 完成掃描與止血；輪替為人工待辦）

- **目的**：清除進版控的憑證，輪替曾外洩密碼。
- **掃描結果**：
  - ~~`api/.env.kinga`~~（已自工作區徹底移除；King-A demo 套件亦已清除）：當時含 DATABASE_URL、SECRET_KEY、OPENAI_API_KEY、ADMIN_PASSWORD 等**真實憑證**。
  - `admin/.env.production`（被追蹤）：僅 API URL，無密碼但不應入庫。
  - 其餘追蹤中的 env 檔皆為 `.example`；全 repo 掃描（sk-proj／xoxb／私鑰／密碼欄位）無其他明文。
- **已執行（止血）**：
  - `git rm --cached` 移除兩檔追蹤（本地檔案保留）。
  - `.gitignore` 改為 `.env.*` 全擋、僅放行 `!.env.example` 與 `!.env.*.example`。
  - **後續（2026-08）**：`demo/king-a/`、King-A intake 腳本、本機 `api/.env.kinga` 已徹底清除。
- **⚠️ 人工待辦（我無法代執行，需當事人操作）**：
  1. 若曾使用 King-A 專用 DB／金鑰，**輪替**相關憑證（資料庫密碼、SECRET_KEY、OPENAI_API_KEY、ADMIN_PASSWORD）。
  2. **決定是否改寫 git 歷史**（`git filter-repo` 移除兩檔的歷史版本）——此為破壞性操作，需團隊協調且強制推送；公開 repo 首次 push 前已執行過一輪。
  3. 若該 DB 為生產庫，檢查存取日誌是否有異常連線。
- **相依**：無，已平行完成。

---

## P2 — 首回速度工程（母計畫 §5.3）

### T5. 高品質 RFQ 即時推播升級 ✅（2026-08-03 完成）

- **目的**：Hot／高品質 RFQ **主動推**給業務，不等登入儀表板（搶先回覆者紅利）。
- **已完成**：
  - 新建 `channels/line.py`（LINE Messaging API push，template buttons）；註冊進 `notification_router._CHANNEL_MAP`（Telegram＋LINE 多通道）。
  - `copilot/monitor.py` 新增 `_should_instant_push` gate：quality ≥ 70 或 priority urgent → 即時推播；其餘併入每日摘要。
  - 推播文案升級：品質分數、貿易訊號（Incoterm／年量／認證／目標價）、國家、首回 SLA 時間、直達詳情連結。
  - 順帶修復 `notification_router._is_quiet_hours` 的 `datetime` 未匯入潛在 bug。
- **測試**：gate 純函式測試＋LINE channel payload mock 測試（`test_rfq_speed_features.py`）。
- **驗收對應**：高品質 RFQ 觸發即時推播（通道需設定 TELEGRAM_BOT_TOKEN／LINE_CHANNEL_ACCESS_TOKEN 才會真正送出）；低品質不即時推 ✅。

### T6. 自動專業回覆（Auto-Acknowledge） ✅（2026-08-03 完成）

- **目的**：RFQ 送出後在買家時區上班時間內**立即**給出專業確認，先佔住 shortlist 位置。
- **已完成**：
  - 新建 `services/rfq_auto_reply.py`：專業英文確認信（已收到＋需求理解＋**缺口資訊清單**（依 T10 欄位）＋預計完整回覆時間＋tenant 簽名檔），XSS escape。
  - Per-tenant 開關：`SiteProfile.ops_config_json`（migration 0048 新欄位，統一承載 `auto_reply_*` 與 `sla_response_hours`，`services/ops_config.py` 讀取），預設關。
  - 發送時間對齊買家上班時段（非上班時段延後至下一時段開頭，上限 12h；⚠️ v1 以 asyncio.sleep 實現，重啟會遺失待發信）。
  - 低品質不發（門檻 30）；冪等（`RFQEvent auto_reply_sent` 存在則不重發）；寄出後記 `first_response_at`（算首回）。
  - `submit_rfq` 已接線觸發。
- **測試**：開關行為／端點接線／冪等／信件內容／缺口清單（`test_rfq_speed_features.py` 全過）。
- **相依**：T9 ✅。

### T7. 時區感知 SLA ✅（2026-08-03 完成）

- **目的**：SLA 以**買家時區工作時間**計時，逾期升級主管——公平且可執行。
- **已完成**：
  - Model＋migration 0047：`buyer_timezone`／`sla_due_at`／`sla_breached`（`first_response_at` 既有）。
  - 新建 `services/sla.py`：國家→IANA 時區對照（40+ 外銷市場）、`add_business_hours`（週一至週五 09–18 買家當地時間，週末／下班自動遞延）、per-tenant 時數（ops_config `sla_response_hours`，預設 4h）。
  - `submit_rfq` 建立時算 `sla_due_at`；`update_rfq_status` 首次離開 `new` 記 `first_response_at`。
  - 排程（main.py）每 15 分鐘 `scan_sla_breaches`：1 小時內到期→催辦（`notify_rfq_reminder`）；逾期→`sla_breached=True`＋升級主管（`notify_rfq_escalation`）。
- **測試**：工作時間計算 4 案例（跨下班／週末／跨日）＋API 生命週期（`test_rfq_sla.py` 全過）。
- **相依**：T1 ✅；T5 ✅。

### T8. 首回時間統計 ✅（2026-08-03 完成）

- **目的**：客戶儀表板與內部都能回答「平均多久回」。
- **已完成**：
  - 新 endpoint `GET /tracking/rfqs/stats?days=N`（注意：定義在 `/rfqs/{rfq_id}` 之前避免路由衝突）：平均／中位首回小時、SLA 達成率（met/breached/pending）、狀態分佈、平均品質分。處理 timestamptz／timestamp 混合時區歸一。
  - Admin 列表頁頂部 4 張摘要卡（平均首回時間／SLA 達成率（<80% 紅字）／逾期單數／平均品質分）。
- **測試**：endpoint 整合測試（`test_rfq_speed_features.py::test_rfq_stats_endpoint`）。
- **相依**：T7 ✅。

---

## P2 — Lead Quality Score（母計畫 §5.1）

### T9. 品質分數後端（規則式 v1） ✅（2026-08-03 完成）

- **目的**：RFQ 進來即分級，業務時間導向有圖面、有貿易條件的真採購單。
- **已完成**：
  - 新建 `services/rfq_quality.py`：規則式評分五維度（規格完整度／商業可行／身分品質／**貿易條件**／風險），全部加分寫成人可讀 reasons，clamp 0–100。ML 版之後可用同介面替換。
  - Model＋migration 0046：`quality_score`（indexed）＋`quality_reasons_json`。
  - `submit_rfq` 內計算並寫入；`list_rfqs`/`get_rfq` 回應暴露分數與 reasons。
- **測試**：5 種典型 RFQ 排序符合直覺（完整採購單 ≥80、一句話 ≤20、垃圾單最低、貿易條件加分 ≥30）（`test_rfq_quality.py` 全過）。
- **相依**：T1 ✅；T10 欄位同批上線（共用 migration 0046）。

### T10. RFQ 表單加貿易條件欄位 ✅（2026-08-03 完成）

- **目的**：讓 T9 的貿易維度有資料可評；會填這些欄位的買家＝強採購訊號。
- **已完成**：
  - Model＋migration 0046：`incoterm`／`annual_volume`／`is_trial_order`／`required_certs_json`／`target_price`。
  - `RFQFormIn` 新增五個**全選填**欄位＋驗證（Incoterm 白名單 11 種、certs ≤10 項）；`form_data` 快照同步收錄；API 測試確認含貿易欄位可送出、略過不受阻。
- **⚠️ 待辦（前端）**：公開站 RFQ 表單的「第二步貿易條件（可跳過）」UI 未實作——公開站表單在各租戶前台（web/），需另開票；API 已完全就緒。
- **相依**：T1 ✅。

### T11. Admin 列表改「品質 × SLA」排序 ✅（2026-08-03 完成）

- **目的**：業務打開列表，最上面就是「最該先回」的單。
- **已完成**：
  - 後端：`list_rfqs` 加 `sort=quality`（quality_score DESC, sla_due_at ASC, created_at ASC）＋`sla=breached|due_soon` 篩選；回應含 quality_score／sla_due_at／sla_breached。
  - 前端：新建共用元件 `admin/src/components/rfq/quality-sla.tsx`（`QualityBadge` 綠黃灰、`SlaCountdown` 逾期紅字／1h 內橘字）；`rfqs/page.tsx` 與 `rfqs/my/page.tsx` 預設 `sort=quality`、新增 Quality／SLA 欄、SLA 篩選與排序切換、逾期列淡紅底。`tsc --noEmit` 通過。
- **相依**：T7 ✅、T9 ✅。

---

## 驗收總表（本批 Done 的定義）

- [x] `alembic heads` 單一；乾淨 DB `upgrade head` 成功（T1）✅ 0048 為唯一 head
- [x] 跨租戶同 email 可各自建 Contact；tracking 聚合無跨租戶污染（T2、T3）✅ 自動化測試通過（92 passed）
- [ ] repo 歷史無明文密碼；舊憑證已輪替（T4）— **止血完成**（檔案移出版控＋gitignore）；輪替與歷史改寫為**人工待辦**
- [x] 高品質 RFQ 1 分鐘內推播到業務手機（T5）✅ 管線完成＋測試通過；實際送出需設定 TELEGRAM_BOT_TOKEN／LINE_CHANNEL_ACCESS_TOKEN
- [x] 開啟 tenant 的買家 5 分鐘內收到專業確認信（T6）✅ 測試通過；需 ESP 設定與 tenant 開啟開關
- [x] SLA 以買家時區計時；逾期升級主管（T7）✅ 測試通過；排程 job 已註冊
- [x] Admin 可見平均首回時間與 SLA 達成率（T8）✅ API＋摘要卡
- [x] 5 種典型 RFQ 的品質分數排序符合業務直覺、原因可讀（T9）✅
- [x] 表單貿易欄位上線且不阻斷送出（T10）✅ API 層；公開站表單 UI 另開票
- [x] Admin 列表預設「品質 × SLA」排序（T11）✅ 兩個列表頁＋tsc 通過

**本批完成後的人工部署清單**：
1. 其他環境 DB：`alembic stamp 0044_add_page_brief_agent_fields` → `alembic upgrade head`（T1 注意事項）。
2. 若曾使用 King-A 專用憑證，輪替相關密鑰（T4；套件與 `api/.env.kinga` 已清除）。
3. 設定推播通道 token（Telegram／LINE）與 ESP（Resend/SendGrid）才能真發送。
4. Tenant 層開啟 `ops_config_json.auto_reply_enabled` 才會發自動確認信。

---

## 與母計畫的對應

| 母計畫 | 本文件票 |
|--------|----------|
| §3 P0 地基 | T1–T4 |
| §5.3 首回速度工程 | T5–T8 |
| §5.1 Lead Quality Score（含貿易維度） | T9–T10 |
| §5.1 用途：品質×SLA 排序 | T11 |

下一批（不在本文件）：Intent facets 前端（§4.1）、回覆品質輔助（§5.4）、客戶儀表板（§6）、顧問工作台（§7）。
