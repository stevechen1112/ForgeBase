# ForgeBase

**RFQ Growth OS for Export Manufacturers** — Capture · Intent · Conversion

ForgeBase 是專為外銷製造商打造的 RFQ 成長系統。
不是幫你做一個網站，而是讓你的網站開始接單——捕捉買家需求、辨識採購意圖、推進詢價、讓業務在對的時間接手。

---

## 產品核心三層

ForgeBase 把官網從展示型網站，升級成可運作的詢價漏斗：

| 層級 | 核心問題 | ForgeBase 做的事 |
|------|----------|------------------|
| **Capture** | 買家找得到你嗎？ | SEO 基礎設施、多語言內容、AI 內容生成、Legacy Site Intake 舊站匯入 |
| **Intent** | 誰只是逛逛、誰在評估？ | 15 種行為追蹤、意圖評分引擎、GeoIP、Dynamic CTA、AI Product Advisor |
| **Conversion** | 高意圖訪客有被推進到詢價嗎？ | RFQ 表單、Chat → RFQ handoff、即時通知、逾時催辦、RFQ 事件審計 |

---

## 核心功能

### Capture — 讓產品被找到、被理解

| 模組 | 說明 |
|------|------|
| **SEO 基礎設施** | canonical、sitemap、JSON-LD schema 自動生成、SEO 重導向管理 |
| **多語言支援** | 英文 + 繁體中文，hreflang 自動產生 |
| **AI 內容生成** | 基於 PageBrief 工作流，AI 自動起草產品頁、應用頁、FAQ |
| **Legacy Site Intake** | 匯入既有企業官網或型錄站，抽取內容候選資料後進入 admin 審核與提交流程 |
| **靜態資產管理** | 產品圖、PDF 規格書上傳至 Cloudflare R2 |

### Intent — 辨識誰在評估、誰有採購意圖

| 模組 | 說明 |
|------|------|
| **訪客追蹤 & 意圖評分** | 自動記錄 page_view / product_view / cta_click 等 15 種事件，計算 Cold → Warm → Hot → Sales-Ready 階段 |
| **Dynamic CTA** | 依訪客買家階段動態切換行動呼籲按鈕 |
| **AI Product Advisor** | FAQ 頁、產品詳頁嵌入情境式 AI 對話，導向 RFQ |
| **GeoIP 國家識別** | 訪客國家自動標記 |

### Conversion — 推進詢價、讓業務接住

| 模組 | 說明 |
|------|------|
| **RFQ 詢價表單** | 結構化詢價，含產品需求、數量、時程等欄位 |
| **聯絡表單** | 一般詢問留資 |
| **Chat → RFQ Handoff** | AI 對話中判定購買意圖後，自動導向預填 RFQ |
| **RFQ 事件審計** | RFQ 生命週期完整紀錄，含狀態變更、指派、首次回覆、報價等事件時間軸 |
| **即時通知 & 逾時催辦** | 新詢價通知、SLA 催辦、業務跟進狀態管理 |

---

## SaaS 方案分層

兩層方案 + 按需 add-on，對應客戶成長階段：

### Starter 入門（$149/月）

**定位：數位型錄 + 詢價入口**

| 漏斗階段 | 功能 |
|----------|------|
| 曝光 | 前台官網（英文）、SEO 基礎（canonical / sitemap / schema）、SEO Redirect 管理 |
| 互動 | 基礎追蹤（page_view） |
| 留資 | RFQ 詢價表單、聯絡表單 |
| 跟進 | — |
| 限制 | 產品 50 筆、管理員帳號 2 組 |

> 升級誘因：「你有 5 筆新詢價，但你不知道其中 2 位早就看了你 12 個產品頁。」

### Professional 專業（$699/月）

**定位：意圖識別 + AI 導購 + 業務跟進全閉環**

含 Starter 全部，加上：

| 漏斗階段 | 功能 |
|----------|------|
| 曝光 | 多語言（EN + zh-TW）、AI 內容生成（PageBrief 工作流） |
| 互動 | 完整行為追蹤（15 種事件）、意圖評分引擎、意圖儀表板、Dynamic CTA、GeoIP、AI Product Advisor |
| 留資 | Chat → RFQ handoff |
| 跟進 | 即時通知、逾時催辦 |
| 限制 | 產品無上限、管理員帳號無上限 |

### 方案驅動的 Admin UI / API

目前 Starter 與 Professional 已由 feature flag 真正驅動前後台行為，而不只是顯示不同 pricing 文案。

- Admin 側欄會依方案自動裁切，鎖定功能會導向升級頁
- Professional-only 頁面會在 route layout 層被 `PlanGate` 阻擋
- 非整頁鎖定的功能會使用 inline upgrade UX，例如儀表板訪客 KPI、策略地圖成效覆蓋
- 後端關鍵 API 也會同步檢查 tenant plan，避免繞過前端直接取用 Professional 功能

