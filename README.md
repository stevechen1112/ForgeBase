# ForgeBase

**外銷製造商官網成長系統** — Expose · Engage · Capture · Follow-up

ForgeBase 是專為中小型外銷製造商設計的 B2B 網站成長平台。核心理念：**讓產品被找到、讓買家意圖被看見、讓每筆詢價都被接住。**

---

## 行銷漏斗四階段

ForgeBase 的功能對應外銷製造商從曝光到成交的完整歷程：

| 階段 | 名稱 | 核心問題 | ForgeBase 功能 |
|------|------|----------|---------------|
| **1. 曝光** | 被找到 | 買家在 Google 搜到我嗎？ | SEO 基礎設施、sitemap、schema、多語言、AI 內容生成 |
| **2. 互動** | 站內行為 | 買家看了什麼？多有興趣？ | 行為追蹤（15 種事件）、意圖評分、Dynamic CTA、AI Product Advisor |
| **3. 留資** | 詢價轉換 | 買家願意報上名嗎？ | RFQ 表單、聯絡表單、Chat → RFQ handoff |
| **4. 跟進** | 業務接住 | 每筆詢價有人跟、跟得好嗎？ | 即時通知、逾時催辦、培育信、狀態管理 |

---

## 核心功能

| 模組 | 說明 | 漏斗階段 |
|------|------|----------|
| **SEO 基礎設施** | canonical、sitemap、JSON-LD schema 自動生成、SEO 重導向管理 | 曝光 |
| **多語言支援** | 英文 + 繁體中文，hreflang 自動產生 | 曝光 |
| **AI 內容生成** | 基於 PageBrief 工作流，AI 自動起草產品頁、應用頁、FAQ | 曝光 |
| **訪客追蹤 & 意圖評分** | 自動記錄 page_view / product_view / cta_click 等 15 種事件，計算 Cold → Warm → Hot → Sales-Ready 階段 | 互動 |
| **Dynamic CTA** | 依訪客買家階段動態切換行動呼籲按鈕 | 互動 |
| **AI Product Advisor** | FAQ 頁、產品詳頁嵌入情境式 AI 對話，導向 RFQ | 互動 → 留資 |
| **RFQ 詢價表單** | 結構化詢價，含產品需求、數量、時程等欄位 | 留資 |
| **聯絡表單** | 一般詢問留資 | 留資 |
| **Chat → RFQ Handoff** | AI 對話中判定購買意圖後，自動導向預填 RFQ | 留資 |
| **GeoIP 國家識別** | 訪客國家自動標記 | 互動 |
| **靜態資產管理** | 產品圖、PDF 規格書上傳至 Cloudflare R2 | 全階段 |

---

## SaaS 方案分層

兩層方案 + 按需 add-on，對應客戶成長階段：

### Starter 入門（$99–199/月）

**定位：數位型錄 + 詢價入口**

| 漏斗階段 | 功能 |
|----------|------|
| 曝光 | 前台官網（英文）、SEO 基礎（canonical / sitemap / schema） |
| 互動 | 基礎追蹤（page_view） |
| 留資 | RFQ 詢價表單、聯絡表單 |
| 跟進 | — |
| 限制 | 產品 50 筆、管理員 2 組 |

> 升級誘因：「你有 5 筆新詢價，但你不知道其中 2 位早就看了你 12 個產品頁。」

### Professional 專業（$499–899/月）

**定位：意圖識別 + AI 導購 + 業務跟進全閉環**

含 Starter 全部，加上：

| 漏斗階段 | 功能 |
|----------|------|
| 曝光 | 多語言（EN + zh-TW）、AI 內容生成（PageBrief 工作流）、SEO Redirect 管理 |
| 互動 | 完整行為追蹤（15 種事件）、意圖評分引擎、意圖儀表板、Dynamic CTA、GeoIP、AI Product Advisor |
| 留資 | Chat → RFQ handoff |
| 跟進 | 即時通知（RFQ / 聯絡 / handoff / 意圖突破閾值 / 回訪通知）、逾時催辦（24h 提醒 / 72h 升級主管）、培育信（確認信自動 + 3 封人工確認） |
| 限制 | 產品無上限、管理員無上限 |

### 按需 Add-on

有客戶明確需求時再啟用，不預建：

| Add-on | 月費 |
|--------|------|
| HubSpot CRM 同步 | +$200 |
| Google Ads 轉換回傳 | +$150 |
| Meta CAPI 轉換回傳 | +$150 |
| Webhook 整合 | +$100 |

