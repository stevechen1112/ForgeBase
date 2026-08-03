# ForgeBase 技術棧與架構決策紀錄

## 確認日期：2026-04-14（2026-08-03 補充 Leads Growth OS）

## 技術選型

| 層級 | 技術 | 版本 / 說明 |
|------|------|-------------|
| 後端 API | Python + FastAPI | Python 3.13+ / FastAPI |
| ORM + migration | SQLModel + Alembic | SQLModel + Alembic |
| 資料庫 | PostgreSQL | 17 |
| 前台 Web | Next.js App Router + React | Next.js 15.5.15 / React 19 |
| Admin 後台 | Next.js App Router + React | Next.js 15.5.15 / React 19 |
| 共用型別 | shared package | TypeScript shared models |
| 檔案 / 資產 | Cloudflare R2 + repo demo assets | S3-compatible |
| AI | Gemini OpenAI-compatible API | model: gemini-3-flash-preview（亦可切換 OpenAI）|
| Email / ESP | Resend / SendGrid / Mailchimp | 依 tenant 與環境設定啟用 |
| 反向代理 | Nginx | web / admin / api 統一入口 |
| 容器化 | Docker + Docker Compose | 本地開發與部署輔助 |

## 系統拓樸

```
訪客 / 管理者
  └── Nginx / CDN / Host-based routing
    ├── Web（Next.js standalone）
    ├── Admin（Next.js standalone）
    └── API（FastAPI）
      ├── PostgreSQL 17
      ├── Cloudflare R2
      └── OpenAI / ESP / 外部整合
```

## 核心架構原則

1. Web、Admin、API 分離部署，但共用同一套多租戶資料模型。
2. 所有內容模型採 tenant-scoped 設計，slug / locale 唯一性以 tenant 邊界為準。
3. Web 品牌資料在 request-time 由 SiteProfile 解析，不再依賴單純的 build-time env branding。
4. Admin 對 API 的呼叫統一由 `admin/src/lib/api/client.ts` 注入 `X-Tenant-ID`。
5. Public side 以 Host / Origin / `X-Tenant-Host` 解析租戶，必要時可接受 `X-Tenant-ID`。

## 多租戶規則

1. 後端 `resolve_tenant_id(...)` 先讀 `X-Tenant-ID`，其次回退到 host / origin / referer / forwarded host。
2. Product、Application、FAQ、Comparison、Capability、Certification、CTA、Page、Category 等內容全部帶 `tenant_id`。
3. 公開內容 API、關聯 API、chat session、RFQ 與 admin CRUD 都必須做 tenant 邊界驗證。
4. 所有關鍵唯一鍵以 `(slug, locale, tenant_id)` 或 `(business_key, tenant_id)` 方式定義。

## Build 與部署原則

1. Web build 以 `FORGEBASE_STRICT_BUILD_API=1` fail-fast；若 build 時 API 不可用，直接失敗，不允許靜默 fallback 產生不完整靜態輸出。
2. Web 與 Admin 的 `postbuild` 均使用 `prepare-next-standalone.mjs`，避免 `.sh` 腳本造成 Windows 失敗。
3. Standalone 產物透過 symlink 連接 `.next/static` 與 `public`，供 Nginx / Node runtime 直接服務。
4. Smoke test 使用 mock site-profile server 驗證多租戶品牌、canonical、robots、sitemap、favicon 隔離。

## AI 與內容生成規則

1. AI 內容生成必須綁定 PageBrief，且寫入 tenant-aware generation log。
2. AI context 查詢不得跨 tenant 讀取 Product / Application / FAQ / Category。
3. Chat、handoff、RFQ、tracking 必須共享同一 tenant 與 visitor/session 邏輯。

## 安全與營運規範

1. JWT access token / refresh token 驗證由 API 負責，Admin client 具備 refresh retry 機制。
2. 所有 secrets 只放在 `.env` 或部署平台 secret store，不得進 repo。
3. Production 預設關閉不必要 debug / docs 入口。
4. 新增功能時，必須同時回答三個問題：tenant boundary 在哪裡、runtime branding 從哪裡來、build-time 是否允許 fallback。

## Leads Growth OS 補充（2026-08-03）

1. **多產品邊界**：ForgeBase、ContentFlow、ExposureFlow 是獨立產品，各自發展租戶；產品間一律走 API 契約（`CF_FB_PUBLISH_CONTRACT.md`），不共用資料庫。
2. **外部寫入安全**：外部系統（ContentFlow）發佈內容進 FB 時，`Page.body` 一律經白名單 HTML 消毒；`POST /content/pages` 支援 `Idempotency-Key` 防止重複建立（含併發競態處理）。
3. **快取一致性**：內容發布/更新/下架後，API 非同步呼叫前台 `POST /api/revalidate` 觸發 ISR revalidate；secret 由環境變數管理，不得硬編碼。
4. **營運設定租戶化**：自動回覆、SLA 時區、通知門檻皆存於 `SiteProfile.ops_config_json`，非全域 env。
5. **成果可衡量**：RFQ 狀態機延伸至成交（`won`/`lost` 必填原因），漏斗、歸因、任務佇列 API 讓成效可追蹤；成交 facet lift 僅 observational，不自動改權重。
6. **部署細節**：環境變數、遷移步驟、回填腳本與上線驗證清單統一收錄於 `FORGEBASE_DEPLOY_SETUP.md`。