目前代表性的 feature flags 包含：

- `full_tracking`：訪客旅程、內容成效、漏斗分析、自訂受眾、策略成效覆蓋
- `intent_scoring`：意圖分析、ML scoring、評分規則
- `chat_handoff`：對話管理與 chat review workspace
- `ai_content_generation`：AI 內容優化與內容生成 API
- `seo_redirects`：Redirect 管理
- `multilingual`：多語管理
- `dynamic_cta`：CTA 管理

---

## 專案結構

```
ForgeBase/
├── api/                    # 後端 API (Python 3.13 + FastAPI)
│   ├── app/
│   │   ├── api/v1/         # REST endpoints（含 Legacy Site Intake、AI Copilot）
│   │   ├── db/migrations/  # Alembic migrations (38 版本)
│   │   ├── models/         # SQLModel 資料模型（含多租戶 tenant_id）
│   │   ├── schemas/        # Pydantic 輸入/輸出 schema
│   │   └── services/       # 後端服務（含 intake_engine、copilot/）
│   ├── .venv/              # API 專用虛擬環境
│   └── .env.example
├── web/                    # 前台網站 (Next.js 15，生產部署 Linode)
│   ├── src/lib/runtimeSiteConfig.ts  # 多租戶 runtime 白標品牌核心
│   └── .env.local.example
├── admin/                  # 管理後台 (Next.js 15，生產部署 Linode)
│   ├── src/app/(dashboard)/dashboard/intake/  # Legacy Site Intake 審核介面
│   └── .env.local.example
├── demo/                   # Demo 示範資料與種子腳本
│   └── handtool-company/   # 示範公司（手工具製造商）
│       └── seed/           # 模擬訪客行為注入腳本
├── scripts/
│   ├── mock-site-profile-server.mjs  # 多租戶品牌 mock API（本地 smoke test 用）
│   └── smoke-test.ps1                # 前台多租戶 smoke test 腳本
├── intake_output/          # 網站擷取實測輸出（crawl raw / seed / analysis）
├── shared/                 # 共用型別與常數
├── ARCHITECTURE.md         # 技術架構決策紀錄
└── .github/                # CI/CD workflows
```

---

## 技術棧

| 層級 | 技術 | 版本 |
|------|------|------|
| 後端 API | Python + FastAPI + SQLModel + Alembic | 3.13 / 0.115 / 0.0.21 / 1.13 |
| 資料庫驅動 | asyncpg (async PostgreSQL) | — |
| 資料庫 | PostgreSQL | 17 |
| 前台 | Next.js (App Router) → Linode | 15.5.15 |
| Admin 後台 | Next.js (App Router) → Linode | 15.5.15 |
| 檔案儲存 | Cloudflare R2 | S3-compatible |
| AI | OpenAI API | gpt-5.4 |
| Email | Resend | — |
| GeoIP | Cloudflare CF-IPCountry header | — |
| Hosting | Linode（API + DB + Web + Admin） | — |
| CI/CD | GitHub Actions | — |

---

## AI Product Advisor MVP

目前已上線的 AI Product Advisor 採用「強掛載 + 條件掛載」策略，避免全站無差別掛載造成低品質回答與雜訊事件。

### 掛載範圍

- 強掛載：FAQ 頁、FAQ tag 頁、產品詳頁
- 條件掛載：首頁、產品總覽頁、產品分類頁、應用總覽頁、應用詳頁
- 不掛載：法務頁、純品牌資訊頁、低內容密度頁面

### 支援的 context 類型

- `home`
- `category`
- `application`
- `product`
- `faq`

### 事件與 handoff

- `chat_start`：訪客開啟 chat session 時寫入 `tracking_events`
- `chat_rfq_handoff`：AI 判定可導向 RFQ 並完成 handoff 時寫入 `tracking_events`
- handoff 會回傳 `rfq_prefill_url`，供前台直接導到預填詢價頁

### API endpoints

```bash
POST /api/v1/chat/sessions
POST /api/v1/chat/sessions/{chat_session_id}/messages
POST /api/v1/chat/sessions/{chat_session_id}/handoff
```

### 本地最小驗證

```bash
cd api && source .venv/bin/activate
python -m pytest tests/test_chat.py -q

cd ../web
npm run type-check
```

---

## AI 行銷專員（AI Marketing Copilot）

ForgeBase v0.22 引入 AI 行銷專員模組—一個串接真實 CRM 資料的 Telegram 對話 AI，讓業務主管可以在 Telegram 直接查詢 RFQ 狀態、識別高意圖訪客、接收事件通知，並獲得針對製造業 B2B 銷售情境的行動建議。

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
                               LLM (gpt-5.4)
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
| `api/app/services/channels/telegram.py` | Telegram Bot API 頻道實作（含 webhook 驗證、binding code 發送）|
| `api/app/api/v1/endpoints/copilot.py` | Preferences CRUD + Telegram 綁定流程 + Telegram webhook 接收器 |