---

## 專案結構

```
ForgeBase/
├── api/                    # 後端 API (Python 3.10 + FastAPI)
│   ├── app/
│   │   ├── api/v1/         # REST endpoints
│   │   ├── db/migrations/  # Alembic migrations (20 版本)
│   │   ├── models/         # SQLModel 資料模型
│   │   └── schemas/        # Pydantic 輸入/輸出 schema
│   ├── .venv/              # API 專用虛擬環境
│   └── .env.example
├── web/                    # 前台網站 (Next.js 15，部署 Vercel)
│   └── .env.local.example
├── admin/                  # 管理後台 (Next.js 15，部署 Linode)
│   └── .env.local.example
├── demo/                   # Demo 示範資料與種子腳本
│   └── handtool-company/   # 示範公司（手工具製造商）
│       └── seed/           # 模擬訪客行為注入腳本
├── shared/                 # 共用型別與常數
├── ARCHITECTURE.md         # 技術架構決策紀錄
└── .github/                # CI/CD workflows
```

---

## 技術棧

| 層級 | 技術 | 版本 |
|------|------|------|
| 後端 API | Python + FastAPI + SQLModel + Alembic | 3.10 / 0.115 / 0.0.21 / 1.13 |
| 資料庫驅動 | asyncpg (async PostgreSQL) | — |
| 資料庫 | PostgreSQL | 16 |
| 前台 | Next.js (App Router) → Vercel | 15.2 |
| Admin 後台 | Next.js (App Router) → Linode | 15.2 |
| 檔案儲存 | Cloudflare R2 | S3-compatible |
| AI | OpenAI API | gpt-5.4 |
| Email | Resend | — |
| GeoIP | Cloudflare CF-IPCountry header | — |
| Hosting | Linode（API + DB + Admin） | — |
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

## 快速開始

### 環境需求

- Python 3.10+
- Node.js 20+
- PostgreSQL 16（本地直接安裝 或透過 Docker）

### 本地開發啟動

```bash
# 1. 後端 API
cd api
cp .env.example .env          # 填入 DB_URL、SECRET_KEY 等環境變數
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head           # 套用全部 DB migrations
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
curl http://localhost:8000/api/v1/health
# → {"status": "ok"}
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

---

## 生產環境（mitselect.com）

| 項目 | 值 |
|------|----|
| **網站** | https://mitselect.com |
| **管理後台** | https://mitselect.com/backend/login |
| **API** | https://mitselect.com/api/v1/ |
| **伺服器** | Linode Ubuntu 24.04，IP `172.234.81.223` |
| **SSH** | `ssh -i ~/.ssh/forgebase_deploy root@172.234.81.223` |
| **DB** | `postgresql://forgebase:***REMOVED***@localhost:5432/forgebase` |
| **Admin 帳號** | `admin@forgebase.com` / `ForgeBase2026` |
| **SSL 憑證** | Let's Encrypt，到期 2026-06-13（certbot auto-renew） |

### Systemd 服務

| 服務 | Port | 說明 |
|------|------|------|
| `forgebase-api` | 8000 | FastAPI |
| `forgebase-web` | 3000 | 前台 Next.js |
| `forgebase-admin` | 3001 | 管理後台 Next.js |

```bash
# 重新部署前端（兩個前端流程相同）
cd /opt/forgebase/app/web   # 或 admin
npm ci --prefer-offline
npm run build
systemctl restart forgebase-web   # 或 forgebase-admin
```

### 重要注意事項

- **HTTPS Mixed Content**：`NEXT_PUBLIC_API_URL` 必須設為 `https://mitselect.com`（不可用 HTTP 或 IP），否則瀏覽器會封鎖所有 API 請求
- **nginx `/backend` 路由**：`location /backend {`（無 trailing slash），`proxy_pass http://127.0.0.1:3001`（也無 trailing slash）— 兩端都有 `/` 會導致 404
- **Next.js standalone 靜態資產**：前後台都依賴 `postbuild` 自動執行 `scripts/prepare-next-standalone.sh`，重建 `.next/standalone/public` 與 `.next/standalone/.next/static` 的 symlink；不要再手動 `cp -r public` 或 `cp -r .next/static`
- **GitHub Actions CI/CD**：需在 GitHub → Settings → Secrets 設定 `DEPLOY_HOST=172.234.81.223` 與 `DEPLOY_SSH_KEY`

