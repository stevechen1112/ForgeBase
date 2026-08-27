# ForgeBase

**RFQ Growth OS for Export Manufacturers** — Capture · Intent · Conversion · Outcomes

ForgeBase 是專為外銷製造商打造的 RFQ 成長系統。
不是幫你做一個網站，而是讓你的網站開始接單——捕捉買家需求、辨識採購意圖、推進詢價、讓業務在對的時間接手。

---

## 產品核心四層

ForgeBase 把官網從展示型網站，升級成可運作的詢價漏斗：

| 層級 | 核心問題 | ForgeBase 做的事 |
|------|----------|------------------|
| **Capture** | 買家找得到你嗎？ | SEO 基礎設施、多語言內容、人工維護的產品與信任內容 |
| **Intent** | 誰只是逛逛、誰在評估？ | 15 種行為追蹤、Intent Score 2.0 採購面向（facets）評分、「為何 Hot」解釋、ML 意圖評分、訪客分眾、GeoIP、Facet 驅動 Dynamic CTA、AI 業務顧問 |
| **Conversion** | 高意圖訪客有被推進到詢價嗎？ | RFQ 表單、AI RFQ 分析與草擬回覆、Chat → RFQ handoff、品質分數、時區感知 SLA、即時通知、自動專業回覆、RFQ 事件審計 |
| **Outcomes** | 詢價有變成訂單嗎？沒有立即詢價的呢？ | 成交漏斗（流量→成交七層）、客戶成果儀表板、內容→成交歸因、內容成效分析、顧問任務佇列；未轉換訪客以分眾＋Email 培育序列養回來再成交 |

---

## 核心功能

### Capture — 讓產品被找到、被理解

| 模組 | 說明 |
|------|------|
| **SEO 基礎設施** | canonical、sitemap、JSON-LD schema 自動生成、SEO 重導向管理 |
| **多語內容支援** | CMS 內容目錄與完整公開網站介面包均支援英文、繁中、日文、法文與俄文；導覽、表單、法務頁、AI 顧問介面、SEO／hreflang／sitemap 與語系切換均涵蓋五語。租戶內容仍須逐語產草稿、人工確認後發布，缺少已發布內容時會明示英文 fallback，不冒充已完成翻譯 |
| **買方語系草稿** | 可依來源語系產任一支援語系草稿（規格／型號／圖片不亂翻）；草稿不上公開站，人工確認後才發布；已發布版本不會被新草稿覆蓋，只標記過期 |
| **語系覆蓋與批次審核** | `/dashboard/content/locales` 與 `GET /content/locale-coverage` 顯示缺漏／草稿／過期；每批最多建立 25 筆缺少草稿，固定自動發布 0 筆 |
| **產品比較頁（Comparisons）** | 產品間規格比較內容型別，前後台完整 CRUD |
| **製造能力頁（Capabilities）** | 產線、設備、製程能力內容型別，建立 B2B 信任 |
| **內容關聯推薦** | 已發布的 Product ↔ Application 關聯資料與人工管理保留；AI 推薦 API 進入退場觀察並預設關閉 |
| **靜態資產管理** | 產品圖、PDF 規格書上傳至 Cloudflare R2；素材缺失可被自診斷健康檢查主動發現 |

**多語內容原則：**

- 內容草稿支援英文、繁中、日文、法文與俄文；台灣受管交付預設以繁中為正本，買方語系先產草稿再上架。
- 後台以 `LocaleSwitcher` 在對應語言版本間切換；FAQ 使用 `variant_key` 配對版本。
- 系統可起草買方語系文案，但不會自動發布；缺該語系已上架內容時，公開站不拿另一語冒充已翻譯。
- AI 客服回覆語言與網站內容語系解耦；訪客使用日文、法文、俄文或其他已辨識語言時，客服維持該語言，不會因知識來源是英文而切回英文。

## 北極星買家管線

ForgeBase 採單一產品，不再區分 Starter／Professional 或第一／第二階段方案。核心流程固定為：

```text
匿名訪客 → 行為追蹤 → 意圖評分 → 推測公司 → 公司相關聯絡窗口候選
→ 依旅程產生個人化信件 → 受控寄送與追蹤 → 對方回覆
→ 真人業務接手 → RFQ／成交
```

公司推測、聯絡窗口、個人化外聯、回覆與接手都是核心能力；若外部資料權利、真實 precision、寄送環境或法遵 Gate 尚未通過，系統以 capability 與 runtime mode fail closed，而不是把它們視為可刪除的實驗功能。公司候選不等於訪客本人，窗口候選也不等於實際訪客。

### Intent — 辨識誰在評估、誰有採購意圖