### 可用的 AI 工具（tools.py）

| 工具 | 功能 |
|------|------|
| `get_dashboard_stats(hours)` | KPI 快照：新 RFQ、緊急 RFQ、超時未回、熱訪客數、開案漏斗 |
| `list_rfqs(status, priority, limit)` | 過濾 RFQ 列表 |
| `get_rfq_detail(rfq_number)` | 單筆 RFQ 完整資料（表單、聯絡人、同公司歷史、產品關聯）|
| `list_hot_visitors(limit)` | 當前 hot / sales_ready 訪客列表 |
| `get_visitor_profile(visitor_id)` | 訪客深度檔案（意圖歷程、身份解析、RFQ 歷史）|
| `list_overdue_rfqs(hours)` | 超 SLA 未回應的 RFQ 列表 |
| `get_contact_profile(email)` | 聯絡人完整檔案（所有 RFQ + 訪客行為連結）|
| `search_contacts(query)` | 跨 name / company / country / email 模糊搜尋 |
| `get_product_interest_stats(days)` | 依 RFQ 量排序的產品需求榜 |
| `get_funnel_stats(days)` | 訪客 → 聯絡人 → RFQ → 成交漏斗 |

### 初始設定

#### 1. 環境變數

```bash
# api/.env
TELEGRAM_BOT_TOKEN=<從 @BotFather 取得>
TELEGRAM_WEBHOOK_SECRET=<自定義隨機字串，用於驗證 webhook 來源>
```

#### 2. DB Migration

```bash
cd api && source .venv/bin/activate
alembic upgrade head   # 套用 0038_copilot_notifications
```

#### 3. 註冊 Telegram Webhook

```bash
# 在 production URL 上操作
curl -X POST https://mitselect.com/api/v1/copilot/telegram/setup-webhook \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://mitselect.com/api/v1/copilot/webhook/telegram"}'
```

> `TELEGRAM_WEBHOOK_SECRET` 會自動帶入 `setWebhook` 的 `secret_token` 參數，確保只有 Telegram 才能呼叫此端點。

#### 4. 綁定 Telegram 帳號（Admin 端）

1. 前往 `/backend/dashboard/settings/notifications`
2. 輸入你的 Telegram chat_id（可在 @userinfobot 取得）
3. 點「發送驗證碼」— Bot 會發一組 6 位碼
4. 輸入驗證碼完成綁定
5. 選擇要開啟的事件通知（新 RFQ、熱訪客、每日摘要等）

### Admin 後台頁面

| 路由 | 功能 |
|------|------|
| `/backend/dashboard/notifications` | 通知中心：最近 100 筆通知紀錄，支援 channel / event / status 篩選 |
| `/backend/dashboard/settings/notifications` | 通知設定：Telegram 綁定流程、各事件開關、靜音時段 |

### API Endpoints

```bash
GET    /api/v1/copilot/preferences           # 列出目前使用者的通知偏好設定
POST   /api/v1/copilot/preferences           # 新增偏好設定
PUT    /api/v1/copilot/preferences/{id}      # 更新開關 / 靜音時段
DELETE /api/v1/copilot/preferences/{id}      # 刪除
GET    /api/v1/copilot/notifications         # 通知歷史（最近 100 筆）
POST   /api/v1/copilot/telegram/bind-start   # 步驟一：產生綁定碼並發到 Telegram
POST   /api/v1/copilot/telegram/bind-verify  # 步驟二：驗證碼核對，啟用綁定
POST   /api/v1/copilot/telegram/setup-webhook # （admin）向 Telegram 登記 webhook URL
POST   /api/v1/copilot/webhook/telegram       # Telegram Bot webhook 接收端（public）
```

### 事件觸發點

| 事件 | 觸發位置 |
|------|----------|
| `new_rfq` | `api/app/api/v1/endpoints/rfqs.py` — RFQ 建立後呼叫 `on_new_rfq()` |
| `hot_visitor` | `api/app/api/v1/endpoints/events.py` — 訪客升至 hot/sales_ready 時呼叫 `on_hot_visitor()` |
| `chat_handoff` | `api/app/api/v1/endpoints/chat.py` — AI chat handoff 完成時呼叫 `on_chat_handoff()` |
| `churn_risk` | `api/app/services/score_decay.py` — 意圖分數衰減觸發降級時呼叫 `on_churn_risk()` |
| `daily_summary` | APScheduler，每日 08:00 Asia/Taipei 執行 `run_daily_digest()` |

### 通知路由邏輯

`send_notification()` 依序執行：

1. **去重**：同一 `(event_type, event_ref_id)` 在 5 分鐘內只送一次
2. **靜音時段**：尊重每位使用者設定的 `quiet_hours_start / quiet_hours_end`（支援跨日，例如 22:00 → 08:00）
3. **逐一發送**：呼叫對應 channel handler（目前支援 `telegram`）
4. **寫入 log**：每次送出都寫入 `notification_logs`（sent / failed / skipped_quiet_hours）