更完整的部署檢查與維運紅線，請見 `ForgeBase_部署與維運注意事項.md`。

---

## 文件

| 文件 | 說明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 技術架構與選型決策紀錄 |
| [ForgeBase_產品規格文件.md](ForgeBase_產品規格文件.md) | 完整產品功能規格 |
| [ForgeBase_完整開發計畫.md](ForgeBase_完整開發計畫.md) | 開發里程碑計畫 |
| [ForgeBase_Demo指導文件.md](ForgeBase_Demo指導文件.md) | Demo 流程與話術指引 |
| [ForgeBase_部署與維運注意事項.md](ForgeBase_部署與維運注意事項.md) | production 部署、standalone 資產檢查與維運紅線 |
| [ForgeBase_前後台改造說明.md](ForgeBase_前後台改造說明.md) | 本次改造評估與工作項目（程式碼實查版）|

---

## 版本更新紀錄

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

### v0.19 — SEO Workbench 與非專家操作體驗（2026-03-15）

本次新增一套以「非 SEO 專家也能操作」為目標的 SEO workbench，將既有 metadata、診斷與分析能力整合成任務導向後台體驗。

| 類別 | 變更 |
|------|------|
| **API** | `POST /content/seo-audit/evaluate` — 以產品 / 分類 / 應用場景的當前內容即時評估 SEO 健康度與建議 |
| **API** | `GET /content/seo-audit/health` — 任務導向健康摘要，提供優先修正項與高風險內容清單 |
| **API** | `GET /content/seo-audit/links` — 依分類與應用關聯提供內部連結建議 |
| **API** | `GET /content/seo-audit/revenue` — 將 SEO 內容表現與 RFQ 轉換串接成洞察 |
| **Admin** | 產品 / 分類 / 應用場景表單新增「SEO 助手」面板，可直接分析目前內容並一鍵套用建議標題與摘要 |
| **Admin** | `後台 → AI / SEO → SEO 診斷` 改為任務式儀表板，分為總覽、內鏈建議、轉換洞察三區 |
| **Web** | 新增 `web/src/lib/seo.ts` 共用 metadata helper，統一 canonical、metadataBase 與 hreflang 生成邏輯 |

| 頁面 | 變更 |
|------|------|
| `products/` | 新增「主推 ⭐」欄位，點擊即時切換 `is_featured` |
| `rfqs/[id]/` | Sidebar 新增「銷售跟進」卡片：一鍵記錄首次回覆/報價時間、未成交原因 |
| `ctas/CTAForm` | 新增「目標意圖階段」選擇器（any / cold / warm / hot）|
| `analytics/funnel/` | 全新漏斗儀表板：轉換率卡片 + 意圖階段條形圖 + RFQ 狀態格 |
| `nurture/` | 列表頁: 序列名稱可點擊、「新增序列」按鈕啟用 |
| `nurture/new/` | 全新新增序列頁面 |
| `nurture/[id]/` | 全新序列詳情頁：設定編輯 + 步驟管理（新增/刪除）+ 入列記錄 |
| `segments/` | 「新增 Segment」按鈕啟用、名稱可點擊 |
| `segments/new/` | 全新視覺化규則建構器（支援 intent_stage / intent_score / country / event_count）|
| `segments/[id]/` | 全新詳情頁：設定編輯 + 條件規則展示 + 一鍵評估符合人數 |
| `Sidebar` | 行銷分析區加入「行銷漏斗」連結 |

#### 前台（Web Next.js）

| 元件/頁面 | 變更 |
|-----------|------|
| `web/src/app/page.tsx` | Homepage 新增「主推產品」區塊（`getFeaturedProducts()` 取 `is_featured=true` 的產品，4 欄 Grid）|
| `ProductCTAButtons.tsx` | 依訪客意圖動態調整主要 CTA 按鈕文案：Hot 階段顯示急迫樣式、服務後端 `personalization.cta_label_override` |

#### 部署注意事項

```bash
# 1. 套用 DB migration（新增 3 欄位到 3 張表）
cd api && source .venv/bin/activate
alembic upgrade head
# → 執行 0018_growth_site_fields

# 2. 重新部署後端
systemctl restart forgebase-api

# 3. 重新建置並部署前台與後台
cd /opt/forgebase/app/web && npm run build && ...
cd /opt/forgebase/app/admin && npm run build && ...
```