| 模組 | 說明 |
|------|------|
| **訪客追蹤 & 意圖評分** | 自動記錄 page_view / product_view / cta_click 等 15 種事件，計算 Cold → Warm → Hot → Sales-Ready 階段 |
| **Intent Score 2.0 採購面向（facets）** | 四個採購維度獨立計分：產品興趣／信任驗證／採購準備度／急迫性，附「為何 Hot」人話解釋 |
| **ML 意圖評分** | `/tracking/ml/*`：模型訓練、狀態查詢、單一／批次訪客評分；規則式評分之外的可選 ML 層 |
| **Intent 規則設定** | `/dashboard/intent-rules`：意圖評分規則與權重的後台配置（`GET /tracking/intent-rules`） |
| **訪客分眾（Segments）** | 條件式受眾定義 CRUD、`evaluate` 即時試算名單、`sync-to-esp` 一鍵同步到 ESP |
| **Facet 篩選** | Admin 可依 facet 門檻＋是否已送 RFQ 篩出目標名單（例如「信任驗證高但未 RFQ」）|
| **Dynamic CTA** | 依訪客買家階段＋facet 組合動態切換行動呼籲按鈕；另有 AI 單訪客 CTA 建議（`/tracking/visitors/{id}/recommend-cta`） |
| **AI 業務顧問** | 情境式 AI 對話，接地於公司 CMS 內容、拒絕幻覺、追問採購條件、導向 RFQ（詳見專章）|
| **GeoIP 國家識別** | 訪客國家自動標記 |
| **行為分析 API** | `/tracking/analytics/*`：頁面、產品、應用頁各自的瀏覽分析、策略地圖與行為漏斗查詢 |

### Conversion — 推進詢價、讓業務接住

| 模組 | 說明 |
|------|------|
| **RFQ 詢價表單** | 結構化詢價，含產品需求、數量、時程、Incoterms 等貿易欄位 |
| **聯絡表單** | 一般詢問留資 |
| **AI RFQ 分析** | `POST /tracking/rfqs/{id}/analyze`：AI 比對產品、分類急迫性、抽取結構化需求 |
| **AI 草擬回覆** | `POST /tracking/rfqs/{id}/draft-reply`：針對單筆 RFQ 產生專業回覆信草稿 |
| **Chat → RFQ Handoff** | AI 對話中判定購買意圖後，自動導向預填 RFQ（含可詢價需求摘要）|
| **RFQ 品質分數** | 規則式 v1：貿易術語、年採購量、時程、認證需求等維度，0–100 分 |
| **時區感知 SLA** | 依租戶營業時區計算首次回應期限，APScheduler 自動掃描逾期 |
| **即時通知 & 自動回覆** | 高品質 RFQ 即時推播 Telegram／LINE；可選自動寄出專業確認信 |
| **RFQ 事件審計** | RFQ 生命週期完整紀錄，含狀態變更、指派、首次回覆、報價等事件時間軸 |
| **AgentOS 工作流（退場觀察）** | runtime 與 tenantless job 均鎖定關閉；歷史 `agent_run_id`／writeback 欄位暫留以支援資料回查與可回復性 |

### Outcomes — 成果閉環、讓客戶看得見成效

| 模組 | 說明 |
|------|------|
| **客戶成果儀表板** | `GET /tracking/outcomes`：新 RFQ、合格 RFQ、平均首回時間、SLA 達成率、報價/成交數 |
| **成交漏斗** | `GET /tracking/funnel`：流量→高意圖訪客→RFQ→合格→報價→議價→成交，含瓶頸層識別 |
| **內容→成交歸因** | `GET /tracking/attribution/content`：哪些頁型帶來會成交的單（path segment 精準比對）|
| **內容成效分析** | `/dashboard/content-performance`：各內容的表現總覽，輔助內容投資決策 |
| **Intent Outcome Feedback** | `GET /tracking/intent/outcome-feedback`：成交單的 facet lift 觀察（observational）|
| **顧問任務佇列** | `GET /ops/task-queue`：SLA 逾期、熱訪客未跟進、低品質 RFQ、待審內容一頁清單 |
| **回覆品質輔助** | RFQ 詳情內建 checklist、Quote Readiness、回覆範本庫（`reply_templates`）|
| **Admin 新頁面** | `/dashboard/outcomes`（成果總覽）、`/dashboard/tasks`（今日必處理）|

### 未轉換訪客培育回流（Nurture Loop）

不是每個訪客都會立刻詢價。ForgeBase 的閉環包含「養回來」這一段：

| 模組 | 說明 |
|------|------|
| **Email 培育序列引擎** | `/tracking/nurture/*`：多步驟序列（sequence → steps）、觸發條件、聯絡人 enroll、到期步驟批次處理；序列採**人工核准制**（approve 後才生效），寄件走 outbox 佇列可逐封送或跳過 |
| **ESP 整合** | `/tracking/esp/*`：Mailchimp／SendGrid 聯絡人雙向同步、名單統計、測試信與連線狀態檢查 |
| **分眾 → ESP 直通** | Segment `sync-to-esp`：把「高意圖但未 RFQ」這類動態名單直接推進 ESP 受眾 |
| **培育管理後台** | `/dashboard/nurture` 序列與寄件佇列管理、`/dashboard/segments` 分眾管理 |

---

## AI 業務顧問（前台 AI 客服）

ForgeBase 的 AI 業務顧問不是通用聊天機器人，而是**接地於公司真實資料、以推進詢價為目標**的 B2B 銷售顧問。

### v1 MVP — 已上線並通過線上端到端驗證（2026-08-06）

已於生產環境實測確認的能力：