---

## Legacy Site Intake

ForgeBase 已包含正式的 Legacy Site Intake 模組，用來把既有製造商官網、型錄站或混合型內容站，轉成可審核的 ForgeBase 導入資料。以目前 repo 狀態來看，這不是概念驗證，而是已落地到資料表、API、admin 審核介面、測試與實測腳本的模組。

### 目前能力範圍

- 建立 intake project，輸入 `project_name`、`source_url`、`locale`
- Phase 1 `discover`：爬取站內 HTML 與 PDF，建立 URL candidates，並分類為 `product`、`category`、`application`、`faq`、`contact`、`resource` 等頁型
- Phase 2 `extract`：抽取 entity candidates、redirect candidates、PageBrief drafts
- Admin 審核：於 admin 後台 `/dashboard/intake` 檢視、接受、略過或編修候選資料
- Commit：可將已接受的 category / product / application / certification / FAQ entity candidates 寫回 ForgeBase 正式資料表，並同步建立 redirect、PageBrief 與主要內容關聯

### Commit 後會寫入哪些正式資料

- `ProductCategory`
- `Product`
- `Application`
- `Certification`
- `FAQItem`
- `Redirect`
- `PageBrief`

同時會補上部分內容關聯：

- Product -> Application
- Product -> Certification
- Product -> FAQ
- Application -> FAQ

### 主要實作位置

- API：`/api/v1/intake/*`
- Backend service：`api/app/services/intake_engine.py`
- Backend endpoints：`api/app/api/v1/endpoints/intake.py`
- Admin UI：`admin/src/app/(dashboard)/dashboard/intake/page.tsx`
- Migration：`api/app/db/migrations/versions/0025_legacy_site_intake.py`
- Tests：`api/tests/test_intake.py`
- Standalone scripts：`api/scripts/intake_pipeline_king_a.py`、`api/scripts/test_intake_king_a.py`
- Output artifacts：`intake_output/king_a_crawl_raw.json`、`intake_output/king_a_forgebase_seed.json`、`intake_output/king_a_analysis_report.json`

### Intake API 範圍

```bash
POST /api/v1/intake/projects
GET  /api/v1/intake/projects
GET  /api/v1/intake/projects/{id}
PATCH /api/v1/intake/projects/{id}
POST /api/v1/intake/projects/{id}/discover
POST /api/v1/intake/projects/{id}/extract
GET  /api/v1/intake/projects/{id}/urls
PATCH /api/v1/intake/urls/{id}/review
GET  /api/v1/intake/projects/{id}/entities
PATCH /api/v1/intake/entities/{id}/review
GET  /api/v1/intake/projects/{id}/redirects
PATCH /api/v1/intake/redirects/{id}/review
GET  /api/v1/intake/projects/{id}/briefs
PATCH /api/v1/intake/briefs/{id}/review
POST /api/v1/intake/projects/{id}/commit
GET  /api/v1/intake/projects/{id}/summary
```

### 使用前提與本地驗證

正式使用 `/api/v1/intake/*` 時，需具備：

- 已完成 DB migration `0025_legacy_site_intake`
- 可登入 admin / API 的授權帳號
- 對外網路抓站能力
- `OPENAI_API_KEY`

本地可先用以下方式驗證：

```bash
cd api
python -m pytest tests/test_intake.py -q

# Standalone 實測，不需要 DB，輸出會寫到 intake_output/
python scripts/intake_pipeline_king_a.py
```

---

## 快速開始

### 環境需求

- Python 3.13+
- Node.js 20+
- PostgreSQL 17（本地直接安裝 或透過 Docker）

### 本地開發啟動

```bash
# 0. 建立本地 PostgreSQL user 與 database（首次設定）
#    Windows：使用 psql 或 pgAdmin；macOS/Linux：
createuser -s forgebase
createctl forgebase --owner=forgebase
# 或直接執行：
# psql -U postgres -c "CREATE USER forgebase WITH PASSWORD 'forgebase_dev';"
# psql -U postgres -c "CREATE DATABASE forgebase OWNER forgebase;"

# 1. 後端 API
cd api
cp .env.example .env          # 填入 DB_URL、SECRET_KEY 等環境變數
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head           # 套用全部 DB migrations（0001 → 0034）
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000

# 2. 前台網站
cd web
cp .env.local.example .env.local
npm install
npm run dev
# → http://localhost:3000

# 3. 管理後台
cd admin
cp .env.local.example .env.local
npm install
npm run dev
# → http://localhost:3001
```

### 健康檢查

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

### 多租戶前台 Smoke Test

驗證多租戶品牌隔離是否正常（title、canonical、theme、layout、robots、sitemap、favicon）：

