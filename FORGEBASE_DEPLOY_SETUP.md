# ForgeBase 部署與設定指南

> 本文件說明把 ForgeBase API（FastAPI）＋ Admin（Next.js）＋ Web 前台（Next.js）
> 部署到生產環境所需的環境變數、遷移步驟、以及各功能的設定方式。
> 適用版本：Leads Growth OS Phase 1–5（2026-08-03 之後）。

---

## 1. 環境變數一覽

### 1.1 必填

| 變數 | 說明 | 範例 |
|---|---|---|
| `DATABASE_URL` | PostgreSQL 連線字串（asyncpg） | `postgresql+asyncpg://user:pass@host:5432/forgebase` |
| `SECRET_KEY` | JWT 簽章密鑰（≥32 字元隨機字串） | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

### 1.2 AI / LLM

| 變數 | 說明 |
|---|---|
| `AI_PROVIDER` | `openai` 或 `gemini` |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` | 對應供應商的 API key |
| `GEMINI_BASE_URL` | Gemini OpenAI 相容端點 |
| `AI_MODEL_NAME` | 模型名（預設 `gemini-3-flash-preview`） |

### 1.3 通知（T5 即時通知）

| 變數 | 說明 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot（@BotFather 取得） |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook HMAC 驗證密鑰；**設了 BOT_TOKEN 就必須設**，否則啟動時 `RuntimeError` |
| LINE 通道 | 由每租戶 `SiteProfile.ops_config_json` 的 `notify.line.access_token` 提供（見 §4） |

### 1.4 Web On-Demand Revalidation（Phase 2a）

FB 內容發布／更新／下架時，非同步觸發前台 ISR revalidate。

| 服務 | 變數 | 說明 |
|---|---|---|
| **API** | `WEB_REVALIDATE_URL` | 前台 revalidate route，例：`https://www.client.com/api/revalidate` |
| **API** | `WEB_REVALIDATE_SECRET` | 與前台 `REVALIDATE_SECRET` **必須相同** |
| **Web 前台** | `REVALIDATE_SECRET` | 驗證 `x-revalidate-secret` header |

> 未設定 `WEB_REVALIDATE_URL` 時，revalidate 呼叫會靜默略過（不影響發布流程）。

### 1.5 Service Account（ContentFlow → ForgeBase，Phase 2a）

```
SERVICE_ACCOUNT_TOKENS=<token>:<user_id>,<token2>:<user_id2>
```
1. 在 FB 建立 `role=marketing_manager` 且有 `tenant_id` 的使用者。
2. `python -c "import secrets; print(secrets.token_urlsafe(32))"` 產生 token。
3. ContentFlow 以 `X-API-Key: <token>` 帶入。

### 1.6 AgentOS（RFQ 工作流觸發）

| 變數 | 說明 |
|---|---|
| `AGENTOSS_URL` | AgentOS 服務位址；**未設定時觸發功能靜默停用**（對應測試失敗屬預期） |
| `AGENTOSS_API_KEY` | 對應金鑰 |

### 1.7 其他（依功能選填）

`R2_*`（素材上傳）、`RESEND_API_KEY`（信件）、`GSC_*`（Search Console）、
`ESP_*`/`SENDGRID_*`/`MAILCHIMP_*`（名單）、`ENCRYPTION_MASTER_KEY`（整合憑證加密）、`PAYPAL_*`。

---

## 2. 部署步驟

```bash
# 1. 安裝依賴
cd api && pip install -r requirements.txt

# 2. 套用資料庫遷移（目前 head = 0051）
alembic upgrade head

# 3. （既有資料才需要）回填 Intent Score 2.0 facets
python scripts/backfill_visitor_facets.py --all
# 或單一租戶試算：
python scripts/backfill_visitor_facets.py --tenant <uuid> --dry-run

# 4. 啟動
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> **SLA 掃描排程**：`app.main` 啟動時自動掛上 APScheduler（T7），無需額外 worker。

---

## 3. Secrets 輪替狀態（重要）

`.gitignore` 已涵蓋 `.env.*`，且以下檔案已從版本控制移除：
- `api/.env.kinga`
- `admin/.env.production`

**截至 2026-08-03，含洩漏的 commit（`6e9fb96`、`91eb14f` 等）尚未 push 到遠端**
（`git branch -r --contains` 無結果），因此：

- ✅ 若尚未 push：**無需公開輪替**，直接 amend／rebase 或在 push 前確認檔案已移除即可。
- ⚠️ 若之後曾 push 過這些檔案的任何版本：**必須輪替**其中的所有金鑰
  （Gemini key、DB 密碼、R2、Resend 等），因 GitHub 會永久保留歷史快照。

---

## 4. 每租戶營運設定（SiteProfile.ops_config_json）

T6（自動專業回覆）與 T7（時區感知 SLA）皆由每租戶的 `SiteProfile.ops_config_json` 驅動：

```json
{
  "auto_reply": { "enabled": true, "min_quality_score": 40 },
  "sla":        { "business_hours": 4, "timezone": "Asia/Taipei" },
  "notify":     { "line": { "access_token": "..." }, "min_quality_score": 70 }
}
```

| 鍵 | 說明 |
|---|---|
| `auto_reply.enabled` | 收到 RFQ 後是否自動寄出專業回覆（T6） |
| `auto_reply.min_quality_score` | 品質分低於此值不自動回覆（品質閘門） |
| `sla.business_hours` | 首次回應 SLA（營業小時，T7） |
| `sla.timezone` | 計算 SLA 的時區（IANA 名稱） |
| `notify.min_quality_score` | 高於此分才即時推播（T5） |

---

## 5. 上線後驗證（手動）

- [ ] `POST /content/pages` 帶 `Idempotency-Key`，重送應回相同 page id（Phase 2a）。
- [ ] 發布一個頁面後 60 秒內前台快取應更新（revalidate 生效）。
- [ ] `GET /content/pages/{id}/trust-check` 回傳信任內容檢核清單。
- [ ] 建立高品質 RFQ → 確認 Telegram/LINE 推播與自動回覆信件寄出。
- [ ] `GET /tracking/funnel`、`/tracking/outcomes`、`/ops/task-queue` 有資料。
- [ ] Admin 的 `/dashboard/outcomes`、`/dashboard/tasks` 正常顯示。

---

## 6. 既有測試注意事項

| 測試 | 狀態 | 原因 |
|---|---|---|
| `tests/test_forgebase_e2e.py` | 預期失敗 | 依賴外部 `agent_platform` 套件（不在本 repo，亦非 pip 套件） |
| `tests/test_forgebase_binding_approval.py` | 預期失敗 | 同上 |
| 其他 DB 測試 | 需 `DATABASE_URL` | 未設定時自動 skip |

這兩個測試屬於 AgentOS 整合層，需在有 `agent_platform` 套件的環境中執行；與本計畫
（Leads Growth OS Phase 1–5）無關，不影響交付。