| 能力 | 說明 |
|------|------|
| **情境感知** | 依訪客所在頁面（產品／分類／應用／首頁／FAQ）即時從 CMS 資料庫組裝上下文：產品規格、型號、關聯 FAQ、認證 |
| **接地回答** | 只根據資料庫內容回答公司事實。實測：能正確答出產品扭力範圍（40–220 Nm）與認證（ISO 9001），資料沒有的（VDE、材質）明確回答「未確認」而非編造 |
| **防幻覺 prompt** | system prompt 明令禁止編造價格、交期、法規與認證；資訊不足時導向 RFQ 或聯絡 |
| **來源引用** | 回覆附產品頁、FAQ、認證頁的來源連結 |
| **商業推進** | 規則式對話政策（`chat_policy.py`）：偵測採購意圖、每輪最多追問一個高價值缺口（方案類型／數量 MOQ／用途／規格／交期／包裝／市場），時機成熟自動產生 RFQ 預填連結 |
| **需求摘要** | handoff 時將整段對話收斂為「業務拿到就能報價」的可詢價需求摘要（`summarize_quotable_needs`），寫入 RFQ prefill |
| **多語回答** | 回答語言與網站內容語系解耦；依訪客最新有效提問自動辨識並以同一語言回答，短型號／數量訊息沿用對話語言；日文、德文、韓文與繁中均有偵測及安全降級測試 |
| **數據閉環** | `chat_start`／`chat_rfq_handoff` 寫入 tracking events 並累積 intent score；後台 `/dashboard/chats` 可審閱對話、評品質分數（1–5）、寫備註 |
| **回應速度** | 生產環境實測每則回覆 3–9 秒 |

掛載策略採「強掛載 + 條件掛載」：FAQ 頁、FAQ tag 頁、產品詳頁強掛載；首頁、產品總覽、分類頁、應用頁條件掛載；法務頁與低內容密度頁不掛載。

API endpoints：

```bash
POST /api/v1/chat/sessions
POST /api/v1/chat/sessions/{chat_session_id}/messages
POST /api/v1/chat/sessions/{chat_session_id}/handoff
```

### 可信顧問架構 — 核心程式已落地，外部品質 Gate 受控

現況已具備公開 CMS／文件知識來源、可追溯引用、跨語言回覆、資格蒐集、RFQ handoff、知識同步與品質評估基礎。外部模型品質、正式文件內容與生產流量指標仍需依交付 Gate 驗證，不能只因程式存在就宣稱達標。

| 階段 | 主題 | 關鍵交付 |
|------|------|----------|
| **安全與語言一致性** | 已落地 | Chat 速率／成本護欄、最新提問語言一致、風險分類、真人交接、timeout 與安全降級 |
| **全公司公開知識庫** | 已落地 | `knowledge_sources`／`knowledge_chunks`／`knowledge_sync_jobs`、CMS 與 PDF 擷取、頁碼來源、耐久同步工作 |
| **可信檢索與回答** | 已落地核心 | 結構化／關鍵字檢索、來源契約、引用與 unsupported-claim 防護；向量供應與真實資料品質依環境驗證 |
| **資格蒐集與 RFQ** | 已落地 | 多語 qualification slots、server-side RFQ draft、買家確認、handoff、品質分數與 SLA 串接 |

驗收門檻（正式上線標準）：公司事實 grounded accuracy ≥95%、關鍵 unsupported claim = 0、內部資料洩漏 = 0、高風險 handoff recall = 100%、語言一致率 ≥98%、p95 回覆 <12 秒。

明確不做的事（本階段紅線）：AI 不自行決定價格與折扣、不保證庫存與交期、不自動接受訂單、不對法規與認證適用性下最終結論、不於未經客戶確認前建立正式 RFQ。

---

## AI 行銷專員（AI Marketing Copilot）

ForgeBase 內建串接真實 CRM 資料的 Telegram 對話 AI，讓業務主管可以在 Telegram 直接查詢 RFQ 狀態、識別高意圖訪客、接收事件通知，並獲得針對製造業 B2B 銷售情境的行動建議。

### 架構概覽

```
[觸發事件]  →  monitor.py  →  notification_router.py  →  TelegramChannel
  new_rfq           │                   │
  hot_visitor        │           NotificationPreference
  chat_handoff       │           NotificationLog
  churn_risk         │
                     └──→  send_notification() 統一分發

[APScheduler]  →  digest.py  →  run_daily_digest()  →  TelegramChannel
  08:00 Asia/Taipei

[Telegram msg]  →  copilot.py webhook  →  BackgroundTasks
                        │
                        └──→  CopilotEngine.run()
                                   │
                               LLM (OpenAI)
                                   │
                          function calling (tools.py)
                                   │
                              DB query results
                                   │
                            Telegram reply (chunked)
```

### 核心元件

| 檔案 | 說明 |
|------|------|
| `api/app/services/copilot/chat_engine.py` | `CopilotEngine` — 多輪對話引擎，含 B2B 系統提示、20 則歷史記憶、最多 6 次 tool call 迴圈 |
| `api/app/services/copilot/tools.py` | 10 個 DB 查詢工具函式（全 tenant-scoped，LLM 透過 function calling 呼叫）|
| `api/app/services/copilot/monitor.py` | 4 個事件處理器：`on_new_rfq`、`on_hot_visitor`、`on_chat_handoff`、`on_churn_risk` |
| `api/app/services/copilot/digest.py` | 每日摘要產生器，產生 24h KPI + AI 建議 |
| `api/app/services/notification_router.py` | 統一通知分發路由：查詢偏好設定→靜音時段→去重→送出→寫入 log |
| `api/app/services/channels/telegram.py` / `line.py` | Telegram／LINE 頻道實作 |
| `api/app/api/v1/endpoints/copilot.py` | Preferences CRUD + Telegram 綁定流程 + webhook 接收器 |