```powershell
# Windows PowerShell（自動啟動 mock server + Next.js dev server）
.\scripts\smoke-test.ps1

# 若 server 已在執行
.\scripts\smoke-test.ps1 -SkipServerStart
```

Smoke test 成功輸出範例：

```
--- Tenant: tenant-a.localhost:3000
  [PASS] Title contains brand
  [PASS] Canonical URL
  [PASS] data-theme
  [PASS] data-layout
  ...
  Smoke Test Results: 13 passed, 0 failed
```

### Demo 資料注入（選用）

以示範公司「NorthForge 手工具製造商」為例，依序執行三個腳本：

```bash
# 在 api 目錄下執行（使用 api/.venv）
cd api && source .venv/bin/activate

# 步驟一：匯入產品、應用、認證、FAQ 等內容資料
python3 ../demo/handtool-company/seed/import_demo_content.py
# → 5 分類 / 32 產品 / 6 應用 / 5 認證 / 18 FAQ / 8 比較主題

# 步驟二：注入模擬訪客行為資料（已有資料時可略過）
python3 ../demo/handtool-company/seed/seed_demo_visitors.py
# → 14 訪客 / 10 RFQ / 14 聯絡人 / 69 事件（含 Thomas/Sarah/Marco 等 demo 角色）

# 步驟三：注入 Page Briefs、CTAs（已有資料時可略過）
python3 ../demo/handtool-company/seed/seed_demo_briefs_ctas_nurture.py
# → 8 個 Page Briefs（各狀態）/ 4 個 CTA
```

注入成功後，管理後台（:3001）可立即看到 Cold / Warm / Hot / Sales-Ready 各階段訪客、RFQ 收件箱、Page Brief 列表、CTA 規則。

---

## 開發規範

- API 版本前綴：`/api/v1/`
- 所有 API 回應格式：`{"data": ..., "meta": ...}` 或 `{"error": ...}`
- DB migration：`alembic revision --autogenerate -m "描述"` 後 commit
- 環境變數：`.env.example` 保持更新，**絕不 commit 真實 `.env`**
- 所有 AI 生成必須有對應的 PageBrief（Approved 狀態）才能觸發

---

## GitHub 與 Linode 部署

### GitHub repository

| 項目 | 值 |
|------|----|
| **Git remote** | `git@github.com:stevechen1112/ForgeBase2026.git` |
| **CI/CD workflow** | `.github/workflows/deploy.yml` |
| **自動部署分支** | `main` |
| **目前常用開發分支** | `refactor/consolidate-analytics-pages` |

### GitHub Actions 自動部署

目前 production 自動部署是由 GitHub Actions 觸發，條件是 push 到 `main`。

```bash
# 開發完成後
git checkout main
git pull origin main
git merge <your-feature-branch>
git push origin main
```

`.github/workflows/deploy.yml` 會在 Linode 依序執行：

1. `git pull origin main`
2. `cd api && source .venv/bin/activate && pip install -r requirements.txt`
3. `alembic upgrade head`
4. `systemctl restart forgebase-api`
5. `cd web && npm ci && npm run build`
6. `cd admin && npm ci && npm run build`
7. `systemctl restart forgebase-web forgebase-admin`
8. `curl https://mitselect.com/health` 驗證 health check

GitHub repository 需先設定以下 Secrets：

- `DEPLOY_HOST=172.234.81.223`
- `DEPLOY_SSH_KEY=<Linode deploy private key>`

### 手動 SSH 部署到 Linode

若目前變更仍在 feature branch，或不想先 merge 到 `main`，可以直接 SSH 到 Linode 手動部署：

```bash
ssh -i ~/.ssh/forgebase_deploy root@172.234.81.223

cd /opt/forgebase/app
git fetch origin
git checkout refactor/consolidate-analytics-pages
git pull origin refactor/consolidate-analytics-pages

cd /opt/forgebase/app/api
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
systemctl restart forgebase-api

cd /opt/forgebase/app/web
npm ci --prefer-offline
npm run build
systemctl restart forgebase-web

cd /opt/forgebase/app/admin
npm ci --prefer-offline
npm run build
systemctl restart forgebase-admin

curl -sf https://mitselect.com/health
systemctl is-active forgebase-api forgebase-web forgebase-admin
```

### 2026-04-10 本次 GitHub / Linode 更新重點

本次同步到 GitHub 與 Linode 的內容包含：

- 多租戶方案功能裁切正式落地到 Admin 導覽、頁面入口與 inline upgrade UX
- `chat_admin`、`visitors`、`segments`、`ml_scoring`、`redirects`、`ai_generate`、`analytics`、`events` 等 API 全面補上 plan gate
- analytics 與 strategy performance 查詢補齊 tenant filter，避免跨租戶混讀資料
- 多個 admin analytics 頁面改回 `apiClient`，避免 token 過期造成 401 壞頁

