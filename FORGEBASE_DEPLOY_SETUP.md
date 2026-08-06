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
| `OPENAI_API_KEY` | OpenAI API key（本系統僅使用 OpenAI LLM） |
| `AI_MODEL_NAME` | 模型名（預設 `gpt-5.6-luna`） |

### 1.3 通知（T5 即時通知）

| 變數 | 說明 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot（@BotFather 取得） |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook HMAC 驗證密鑰；**設了 BOT_TOKEN 就必須設**，否則啟動時 `RuntimeError` |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API 通道金鑰（全域環境變數；未設則 LINE 通道自動略過，不影響其他通道） |

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

## 3. Secrets 狀態（重要）

`.gitignore` 涵蓋 `.env.*`。**2026-08-03：首次 push 前已用 `git filter-repo` 抹除整段歷史中的敏感檔與 README 內的 production DB 密碼**，再推送至 [stevechen1112/ForgeBase](https://github.com/stevechen1112/ForgeBase)（Public）。因此 GitHub 上的歷史不含任何真實金鑰。

⚠️ 往後任何 secret 誤 commit，一律視為已外洩並立即輪替。King-A 相關本機 env（例如曾存在的 `api/.env.kinga`）已自工作區移除，不應再使用。

---

## 4. 每租戶營運設定（SiteProfile.ops_config_json）

T6（自動專業回覆）與 T7（時區感知 SLA）皆由每租戶的 `SiteProfile.ops_config_json` 驅動。
**實際生效的鍵為扁平結構**（以 `app/services/rfq_auto_reply.py`、`app/services/sla.py` 為準）：

```json
{
  "auto_reply_enabled": true,
  "auto_reply_signature": "Export Sales Team",
  "auto_reply_from_name": "NorthForge Sales",
  "sla_response_hours": 4
}
```

| 鍵 | 說明 |
|---|---|
| `auto_reply_enabled` | 收到 RFQ 後是否自動寄出專業確認信（T6，預設關） |
| `auto_reply_signature` | 確認信署名（預設 `Sales Team`） |
| `auto_reply_from_name` | 寄件者顯示名稱（預設沿用系統設定） |
| `sla_response_hours` | 首次回應 SLA 目標（營業小時，T7；逾時標記 `sla_breached` 並進「今日必處理」） |

**設定方式（2026-08-03 起有 UI）**：

- **Admin UI**：設定 → 網站設定頁底部「營運設定（RFQ 自動回覆 / SLA）」卡片。
- **API（admin token）**：`GET / PUT /api/v1/site-profile/ops-config`（部分更新、顯式 `null` 清除鍵、保留未知鍵）。
- 公開端點 `GET /api/v1/site-profile` **不會**回傳 ops_config，避免設定外洩。

注意事項（與直覺不同之處，以代碼為準）：

- **LINE 金鑰不在 ops_config**：為全域環境變數 `LINE_CHANNEL_ACCESS_TOKEN`（`app/services/channels/line.py`）。
- **SLA 時區不由租戶設定**：SLA 依**買家時區**計時，由 `buyer_timezone` 或表單 `country` 推斷（`app/services/sla.py`）。
- **高品質即時推播門檻固定為 70 分**：`app/services/copilot/monitor.py` 的 `HIGH_QUALITY_THRESHOLD`，低分 RFQ 併入每日摘要。

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