### 可用的 AI 工具（tools.py）

| 工具 | 功能 |
|------|------|
| `get_dashboard_stats(hours)` | KPI 快照：新 RFQ、緊急 RFQ、超時未回、熱訪客數、開案漏斗 |
| `list_rfqs(status, priority, limit)` | 過濾 RFQ 列表 |
| `get_rfq_detail(rfq_number)` | 單筆 RFQ 完整資料 |
| `list_hot_visitors(limit)` | 當前 hot / sales_ready 訪客列表 |
| `get_visitor_profile(visitor_id)` | 訪客深度檔案（意圖歷程、身份解析、RFQ 歷史）|
| `list_overdue_rfqs(hours)` | 超 SLA 未回應的 RFQ 列表 |
| `get_contact_profile(email)` | 聯絡人完整檔案 |
| `search_contacts(query)` | 跨 name / company / country / email 模糊搜尋 |
| `get_product_interest_stats(days)` | 依 RFQ 量排序的產品需求榜 |
| `get_funnel_stats(days)` | 訪客 → 聯絡人 → RFQ → 成交漏斗 |

### Admin 浮動 AI 聊天視窗

後台 AI 業務助理使用 `/dashboard/copilot` 專屬頁面；重複且未接入 bundle 的浮動元件已依安全退場稽核移除。

### 初始設定

```bash
# api/.env
TELEGRAM_BOT_TOKEN=<從 @BotFather 取得>
TELEGRAM_WEBHOOK_SECRET=<自定義隨機字串>
```

Admin 端至 `/backend/dashboard/settings/notifications` 輸入 Telegram chat_id、收取 6 位驗證碼完成綁定，再選擇要開啟的事件通知。

---

## 單一產品與能力治理

ForgeBase 不再區分 Starter／Professional，也不以兩階段方案切割產品。產品以同一條北極星流程交付：匿名訪客 → 行為追蹤 → 意圖評分 → 公司與窗口候選 → 個人化外聯 → 回覆 → 真人業務接手 → RFQ／成交。

固定核心能力對所有租戶開啟；仍在建置、試行、等待第三方資源或退場觀察的能力，則由平台營運方透過 capability override 管理。Admin 使用 `CapabilityProvider`／`CapabilityGate` 對齊後端 `RequireFeature`，此機制是營運安全與成熟度治理，不是付費分級或升級牆。

### 平台營運層（ForgeBase 營運方專用）

| 模組 | 說明 |
|------|------|
| **Platform 超級管理員** | `platform_admin` router（superuser 限定）：跨租戶儀表板、全部租戶列表與單租戶詳情、跨租戶使用者列表、系統健康檢查（`/admin/system/health`） |
| **整合狀態頁** | `/dashboard/integrations` + `GET /admin/integrations/status`：各外部服務（ESP、Telegram、R2 等）連線狀態一頁檢視 |

---

## 專案結構

```
ForgeBase/
├── api/                      # 後端 API (Python 3.12 + FastAPI)
│   ├── Dockerfile            # 生產映像（uvicorn）
│   ├── app/
│   │   ├── api/v1/           # REST endpoints（chat、copilot、content、tracking…）
│   │   ├── db/migrations/    # Alembic migrations（head = 0089）
│   │   ├── models/           # SQLModel 資料模型（多租戶 tenant_id）
│   │   ├── schemas/          # Pydantic 輸入/輸出 schema
│   │   └── services/         # 業務服務（chat_service、copilot/、rfq_quality、sla…）
│   ├── scripts/              # 維運腳本（seed、backfill）
│   └── tests/                # pytest（含 chat、copilot、e2e growth loop）
├── web/                      # 前台網站 (Next.js 15，standalone 輸出)
│   ├── Dockerfile            # 多階段建置生產映像
│   └── src/
│       ├── components/chat/  # AI 業務顧問前端（ChatWidget/ChatPanel/ChatInput）
│       ├── lib/demoAssetRoute.ts      # demo 素材路由（實體檔 / 佔位 SVG，含缺檔追蹤）
│       └── app/api/health/assets/     # 素材與內容自診斷健康檢查端點
├── admin/                    # 管理後台 (Next.js 15，standalone 輸出)
│   ├── Dockerfile
│   └── src/
│       ├── app/(dashboard)/dashboard/           # 租戶後台：內容、RFQ、成效、AI 顧問與受 feature gate 控制的觀察中功能
│       └── app/(dashboard)/dashboard/copilot/page.tsx
├── deploy/                   # 生產部署資產
│   ├── Caddyfile             # 網域模式（自動 HTTPS）
│   ├── Caddyfile.ip          # IP-only HTTP 模式
│   ├── compose.env.example   # Docker Compose 環境變數範本
│   ├── api.env.example       # API 機密範本
│   ├── check-assets.sh       # 素材載入診斷（實體檔/佔位/缺檔分級）
│   ├── verify-selfcheck.sh   # 故障注入回歸測試（健康檢查抓不抓得到問題）
│   └── test-chat.sh          # AI 客服端到端測試（建 session→提問→handoff）
├── docker-compose.prod.yml   # 生產編排：db / migrate / api / admin / web / caddy
├── demo/handtool-company/    # 示範公司內容、素材與種子腳本
├── shared/                   # 共用型別與常數
└── .github/                  # CI/CD workflows
```