這次沒有新增 Alembic migration，但 production 仍建議維持標準部署順序：

1. push 分支到 GitHub
2. Linode `git pull`
3. `pip install -r requirements.txt`
4. `alembic upgrade head`
5. 重建 admin / web
6. restart systemd services

### Linode 上的實際路徑

| 路徑 | 用途 |
|------|------|
| `/opt/forgebase/app` | production repo root |
| `/opt/forgebase/app/api` | FastAPI 專案 |
| `/opt/forgebase/app/web` | 前台 Next.js |
| `/opt/forgebase/app/admin` | Admin Next.js |
| `/etc/nginx/sites-available/forgebase` | nginx 設定檔 |

---

---

## 生產環境（mitselect.com）

| 項目 | 值 |
|------|----|
| **網站** | https://mitselect.com |
| **管理後台** | https://mitselect.com/backend/login |
| **API** | https://mitselect.com/api/v1/ |
| **伺服器** | Linode Ubuntu 24.04，IP `172.234.81.223` |
| **SSH** | `ssh -i ~/.ssh/forgebase_deploy root@172.234.81.223` |
| **部署目錄** | `/opt/forgebase/app` |
| **DB** | `postgresql://forgebase:***REMOVED***@localhost:5432/forgebase` |
| **Admin 帳號** | 見 `.env` 的 `ADMIN_EMAIL` / `ADMIN_PASSWORD` |
| **SSL 憑證** | Let's Encrypt，到期 2026-06-13（certbot auto-renew） |

### Systemd 服務

| 服務 | Port | 說明 |
|------|------|------|
| `forgebase-api` | 8000 | FastAPI |
| `forgebase-web` | 3000 | 前台 Next.js |
| `forgebase-admin` | 3001 | 管理後台 Next.js |

```bash
# API
cd /opt/forgebase/app/api
source .venv/bin/activate
alembic upgrade head
systemctl restart forgebase-api

# Web
cd /opt/forgebase/app/web
npm ci --prefer-offline
npm run build
systemctl restart forgebase-web

# Admin
cd /opt/forgebase/app/admin
npm ci --prefer-offline
npm run build
systemctl restart forgebase-admin
```

### 重要注意事項

- **HTTPS Mixed Content**：`NEXT_PUBLIC_API_URL` 必須設為 `https://mitselect.com`（不可用 HTTP 或 IP），否則瀏覽器會封鎖所有 API 請求
- **nginx `/backend` 路由**：`location /backend {`（無 trailing slash），`proxy_pass http://127.0.0.1:3001`（也無 trailing slash）— 兩端都有 `/` 會導致 404
- **Next.js standalone 靜態資產**：前後台都依賴 `postbuild` 自動執行 `scripts/prepare-next-standalone.sh`，重建 `.next/standalone/public` 與 `.next/standalone/.next/static` 的 symlink；不要再手動 `cp -r public` 或 `cp -r .next/static`
- **GitHub Actions CI/CD**：production 自動部署只監聽 `main`；若你在 feature branch 開發，需先 merge 到 `main`，或改走上面的手動 SSH 部署

更完整的部署檢查與維運紅線，請見 `ForgeBase_部署與維運注意事項.md`。

---

## 文件

| 文件 | 說明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 技術架構與選型決策紀錄 |
| [ForgeBase_產品規格文件.md](ForgeBase_產品規格文件.md) | 完整產品功能規格 |
| [ForgeBase_Legacy_Site_Intake_產品規格草案.md](ForgeBase_Legacy_Site_Intake_產品規格草案.md) | Legacy Site Intake 模組規格與產品化方向 |
| [ForgeBase_Legacy_Site_Intake_操作與Demo指南.md](ForgeBase_Legacy_Site_Intake_操作與Demo指南.md) | Legacy Site Intake 實際操作、審核標準與 demo 順序 |
| [ForgeBase_完整開發計畫.md](ForgeBase_完整開發計畫.md) | 開發里程碑計畫 |
| [ForgeBase_Demo指導文件.md](ForgeBase_Demo指導文件.md) | Demo 流程與話術指引 |
| [ForgeBase_部署與維運注意事項.md](ForgeBase_部署與維運注意事項.md) | production 部署、standalone 資產檢查與維運紅線 |
| [ForgeBase_前後台改造說明.md](ForgeBase_前後台改造說明.md) | 本次改造評估與工作項目（程式碼實查版）|

---

## 版本更新紀錄

### v0.20 — 多租戶修復 + 前台 Runtime 白標收斂（2026-04-14）

本次改造聚焦多租戶正確性與前台 SaaS 白標彈性，共完成 3 個方向的系統性修補。

#### 後端多租戶修復

