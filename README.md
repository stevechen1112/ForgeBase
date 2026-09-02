# ForgeBase

**外銷製造業的受管網站與詢價交接系統**
內容準備 · 訪客旅程 · 詢價收件 · 人工接手

ForgeBase 協助傳產外銷團隊經營多語網站，保存第一方訪客脈絡，接收結構化詢價，並把完整資料交給負責業務。產品邊界停在「業務確認接手」；報價、通話、視訊、議價、成交與失單屬於公司既有業務流程或 CRM，不要求業務重複回填，也不由網站推測。

## 產品流程

```text
準備產品與網站內容
  → 發布多語網站
  → 觀察第一方訪客來源、頁面足跡與 AI 客服對話
  → 訪客送出聯絡或 RFQ 詢價
  → 系統保存原始需求並可寄送交易型收件確認
  → 主管分派負責業務
  → 業務確認接手
  → 回到企業既有線下業務流程
```

詢價的系統狀態只有四種：

| 狀態 | 意義 |
|---|---|
| `new` | 網站已收到，尚未分派 |
| `assigned` | 已分派，等待負責業務確認接手 |
| `accepted` | 負責業務已確認接手，ForgeBase 的主要交接任務完成 |
| `archived` | 不再需要出現在承接工作清單，但保留稽核紀錄 |

垃圾詢價與重複詢價使用獨立旗標隔離或合併，不冒充銷售階段，也不直接刪除稽核資料。

## 核心功能

### 網站與產品準備

- 產品、分類、應用、製造能力、FAQ、認證與一般頁面 CMS。
- 英文、繁中、日文、法文、俄文內容版本；草稿、審核、發布與缺漏覆蓋檢查分開。
- SEO、canonical、hreflang、sitemap、JSON-LD 與重導向管理。
- 圖片與 PDF 素材管理，Cloudflare R2 可選。
- 租戶免費網址與經 DNS 驗證的自有網域。

### 訪客與來源

- 第一方 page view、產品瀏覽、CTA、下載與 RFQ 事件。
- 訪客旅程、來源、活動、裝置、國家與內容成效。
- 前台 AI 客服依公開 CMS／文件回答，資料不足時保守回答並導向詢價。
- AI 客服對話、聯絡表單、inbound reply 與真人 handoff 保留在同一工作脈絡。
- 公司識別與聯絡窗口候選必須受權利、法遵、供應商與人工審核 Gate 約束；候選公司不代表已識別自然人。

### 詢價承接

- 結構化 RFQ 保存原始規格、數量、圖面、Incoterm、年需求量、目標價格與認證需求。
- 單一「詢價承接」頁；主管看租戶內全部案件，業務只看分派給自己的案件。
- 收件、收件確認、分派、人工接手、可驗證人工回覆分成不同時間戳，不能互相冒充。
- 依買家時區計算內部接手期限，逾期進入「今日工作」。
- 內部備註、垃圾隔離、重複合併、CSV 匯出與完整事件時間軸。
- 回覆準備 checklist 與範本可協助整理缺少的詢價資料；它不是買家價值評分。

## 明確不包含

ForgeBase 不是 CRM，以下能力已退出產品 runtime、API、前台、資料模型與 Demo 資料：

- 報價、議價、成交、失單、逾期等銷售狀態。
- 成交金額、幣別、成交／失單原因與下一次跟進日期。
- 成交漏斗、成果儀表板、內容到成交歸因。
- 智慧買家／詢價品質分數，以及依分數自動通知或寄信。
- AI 行銷工作助理與通用外部服務連線介面。
- 郵件培育、回訪名單、寄出前確認與其自動排程；業務接手後不要求在 ForgeBase 回填後續動作。

歷史 migration 保留以維持資料庫演進可追溯；它們不代表現行功能。`0102_realign_rfq_to_handoff_scope` 是不可逆的前向退場 migration，正式套用前必須先備份資料庫並用 `api/scripts/export_retired_rfq_sales_data.py` 匯出將刪除的舊銷售欄位。

完整決策與資料處理原則見 [FORGEBASE_PRODUCT_SCOPE_REALIGNMENT_DECISION_2026-09-02.md](FORGEBASE_PRODUCT_SCOPE_REALIGNMENT_DECISION_2026-09-02.md)。文件的新舊適用順序與 production 證據入口，統一由 [FORGEBASE_DOCUMENT_AUTHORITY_INDEX_2026-08-28.md](FORGEBASE_DOCUMENT_AUTHORITY_INDEX_2026-08-28.md) 管理。

## 專案結構