---

## 技術棧

| 層級 | 技術 | 版本 |
|------|------|------|
| 後端 API | Python + FastAPI + SQLModel + Alembic | 3.13 / 0.115 / 0.0.21 / 1.13 |
| 資料庫 | PostgreSQL（Docker 容器） | 16-alpine |
| 資料庫驅動 | asyncpg (async) | 0.29 |
| 前台 | Next.js (App Router，standalone) | 15.5 |
| Admin 後台 | Next.js (App Router，standalone) | 15.5 |
| 反向代理 | Caddy（自動 HTTPS／IP HTTP 雙模式） | 2-alpine |
| 容器編排 | Docker Compose | v2 |
| 檔案儲存 | Cloudflare R2 | S3-compatible |
| LLM | OpenAI API（Langfuse tracing 可選，內建 PII 遮罩） | 由 `AI_MODEL_NAME` 設定 |
| Email | Resend | — |
| GeoIP | Cloudflare CF-IPCountry header | — |
| Hosting | Linode Ubuntu 24.04（單機全棧容器） | — |
| CI/CD | GitHub Actions | — |

---

## 生產環境與部署

2026-08-06 起，生產架構從 systemd + nginx 全面改為 **Docker Compose 單機容器化**。

### 服務拓撲

| 服務 | 說明 |
|------|------|
| `db` | PostgreSQL 16-alpine，named volume 持久化，pg_isready 健康檢查 |
| `migrate` | 一次性容器，`alembic upgrade head` 成功後 api 才啟動 |
| `api` | FastAPI，uvicorn 2 workers，uploads volume |
| `admin` | 管理後台 Next.js standalone |
| `web` | 前台 Next.js standalone；`./demo:/demo:ro` 掛載 demo 素材；內建 `/api/health/assets` 自診斷健康檢查（60s 間隔）|
| `caddy` | 80/443，網域模式自動申請 Let's Encrypt；IP 模式走 `Caddyfile.ip` |

### 目前生產狀態

| 項目 | 值 |
|------|----|
| **ForgeBase 官網** | https://pcbrm.tw/ |
| **NorthForge 參考站** | https://pcbrm.tw/northforge-tools/ |
| **後台** | https://pcbrm.tw/backend/login |
| **API** | https://pcbrm.tw/api/v1/ |
| **伺服器** | Linode Ubuntu 24.04，IP `172.233.64.5` |
| **部署目錄** | `/opt/forgebase` |
| **SSH** | `ssh -i ~/.ssh/mitselect_linode_ed25519 root@172.233.64.5` |
| **Admin 帳號** | 由 `api/scripts/seed_admin_bcrypt.py` 建立（憑證見部署紀錄，不入庫）|

### 自診斷與防呆（2026-08-06 圖片根因修復的遺產）

這次部署過程中修掉了前台圖片反覆失效的四個根因，並留下永久性防呆機制：

| 根因（已修復） | 防呆機制 |
|----------------|----------|
| demo 素材未掛進 web 容器 | `docker-compose.prod.yml` 明確掛載 `./demo:/demo:ro`；`/api/health/assets` 開機探針驗證主視覺實體檔可讀 |
| 佔位圖被長時間快取污染 | `demoAssetRoute.ts` 佔位回應改 `Cache-Control: no-store`；實體檔才用 `immutable` 長快取；佔位帶 `X-Demo-Asset: placeholder` 標頭 |
| 前端 tenant slug 與內容 tenant 不符導致查無內容 | `NEXT_PUBLIC_TENANT_SLUG` 預設留空（對應 NULL-tenant 內容）；健康檢查以「已發布分類數 = 0」作為租戶錯配訊號 |
| SSR API 呼叫繞外部網域不穩 | `API_INTERNAL_URL: http://api:8000` 走容器內網；`localhost` 健康檢查改用 `127.0.0.1`（Alpine IPv6 解析問題）|

診斷工具：

```bash
bash deploy/check-assets.sh      # 掃描各頁素材：實體檔 / 佔位 / 缺檔分級報告
bash deploy/verify-selfcheck.sh  # 故障注入回歸：確認健康檢查真的抓得到素材與租戶問題
curl http://172.233.64.5/api/health/assets   # 即時狀態（ok / ok-with-warnings / degraded）
```

### 部署操作

```bash
# 伺服器上
cd /opt/forgebase
docker compose -f docker-compose.prod.yml --env-file .env build api    # 依序建置避免低記憶體 OOM
docker compose -f docker-compose.prod.yml --env-file .env build admin
docker compose -f docker-compose.prod.yml --env-file .env build web
docker compose -f docker-compose.prod.yml --env-file .env up -d
docker compose -f docker-compose.prod.yml --env-file .env run --rm api \
  sh -c "cd /app && PYTHONPATH=/app python scripts/seed_admin_bcrypt.py"   # 首次建立管理員
docker compose -f docker-compose.prod.yml ps    # web 應顯示 healthy
```

完整步驟與環境變數說明見 [deploy/README.md](deploy/README.md)。