| 類別 | 變更 |
|------|------|
| **DB Models** | 所有剩餘 content tables 補上 `tenant_id` 欄位 |
| **Unique constraints** | 由全域唯一改為 `(slug, tenant_id)` 或 `(slug, locale, tenant_id)` 複合唯一 |
| **Endpoints** | 全部 content / chat / intake / publish / relations API 修正 tenant 隔離邏輯 |
| **AI 生成** | `AIGenerationLog` 補上 `tenant_id`，生成結果不跨租戶混讀 |
| **Migration** | 新增 `0034_multitenant_content_phase3`（head）|
| **Migration 修復** | `0025_drop_phase2_residuals` 改用 `IF EXISTS`，修正對新 DB 的相容性問題 |

#### 前台 Runtime 白標收斂

| 類別 | 變更 |
|------|------|
| **核心** | 新增 `web/src/lib/runtimeSiteConfig.ts`，每次請求從 API `/api/v1/site-profile` 取得租戶品牌設定 |
| **全頁面遷移** | `web/src/app/**` 所有頁面從靜態 `siteConfig` 改為 `getRuntimeSiteContext()` + async `generateMetadata()` |
| **robots / sitemap** | `robots.ts`、`sitemap.ts` 改用 runtime site URL，每個租戶獨立 |
| **favicon** | 動態路由根據 `SiteProfile.favicon_url` 供應不同圖示 |
| **SEO** | canonical、`og:url`、`og:site_name` 全部 runtime 化 |

#### 驗證結果

- **Alembic**：`0001 → 0034` 全部 migration 成功
- **後端測試**：`52 passed, 3 skipped, 0 failed`
- **前台 Smoke Test**：`13 passed, 0 failed`（兩個測試租戶品牌、canonical、theme、favicon 完全隔離）
- **TypeScript type-check**：zero errors

---

### v0.18 — 成長網站強化改造（2026-03-15）

本次改造聚焦「B2B 行銷漏斗可視化與 CTA 意圖分階」，共完成 23 項工作項目，新增 1 個 Alembic migration（0018）。

#### 後端 API（FastAPI）

| 類別 | 變更 |
|------|------|
| **DB Model** | `products` 新增 `is_featured` (bool)、`display_priority` (int) |
| **DB Model** | `rfq_requests` 新增 `first_response_at`、`quote_sent_at`、`lost_reason` |
| **DB Model** | `ctas` 新增 `target_intent_stage` (cold / warm / hot / any) |
| **Migration** | `0018_growth_site_fields.py` — 三表統一 migration |
| **API** | `GET /products?featured=true` — 主推產品篩選 + `display_priority` 排序 |
| **API** | `PUT /rfqs/{id}/follow-up` — 記錄首次回覆/報價/未成交原因 |
| **API** | `GET /tracking/analytics/funnel` — 漏斗分析（意圖階段分佈、RFQ 狀態、轉換率）|
| **Service** | `dynamic_cta.py` 新增 `target_intent_stage` 過濾邏輯 |

#### 管理後台（Admin Next.js）

### v0.20 — 多租戶 SaaS 基礎建設（2026-04-09）

將單租戶架構升級為支援多租戶的 SaaS 基礎，並強化 API 安全性與 auth contract 一致性。

| 類別 | 變更 |
|------|------|
| **DB** | 新增 `tenants` 資料表，含 plan / max_products / max_admins / PayPal 欄位 |
| **DB** | `users` 新增 `tenant_id` FK |
| **DB** | `products`、`rfq_requests`、`briefs`、`pages` 等核心模型新增 `tenant_id` FK |
| **Migration** | `0027_add_tenant_id_to_core_models`、`0028_merge_site_profile_and_multitenant_heads`（合併 revision）|
| **API** | `POST /auth/register` — 建立 Tenant + owner 帳號（需 `REGISTRATION_KEY` 環境變數保護）|
| **API** | `POST /subscription/checkout|activate|upgrade|cancel` — 改為 `require_owner`，移除 inline 角色判斷 |
| **API** | `PUT|DELETE /admin/integrations/{service}/{key}` — 升為 `require_admin`（原為 content_editor）|
| **API** | `PUT /site-profile` — 升為 `require_admin`（原無角色保護）|
| **API** | Team invite / update — owner 才能邀請或晉升 admin 角色 |
| **API** | 新增 `require_owner` dependency；移除 `require_super_admin`（原與 `require_admin` 完全相同）|
| **API** | `/auth/team` 系列統一回傳 `UserRead`（移除手動 mapping 的 `TeamMemberOut`）|
| **Admin** | `client.ts` 加入 token 自動 refresh 機制（401 → 先嘗試 refresh → 失敗才登出）|
| **Admin** | Billing 頁方案比較表修正（Starter: 2 管理員；Professional: 無限額）|
| **Admin** | 側欄導覽重構：移除「自動化」群組、整合設定移入「系統」、`owner` 角色可見系統管理選單 |

### v0.22 — AI 行銷專員（AI Marketing Copilot）（2026-04-14）

