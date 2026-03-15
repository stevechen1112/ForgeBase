# ForgeBase

**外銷製造商官網成長系統** — Capture · Intent · Conversion

ForgeBase 是專為外銷製造商設計的 B2B 網站成長平台，整合訪客行為追蹤、意圖評分、詢價捕捉、AI 內容生成與帳戶智能（Account Intelligence），讓業務團隊能在潛在買家主動詢價前就掌握其購買信號。

---

## 核心功能

| 模組 | 說明 |
|------|------|
| **訪客追蹤 & 意圖評分** | 自動記錄頁面瀏覽、產品查看、FAQ 展開、規格下載等行為事件，實時計算 Cold / Warm / Hot / Sales-Ready 買家階段 |
| **RFQ 捕捉** | 結構化詢價表單，含產品需求、預算、時程等欄位，直送管理後台 |
| **Download Gate** | 規格書、技術文件需留資才可下載，自動建立聯絡人 |
| **帳戶智能（Account Intelligence）** | 通過 GeoIP 識別訪客國家，IP-to-Company 反查企業身份 |
| **AI 內容生成** | 基於 PageBrief 工作流，AI 自動起草產品頁、應用頁、FAQ |
| **Dynamic CTA** | 依訪客買家階段顯示不同行動呼籲（詢價 / 下載目錄 / 聯繫業務）|
| **Nurture Email 序列** | 依買家階段觸發自動化培育郵件，整合 Resend |
| **A/B 測試** | 版本對照測試 CTA 與內容效果 |
| **CRM 同步** | 將 RFQ / 聯絡人同步至外部 CRM |
| **SEO 稽核** | 產品頁 SEO 評分、關鍵字建議、結構化資料檢查 |

---

## 專案結構

```
ForgeBase/
├── api/                    # 後端 API (Python 3.10 + FastAPI)
│   ├── app/
│   │   ├── api/v1/         # REST endpoints
│   │   ├── db/migrations/  # Alembic migrations (17 版本)
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
alembic upgrade head           # 套用全部 17 個 DB migrations
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

以示範公司「手工具製造商」為例，注入 7 位模擬買家與 2 筆 RFQ：

```bash
# 先確保 API (8000) 正在執行
cd demo/handtool-company/seed
python3 seed_demo_visitors.py
```

注入成功後，管理後台（:3001）可立即看到 Cold / Warm / Hot / Sales-Ready 分布的訪客列表。

---

## 開發規範

- API 版本前綴：`/api/v1/`
- 所有 API 回應格式：`{"data": ..., "meta": ...}` 或 `{"error": ...}`
- DB migration：`alembic revision --autogenerate -m "描述"` 後 commit
- 環境變數：`.env.example` 保持更新，**絕不 commit 真實 `.env`**
- 所有 AI 生成必須有對應的 PageBrief（Approved 狀態）才能觸發

---

## 文件

| 文件 | 說明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 技術架構與選型決策紀錄 |
| [ForgeBase_產品規格文件.md](ForgeBase_產品規格文件.md) | 完整產品功能規格 |
| [ForgeBase_完整開發計畫.md](ForgeBase_完整開發計畫.md) | 開發里程碑計畫 |
| [ForgeBase_Demo指導文件.md](ForgeBase_Demo指導文件.md) | Demo 流程與話術指引 |