---

## 快速開始（本地開發）

### 環境需求

- Python 3.12（與 Docker／CI 一致）
- Node.js 20+
- PostgreSQL 16+（本地直接安裝或透過 Docker）

### 本地啟動

```bash
# 0. 建立本地 PostgreSQL user 與 database（首次設定）
# psql -U postgres -c "CREATE USER forgebase WITH PASSWORD 'forgebase_dev';" # pragma: allowlist secret -- local-only example
# psql -U postgres -c "CREATE DATABASE forgebase OWNER forgebase;"

# 1. 後端 API
cd api
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head           # 套用至目前單一 head
uvicorn app.main:app --reload --port 8000

# 2. 前台網站
cd web && cp .env.local.example .env.local && npm install && npm run dev

# 3. 管理後台
cd admin && cp .env.local.example .env.local && npm install && npm run dev
```

### 測試

```bash
cd api && source .venv/bin/activate
python -m pytest -q
python scripts/verify_schema_contract.py
cd ../admin && npm run type-check && npm run lint && npm run build
cd ../web && npm run type-check && npm run lint && npm run build
```

可選的 authenticated Admin UI 文案掃描需另裝 Playwright，不會污染 API runtime image：

```bash
pip install -r scripts/requirements-ui-scan.txt
playwright install chromium
FORGEBASE_ADMIN_EMAIL=... FORGEBASE_ADMIN_PASSWORD=... python scripts/scan_admin_ui_copy.py
```

### Demo 資料注入（選用）

```bash
cd api && source .venv/bin/activate
python3 ../demo/handtool-company/seed/import_demo_content.py      # 5 分類 / 32 產品 / 6 應用 / 5 認證 / 18 FAQ
python3 ../demo/handtool-company/seed/seed_demo_visitors.py       # 模擬訪客行為
python3 ../demo/handtool-company/seed/seed_demo_briefs_ctas_nurture.py
```

### AI 客服端到端測試（對任意環境）

```bash
bash deploy/test-chat.sh   # 建 session → 跨品類提問 → 模糊需求追問 → handoff → 產品頁情境
```

---

## 開發規範

- API 版本前綴：`/api/v1/`
- 所有 API 回應格式：`{"data": ..., "meta": ...}` 或 `{"error": ...}`
- DB migration：`alembic revision --autogenerate -m "描述"` 後 commit；`alembic heads` 必須維持單一
- 環境變數：`.env.example` 保持更新，**絕不 commit 真實 `.env`**（`.gitignore` 已全擋 `.env.*`，僅放行 example）
- AI 客服回答公司事實必須接地於資料庫內容；缺資料時保守回答並導向 RFQ，禁止編造

---

## 文件

| 文件 | 說明 |
|------|------|
| [FORGEBASE_AI_CUSTOMER_SERVICE_DEVELOPMENT_PLAN.md](FORGEBASE_AI_CUSTOMER_SERVICE_DEVELOPMENT_PLAN.md) | AI 業務顧問 v2 完整工程開發計畫（四階段、資料模型、驗收門檻）|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 技術架構與選型決策紀錄 |
| [FORGEBASE_DEPLOY_SETUP.md](FORGEBASE_DEPLOY_SETUP.md) | 部署環境變數、遷移步驟、營運設定 |
| [deploy/README.md](deploy/README.md) | Docker Compose 生產部署完整指南（Linode）|
| [FORGEBASE_MASTER_ROADMAP.md](FORGEBASE_MASTER_ROADMAP.md) | Leads Growth OS 五線五階段總路線圖與進度追蹤 |
| [FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md](FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md) | Intent／Conversion／Leads／Ops 強化計畫 |
| [FORGEBASE_SPRINT_TICKETS_P0_SPEED.md](FORGEBASE_SPRINT_TICKETS_P0_SPEED.md) | Phase 1 票級紀錄（T1–T11：地基＋首回速度＋品質分數）|
| [FORGEBASE_SPRINT_TICKETS_PHASE3_INTENT.md](FORGEBASE_SPRINT_TICKETS_PHASE3_INTENT.md) | Phase 3 票級紀錄（Intent Score 2.0 facets）|
| [FORGEBASE_SPRINT_TICKETS_PHASE4_OUTCOMES.md](FORGEBASE_SPRINT_TICKETS_PHASE4_OUTCOMES.md) | Phase 4 票級紀錄（成果與閉環）|
| [FORGEBASE_SPRINT_TICKETS_PHASE5_DEEPENING.md](FORGEBASE_SPRINT_TICKETS_PHASE5_DEEPENING.md) | Phase 5 票級紀錄（歸因＋E2E）|
| [MULTILINGUAL_PRODUCT_VISION.md](MULTILINGUAL_PRODUCT_VISION.md) | 已封存的多語自動化構想；不代表現行產品能力 |
| [FORGEBASE_NORTH_STAR_CORE_GAP_IMPLEMENTATION_PLAN_2026-08-26.md](FORGEBASE_NORTH_STAR_CORE_GAP_IMPLEMENTATION_PLAN_2026-08-26.md) | 單一產品北極星核心缺口、取捨與實作規格 |
| [deploy/README.md](deploy/README.md) | production 部署、standalone 資產檢查與維運紅線 |
| [FORGEBASE_CLOSED_TEST_PROTOCOL_2026-08-15.md](FORGEBASE_CLOSED_TEST_PROTOCOL_2026-08-15.md) | 封閉測試流程、驗收門檻與回報規範 |