Phase 1 完整事件通知系統 + Phase 2 全 LLM 對話引擎，讓業務主管在 Telegram 直接存取真實 CRM 數據並獲得 B2B 製造業行銷建議。

#### Phase 1 — 事件通知系統

| 類別 | 變更 |
|------|------|
| **DB Models** | 新增 `NotificationPreference`、`NotificationLog`、`CopilotConversation` 三個資料模型 |
| **Migration** | `0038_copilot_notifications` |
| **Channels** | `TelegramChannel`（`services/channels/telegram.py`），含 HMAC webhook 驗證、binding code 流程 |
| **Router** | `notification_router.py` — 統一分發：去重 → 靜音時段 → 送出 → log |
| **Monitor** | `copilot/monitor.py` — 4 個事件處理器（new_rfq / hot_visitor / chat_handoff / churn_risk），new_rfq 通知含 AI RFQ 摘要 |
| **Digest** | `copilot/digest.py` — 每日 08:00 Asia/Taipei 執行，產生 24h KPI + AI 行動建議 |
| **APScheduler** | `main.py` 新增 `daily_copilot_digest` job |
| **API** | `/copilot/preferences` CRUD + `/copilot/telegram/bind-start|bind-verify|setup-webhook` |
| **Admin** | 通知設定頁（Telegram 綁定 + 事件開關 + 靜音時段） |
| **Admin** | 通知中心頁（最近 100 筆，支援篩選） |
| **Sidebar** | 新增「AI 行銷專員」群組（通知中心 + 通知設定）|

#### Phase 2 — LLM 對話引擎

| 類別 | 變更 |
|------|------|
| **CopilotEngine** | `copilot/chat_engine.py` — 完整 LLM 對話引擎：20 則持久歷史、最多 6 次 tool call 迴圈、Telegram 分段輸出 |
| **Tools** | `copilot/tools.py` — 10 個 tenant-scoped DB 查詢工具，透過 function calling 供 LLM 呼叫 |
| **System Prompt** | 內建台灣外銷製造業 B2B 域知識（採購週期、RFQ 優先級框架、買家國家輪廓、跟進策略）|
| **Webhook 改造** | `copilot.py` webhook 改用 FastAPI `BackgroundTasks`，立即回應 200、非同步送出 LLM reply |
| **Typing 指示器** | 每次 LLM 運算前發送 `sendChatAction: typing`，長回答分段時也會重新觸發 |
| **去除舊碼** | 移除 Phase 1 的關鍵字比對邏輯（`_handle_copilot_message`），完全由 LLM 接手 |

#### Code Review Fixes（同次 commit）

| 類別 | 修正 |
|------|------|
| 🔴 | `tools.py` `get_product_interest_stats()`：`col("cnt")` runtime 崩潰 → 改為 `func.count(...).desc()` |
| 🟠 | `monitor.py` `on_new_rfq()`：OpenAI API call 在 DB session 內執行 → 移至 session 關閉後執行 |
| 🟠 | `copilot.py` webhook：`channel_config.contains(chat_id)` 子字串誤判 → 改 Python 端 JSON 精確比對 |
| 🟡 | `tools.py` / `digest.py` / `chat_engine.py`：`datetime.utcnow()` 淘汰 API（10 處）→ 全部改用 `utcnow_naive()` |
| ⚪ | `tools.py`：移除未使用的 `NotificationPreference` import |
| ⚪ | `notification_router.py`：移除未使用的 `datetime`, `timezone` import |

---

### v0.21 — 方案驅動功能裁切與權限收斂（2026-04-10）

將多租戶 SaaS 從「有方案資料」推進到「方案真正影響產品行為」，並補齊前後台權限一致性。

| 類別 | 變更 |
|------|------|
| **Admin** | 新增 `PlanProvider`、`usePlan`、`PlanGate`，改由 `subscription/current` 回傳的 feature flags 驅動 UI |
| **Admin** | Sidebar 依方案自動裁切，Starter 進入 Professional 功能時統一導向 billing 升級流程 |
| **Admin** | `chats`、`intent`、`ml-scoring`、`content-optimizer`、`redirects`、`segments`、`visitors`、`multilingual`、`ctas`、`analytics/*` 改為 route-level gating |
| **Admin** | Dashboard 與 Strategies 頁新增 inline upgrade UX，避免 Starter 看見 403 或壞掉的圖表卡片 |
| **Admin** | analytics / funnel / strategy / content-performance / dashboard 等頁面改回 `apiClient`，避免 token 過期時 401 壞頁 |
| **API** | 新增 `RequireFeature` dependency，依 tenant plan 封鎖 Professional-only endpoints |
| **API** | `chat_admin`、`visitors`、`segments`、`ml_scoring`、`redirects`、`ai_generate`、`analytics`、`events` 等 endpoint 全面接上 feature gate |
| **API** | 修正 analytics 與 strategy performance 查詢的 tenant filter，避免跨租戶資料混讀 |