```text
ForgeBase/
├── api/       FastAPI、SQLModel、Alembic、背景工作與 pytest
├── admin/     租戶管理後台與平台營運後台（Next.js）
├── web/       公開多語網站與 AI 客服（Next.js）
├── deploy/    Docker Compose、Caddy、健康檢查與維運腳本
├── demo/      受保護的示範內容與素材
└── .github/   CI、部署與受保護 Demo seed workflow
```

## 技術棧

| 層級 | 技術 |
|---|---|
| API | Python、FastAPI、SQLModel、Alembic、asyncpg |
| 資料庫 | PostgreSQL 16 |
| 前台／後台 | Next.js App Router、React、TypeScript、Tailwind CSS |
| 反向代理 | Caddy |
| 容器 | Docker Compose |
| 檔案 | 本地 volume 或 Cloudflare R2 |
| Email | Resend，受治理開關與 outbox 控制 |
| AI | OpenAI API，可選 Langfuse tracing，內建敏感資料遮罩 |

## 本地開發

需求：Python 3.12+、Node.js 20+、PostgreSQL 16+。

```bash
# API
cd api
cp .env.example .env
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 公開網站
cd web
cp .env.local.example .env.local
npm ci
npm run dev

# 管理後台
cd admin
cp .env.local.example .env.local
npm ci
npm run dev
```

## 驗證

```bash
cd api
python -m pytest -q
python scripts/verify_schema_contract.py
alembic heads

cd ../admin
npm run type-check
npm run lint
npm run build

cd ../web
npm run type-check
npm run lint
npm run build
```

資料庫 migration 必須維持單一 head。正式發布前還要執行退場殘留掃描、備份／還原演練、API smoke test，以及用真實瀏覽器逐頁檢查桌面與窄版介面。

## Demo 資料

受保護的展示資料只允許寫入名稱明確包含 `Demo` 的租戶，使用固定 UUID idempotent 更新，不寄信、不建立外送工作，也不產生成交或營收資料。

```bash
cd api
python scripts/seed_demo_showcase.py \
  --user-email owner@your-protected-demo-tenant.test \
  --apply
```

展示資料包含完整產品瀏覽足跡、買家聯絡資料、詢價原文、收件確認、分派、待接手、已接手、封存、內部備註、內容草稿、客服對話與通知，足以進行正式部署狀態的 Demo 彩排。腳本會拒絕一般正式租戶。

## 生產部署

生產拓撲由 `docker-compose.prod.yml` 管理：`db`、一次性 `migrate`、`api`、`admin`、`web`、`caddy`。完整環境變數、TLS、備份、復原與健康檢查說明見 [deploy/README.md](deploy/README.md)。

套用 `0102` 的必要順序：

1. 進入維護視窗並確認沒有 RFQ 寫入工作正在執行。
2. 建立 PostgreSQL 可還原備份並完成校驗。
3. 在受保護路徑執行 `export_retired_rfq_sales_data.py`；匯出檔不得進 Git、CI artifact 或公開日誌。
4. 先在備份還原出的隔離資料庫執行 `alembic upgrade head`、schema contract 與 API smoke test。
5. 建置並部署同一 commit 的 API 與 Admin，避免新舊 schema 混用。
6. 正式 migration 後檢查 readiness、背景工作、RFQ 建立／分派／接手與 tenant isolation。
7. 用租戶管理員與業務兩種角色進行唯讀頁面巡檢，再依測試資料完成受控寫入 smoke test。

若 migration 失敗，不做 in-place downgrade；停止服務並從已驗證備份還原。

## 正式租戶上線前檢查

- 租戶、管理員、業務角色與資料隔離已驗證。
- 品牌、產品、頁面、五語內容狀態與素材均非 Demo 殘留。
- 自有網域、TLS、canonical、sitemap 與表單允許 hostname 正確。
- RFQ challenge、Turnstile、速率限制、通知與接手期限設定已確認。
- 收件確認信預設可關閉；若開啟，寄件網域、內容與收件範圍已核准。
- 備份、還原、readiness、migration head、API、Admin 與公開網站 smoke test 通過。

## 開發原則

- 所有租戶資料查詢必須強制 tenant scope；業務 RFQ 查詢還要強制 assignee scope。
- 公開表單、寄信、發布與刪除都要有明確權限、冪等或稽核紀錄。
- AI 回答公司事實必須接地於已發布內容；缺資料時保守回答，不編造價格、交期、認證或能力。
- 自動收件確認不是人工回覆；分派不是接手；接手不是成交。
- `.env`、正式資料匯出、備份與憑證永不提交版本庫。