---

## 版本更新紀錄

### v1.3 — 內容可靠性優先（2026-08-11）

| 類別 | 變更 |
|------|------|
| **移除** | 停用 Legacy Site Intake、AI 內容生成、LLM 翻譯草稿與英文內容自動同步。 |
| **內容治理** | 英文與繁中均改為人工建立、人工審核、人工發布；系統不會自行產生或改寫公開內容。 |
| **保留** | AI 業務顧問、RFQ 分析與回覆草稿持續作為銷售協作工具，不會直接發布網站內容。 |

### v1.2 — 英文母語多語自動同步（2026-08-07）

| 類別 | 變更 |
|------|------|
| **同步** | 新增 `locale_sync`：存來源語系後產生其他語系草稿；需啟用 `multilingual` capability，確認後才公開 |
| **防呆** | `content_field_locks`：繁中手改欄位下次自動同步跳過；無待審／核准 UI |
| **資料** | migrations `0059`（locks／FAQ `variant_key`／`model_number` 含 locale）+ `0060`（拿掉全域 slug UNIQUE，改 per-locale）|
| **FK** | 產品分類／分類父子／Page `entity_id` 跨語系重映射到目標語對應列 |
| **Admin** | 列表假語系選項移除；`LocaleSwitcher` 說明文案＋同頁切語系；FAQ 起草帶 `variant_key` |
| **Locale** | API／web／admin 統一正規化；前台路由 `zh-TW` ↔ DB `zh-tw` |
| **驗證** | Linode 端到端：EN 分類／產品／FAQ 存檔 → 自動產生 published 繁中列 |

### v1.1 — Docker 化全棧部署 + 素材自診斷 + AI 客服線上驗證（2026-08-06）

#### 部署架構翻新

| 類別 | 變更 |
|------|------|
| **容器化** | 新增 `api/Dockerfile`、`web/Dockerfile`、`admin/Dockerfile`（Next.js 多階段 standalone）、三份 `.dockerignore` |
| **編排** | 新增 `docker-compose.prod.yml`：db / migrate / api / admin / web / caddy 六服務；`x-api-env` YAML anchor 確保 migrate 與 api 環境一致（修掉 production validation 誤殺）|
| **反向代理** | `deploy/Caddyfile`（網域自動 HTTPS）+ `deploy/Caddyfile.ip`（IP-only HTTP 過渡模式）；`/api/health/*` 正確路由至 web |
| **環境管理** | `deploy/compose.env.example` 與 `deploy/api.env.example` 分離一般設定與機密；secrets 全部生成式，不入庫 |
| **伺服器** | 新 Linode（Ubuntu 24.04） provisioning：swap 防 Next.js build OOM、Docker 安裝、SSH key 認證、Cloud Firewall 規則（22/80/443）|

#### 前台圖片根因修復（四根因，見「自診斷與防呆」）

| 類別 | 變更 |
|------|------|
| **素材掛載** | web 容器掛載 `./demo:/demo:ro` |
| **快取污染** | 佔位 SVG 改 `no-store` + `X-Demo-Asset` 診斷標頭；實體檔 `immutable` |
| **租戶錯配** | `NEXT_PUBLIC_TENANT_SLUG` 預設留空對齊 NULL-tenant 內容 |
| **內網呼叫** | `API_INTERNAL_URL` 修正，SSR 不再繞外部 IP |

#### 自診斷基礎設施（新）

| 類別 | 變更 |
|------|------|
| **健康檢查** | 新增 `web/src/app/api/health/assets/route.ts`：素材掛載探針、內容探針（租戶錯配偵測）、執行期缺檔追蹤、產品缺圖警告；整合 Docker healthcheck |
| **診斷腳本** | `deploy/check-assets.sh`（素材分級報告）、`deploy/verify-selfcheck.sh`（故障注入回歸）|
| **型別修復** | `demoAssets.ts` 產品圖欄位改 optional、`rfq/page.tsx` metadata 包裝修正（生產建置浮現的兩個潛在 type error）|

#### AI 業務顧問線上端到端驗證

以 `deploy/test-chat.sh` 對生產環境完成五段驗證：首頁跨品類採購問題（正確引用 FAQ + 結構化需求抽取 + 反問 MOQ）、模糊需求追問、handoff 需求摘要、產品頁規格接地回答（40–220 Nm／ISO 9001，未確認項目誠實標示）、繁體中文問答。後端回覆 3–9 秒，DB 稽核軌跡完整。v2 升級工程計畫已定案（見專章與計畫文件）。

**當時待辦（歷史紀錄）**：Chat 速率限制、zh-TW 固定文案與 tenant handoff gate 已在後續可靠性批次處理；正式環境狀態應以部署健康檢查與交付紀錄為準，不以這段歷史版本說明判定。

---

### v1.0 — Leads Growth OS Phase 1–5（2026-08-03）

以「產出並接住 qualified leads」為目標的五階段交付，ForgeBase 從 Capture/Intent/Conversion 三層擴展為含 Outcomes 的四層閉環。詳細票級紀錄見 `FORGEBASE_SPRINT_TICKETS_*.md`，總表見 `FORGEBASE_MASTER_ROADMAP.md`。

