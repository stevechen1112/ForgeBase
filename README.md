# ForgeBase

外銷製造商官網成長系統 — Capture · Intent · Conversion

## 專案結構

```
ForgeBase/
├── api/          # 後端 API (Python 3.12 + FastAPI)
├── web/          # 前台網站 (Next.js 15，部署 Vercel)
├── admin/        # 管理後台 (Next.js 15，部署 Linode)
├── shared/       # 共用型別與常數
└── .github/      # CI/CD workflows
```

## 技術棧

| 層級 | 技術 |
|------|------|
| 後端 API | Python 3.12 + FastAPI + SQLModel + Alembic |
| 資料庫 | PostgreSQL 16 |
| 前台 | Next.js 15 (App Router) → Vercel |
| Admin | Next.js 15 (App Router) → Linode |
| 檔案儲存 | Cloudflare R2 (S3-compatible) |
| AI | OpenAI API (gpt-5.4) |
| Email | Resend |
| GeoIP | Cloudflare CF-IPCountry header |
| Hosting | Linode (API + DB + Admin) |
| CI/CD | GitHub Actions |

## 快速開始

### 環境需求

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose（本地開發用）
- PostgreSQL 16（或透過 Docker）

### 本地開發啟動

```bash
# 1. 啟動資料庫
docker compose up -d db

# 2. 後端 API
cd api
cp .env.example .env   # 填入環境變數
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. 前台
cd web
cp .env.local.example .env.local
npm install
npm run dev  # http://localhost:3000

# 4. 管理後台
cd admin
cp .env.local.example .env.local
npm install
npm run dev  # http://localhost:3001
```

### 健康檢查

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

## 開發規範

- API 版本前綴：`/api/v1/`
- 所有 API 回應格式：`{"data": ..., "meta": ...}` 或 `{"error": ...}`
- DB migration：`alembic revision --autogenerate -m "描述"` 後 commit
- 環境變數：`.env.example` 保持更新，**絕不 commit 真實 `.env`**
