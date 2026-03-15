# ForgeBase 技術棧與架構決策紀錄

## 確認日期：2026-03-14

## 技術選型

| 層級 | 技術 | 版本 |
|------|------|------|
| 後端 API | Python + FastAPI | 3.12 / 0.115 |
| ORM + migration | SQLModel + Alembic | 0.0.21 / 1.13 |
| 資料庫 | PostgreSQL | 16 |
| 前台 | Next.js (App Router) | 15.2 |
| Admin 後台 | Next.js (App Router) | 15.2 |
| 檔案儲存 | Cloudflare R2 | S3-compatible |
| AI | OpenAI API | model: gpt-5.4 |
| Email | Resend | — |
| GeoIP | Cloudflare CF-IPCountry header | 免費，需 DNS 轉到 Cloudflare |
| 前台 Hosting | Vercel | — |
| API/DB/Admin Hosting | Linode (Akamai Cloud) | — |
| CI/CD | GitHub Actions | — |
| 容器化 | Docker + Docker Compose | 本地開發用 |

## 部署架構

```
訪客瀏覽器
  └── Cloudflare CDN（提供 CF-IPCountry header）
        ├── 前台網站 → Vercel（Next.js SSR/SSG）
        └── /api/v1/* → Linode（FastAPI）
                          └── PostgreSQL（同 Linode）
                          └── Cloudflare R2（圖片/PDF）
                          └── Resend（email）
Admin 後台 → Linode（Next.js standalone）
```

## 環境設定原則

1. 所有機密（API keys、DB 密碼）只存在 `.env`，**絕不 commit**
2. 每個子專案都有 `.env.example`，說明必填項目
3. `APP_ENV=production` 時自動關閉 `/docs` 和 debug 輸出
4. DB URL 格式：`postgresql+asyncpg://user:pass@host:5432/dbname`（asyncpg 驅動）

## AI 使用原則

- Model：`gpt-5.4`（由 `AI_MODEL_NAME` 環境變數管理，可切換）
- 所有 AI 生成必須有對應的 PageBrief（Approved 狀態）才能觸發
- 每次生成結果完整記錄（model 版本、輸入 IDs、完整輸出）

## 安全規範

- JWT 認證：access token 60 分鐘，refresh token 30 天
- CORS 白名單：僅允許 `ALLOWED_ORIGINS` 設定的 origin
- 密碼雜湊：bcrypt
- Webhook 簽章：HMAC-SHA256
- Production 關閉 `/docs`