#### Phase 1 — 工程地基＋首回速度（T1–T11）

| 類別 | 變更 |
|------|------|
| **Migration 鏈修復** | 修正 0042–0044 orphan revisions，鏈恢復可升級 |
| **多租戶** | `contacts.email` 改為 `(tenant_id, email)` 複合唯一（T2）；tracking/events/visitors/segments/ml_scoring 13 處 tenant 隔離缺口修補（T3）|
| **Secrets** | 移除已追蹤的客戶／環境 secrets 檔（T4）|
| **即時通知** | 新增 LINE channel；品質分數 gate 高品質 RFQ 即時推播（T5）|
| **自動專業回覆** | 依 RFQ 內容自動寄出確認信，租戶可開關＋品質閘門（T6）|
| **時區感知 SLA** | 依租戶營業時區計算首回期限，APScheduler 掃描逾期（T7）|
| **品質分數** | 規則式 v1 含貿易術語維度：Incoterms／年量／認證／時程（T9/T10）|
| **Admin** | RFQ 列表品質 badge＋SLA 倒數（T11）|
| **Migrations** | `0045`–`0048` |

#### Phase 2a — ContentFlow 發佈接收端

| 類別 | 變更 |
|------|------|
| **HTML 消毒** | 白名單 stdlib sanitizer，套用到 `Page.body` |
| **Meta-only 端點** | `PATCH /content/pages/{id}/meta`（僅 SEO 欄位）|
| **On-demand revalidate** | FB→web `POST /api/revalidate`，發布/更新/下架觸發 |
| **Idempotency** | `POST /content/pages` 支援 `Idempotency-Key`，含併發競態處理（migration `0049`）|
| **Tenant 解析修正** | list 端點以 auth user 覆寫 host 解析，修復 CF slug 查詢盲點 |

#### Phase 3 — 看懂買家（Intent Score 2.0）

| 類別 | 變更 |
|------|------|
| **Facets** | 四採購面向獨立計分（migration `0050`）|
| **「為何 Hot」** | 由近期事件產生人話解釋，正確處理表單 RFQ |
| **Facet→CTA** | 採購準備度高→RFQ 優先；產品興趣高＋信任低→下載型錄優先 |
| **Advisor 收斂** | 新 slots（用途/規格/交期），handoff 寫入可詢價需求摘要 |
| **信任內容標準** | `GET /content/pages/{id}/trust-check` 回傳檢核清單與分數 |

#### Phase 4 — 成果與閉環

| 類別 | 變更 |
|------|------|
| **狀態機** | 新增 `negotiation`；`won`/`lost` 必填原因（migration `0051`）|
| **回覆品質輔助** | RFQ 詳情 reply-assist 面板＋`reply_templates` 範本庫 CRUD |
| **Outcomes API** | `GET /tracking/outcomes` 客戶首屏五項 |
| **成交漏斗** | `GET /tracking/funnel` 七層，含瓶頸層 |
| **顧問任務佇列** | `GET /ops/task-queue`；`first_response_at` 僅真實回覆才寫入 |
| **Admin** | 新增 `/dashboard/outcomes`、`/dashboard/tasks` |

#### Phase 5 — 深化與規模化

| 類別 | 變更 |
|------|------|
| **內容歸因** | `GET /tracking/attribution/content`，path segment 精準比對＋won_rate |
| **Intent feedback** | `GET /tracking/intent/outcome-feedback` 成交 facet lift（observational）|
| **E2E 測試** | `test_e2e_growth_loop.py` 全成長迴路＋跨租戶污染驗證 |
| **回填腳本** | `scripts/backfill_visitor_facets.py` 既有訪客 facets 重算 |

**驗證結果**：全量回歸 136 passed；Admin 前端 tsc 通過。

---

### v0.23 — AI 行銷專員可觀測性 + Admin 浮動視窗（2026-04-16）

| 類別 | 變更 |
|------|------|
| **DB Model** | 新增 `CopilotRunLog` 可觀測性資料表（migration `0040`）|
| **API** | `GET /copilot/stats`：7 天 total_runs / tool_hit_rate / error_rate / avg_duration_ms / top_tools |
| **Admin** | `/dashboard/copilot` 專屬 AI 業務助理頁面（依 feature entitlement 顯示） |
| **CI** | api workflow 補 `alembic upgrade head`，`@requires_db` 測試不再 skip |

### v0.20–0.22 — 多租戶、能力治理、AI 行銷專員（2026-04）

| 版本 | 重點 |
|------|------|
| **v0.20** | 全 content tables 補 `tenant_id`；slug 複合唯一；前台 runtime 白標（`runtimeSiteConfig.ts`）；52 passed + smoke test 13 passed |
| **v0.21** | 最初導入前後端 feature entitlement；其方案語意已於 migration `0088` 改為單一產品的 capability governance |
| **v0.22** | AI Marketing Copilot：Telegram 通知系統 + LLM 對話引擎 + 10 個 tenant-scoped 工具（migration `0038`）|

### v0.18 — 成長網站強化改造（2026-03-15）

產品主推欄位、RFQ 跟進時間軸、CTA 意圖分階、漏斗分析 API（migration `0018`），共 23 項工作項目。
