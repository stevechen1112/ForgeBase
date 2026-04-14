# ForgeBase AI 行銷專員（AI Marketing Copilot）功能規劃書

> 日期：2026-04-14  
> 狀態：規劃階段  
> 目標：將 ForgeBase 從「被動式行銷工具」升級為「主動式 AI 行銷助手平台」

---

## 一、為什麼要做這個？

### 現狀問題

ForgeBase 目前的核心能力是：多租戶網站 + 產品展示 + RFQ + 後台管理。  
雖然已經有 visitor intent scoring、AI chat advisor、AI RFQ 分析等模組，  
但這些 AI 能力都是**被動的**——使用者必須自己：

1. 登入後台看報表
2. 理解 intent score、visitor stage 等概念
3. 手動決定下一步動作（跟進誰、回覆什麼、優化哪個頁面）

**結果**：大部分中小企業客戶根本不會主動看後台，AI 能力形同虛設。

### 改造方向

加入一個「AI 行銷專員」角色，讓系統：

- **主動監測** → 發現值得關注的事件
- **主動通知** → 推送到使用者習慣的通訊管道（Telegram / LINE / Email）
- **主動建議** → 告訴使用者該做什麼、為什麼
- **可互動** → 使用者可以直接對話追問、下指令

這樣 ForgeBase 才是真正的「AI 驅動行銷平台」，而不只是「有 AI 功能的行銷工具」。

---

## 二、系統現有基礎（可直接複用）

| 模組 | 現有能力 | AI 專員如何利用 |
|------|---------|---------------|
| **Intent Scoring** | 15+ 事件類型計分、stage 升降、ML blending | 當 visitor 升級 hot/sales_ready → 觸發通知 |
| **Score Decay** | 7/14/30/60 天衰減 | 偵測「即將流失」的客戶 → 提醒跟進 |
| **AI Chat Advisor** | 對話狀態機、商業 slot 追蹤、handoff | 當 chat 觸發 handoff → 即時通知業務 |
| **AI RFQ Analysis** | 需求提取、產品配對、回覆草稿 | 新 RFQ 進來 → 分析 + 草稿 → 推送給負責人 |
| **AI Content Optimizer** | 頁面表現分析 + 改善建議 | 週報：哪些頁面需要優化 |
| **AI CTA Recommender** | 行為 profile → CTA 推薦 | 發現高潛力 visitor → 推薦最佳觸及方式 |
| **Webhook System** | 5 種 event、HMAC 簽名、重試 | AI 專員的事件來源之一 |
| **Notification (SMTP)** | RFQ 通知、hot visitor 警報 | 現有 email 通知可直接擴充 |
| **Dynamic CTA** | Stage → 行動優先級 | AI 專員建議的依據 |
| **Segmentation** | AudienceTag + Segment 條件分群 | AI 專員可以按分群推送洞察 |

**結論**：不需要從零開始。核心分析引擎、資料模型、排程架構都已到位，主要要做的是「大腦」（決策引擎）和「嘴巴」（通知 + 對話通道）。

---

## 三、功能架構

```
┌─────────────────────────────────────────────────────┐
│                  AI Marketing Copilot                │
├──────────┬──────────┬──────────┬────────────────────┤
│  監測層   │  決策層   │  對話層   │     通知層          │
│ Monitor  │ Decision │ Dialog   │   Notification     │
├──────────┼──────────┼──────────┼────────────────────┤
│ DB 事件   │ 規則引擎  │ LLM 對話  │   Telegram Bot    │
│ Webhook  │ AI 分析   │ 指令解析  │   LINE OA Msg API │
│ 排程掃描  │ 優先排序  │ 上下文管理│   Email (Resend)  │
│ 閾值偵測  │ 摘要生成  │ 快捷回覆  │   站內通知中心     │
└──────────┴──────────┴──────────┴────────────────────┘
         ↑                              ↓
   現有 ForgeBase 資料層          使用者（老闆 / 業務）
```

---

## 四、核心場景設計（Phase 1 — MVP）

### 場景 1：新 RFQ 即時通知 + AI 摘要

```
觸發：rfq_request 新增（INSERT trigger 或 webhook）
動作：
  1. 呼叫現有 ai_rfq.analyze_rfq() 提取需求摘要
  2. 呼叫現有 ai_rfq.generate_draft_reply() 產生回覆草稿
  3. 組合訊息推送到 Telegram / LINE：
     ───────────────────────
     🔔 新 RFQ 通知
     編號：RFQ-20260414-003
     公司：ABC Industrial Co.
     產品：8" Adjustable Wrench × 5000pcs
     緊急度：🔴 高（intent score 72）
     
     AI 摘要：客戶需要 OEM 自有品牌包裝，
     交期要求 45 天內，預算中等偏上。
     
     AI 建議回覆：已產生草稿 → [查看後台]
     ───────────────────────
  4. 使用者可直接回覆 Telegram：
     → "幫我回覆這封" → AI 發送草稿 email
     → "這個客戶之前有來過嗎？" → 查 visitor history
     → "標記為急件" → 更新 RFQ priority
```

### 場景 2：高意圖訪客警報

```
觸發：intent_score 升級至 hot 或 sales_ready
動作：
  1. 查詢 visitor 完整行為軌跡（瀏覽頁面、下載、chat 記錄）
  2. 呼叫現有 ai_recommend.recommend_cta_for_visitor() 
  3. 推送：
     ───────────────────────
     🔥 高意圖訪客偵測
     IP 來源：德國 / Bosch Group（推測）
     行為：瀏覽 5 個產品頁 → 下載 spec → 開始 chat
     意圖分數：67 → sales_ready
     
     AI 建議：此訪客已進入銷售就緒階段，
     建議立即觸發 live chat 或發送個人化 email。
     推薦 CTA：urgent RFQ 表單
     ───────────────────────
```

### 場景 3：每日營運摘要

```
觸發：每日排程（cron 08:00 local time）
動作：
  1. 查詢過去 24h 數據
  2. AI 生成自然語言摘要
  3. 推送：
     ───────────────────────
     📊 每日營運摘要 — 2026/04/14
     
     訪客：47 人（↑12% vs 昨日）
     新 RFQ：3 筆（2 筆高優先 ⚠️）
     待回覆 RFQ：1 筆超過 24h ⚠️
     熱門產品：Adjustable Wrench（被查看 23 次）
     
     ⚡ AI 建議：
     1. RFQ-003 超過 24h 未回覆，建議立即處理
     2. 德國 IP 訪客連續 3 天瀏覽，建議主動觸及
     3. "Pipe Wrench" 頁面跳出率偏高，建議優化內容
     ───────────────────────
```

### 場景 4：流失預警

```
觸發：score_decay 執行後偵測到 stage 降級
動作：
  1. 篩出從 hot → warm 或 warm → cold 的 visitor
  2. 查詢其 contact 資訊（若有）
  3. 推送：
     ───────────────────────
     ⚠️ 客戶流失風險
     ABC Co. (john@abc.com) 已 14 天未活動
     原 stage：hot → 現 stage：warm
     
     AI 建議：發送 re-engagement email，
     內容聚焦其上次瀏覽的 "Socket Set" 產品線。
     
     → "幫我發" → AI 觸發 nurture email
     ───────────────────────
```

---

## 五、對話式互動能力（Phase 2）

使用者可以主動在 Telegram / LINE 跟 AI 專員對話：

| 使用者問 | AI 做什麼 |
|---------|----------|
| 「今天有新詢價嗎？」 | 查 rfq_requests WHERE created_at = today |
| 「告訴我 ABC 公司的狀況」 | 查 contacts + visitors + rfq history |
| 「幫我回覆 RFQ-003」 | 呼叫 ai_rfq.generate_draft_reply() → 確認後發送 |
| 「哪個產品最多人看？」 | 查 tracking_events GROUP BY product |
| 「這週轉換率怎樣？」 | 算 RFQ / unique visitors |
| 「把這個客戶標為 VIP」 | 更新 audience_tag |
| 「網站有什麼問題嗎？」 | 呼叫 content_optimizer 分析 |
| 「幫我優化 Wrench 頁面的 SEO」 | 呼叫 ai_engine 生成建議 |

### 技術實現

```python
# 核心：Function Calling / Tool Use 架構
# AI 專員 = LLM + 一組 ForgeBase API tools

COPILOT_TOOLS = [
    {"name": "query_rfqs",        "fn": query_rfqs_summary},
    {"name": "query_visitors",    "fn": query_visitor_detail},
    {"name": "query_products",    "fn": query_product_stats},
    {"name": "query_daily_stats", "fn": query_daily_overview},
    {"name": "send_email",        "fn": trigger_email_via_esp},
    {"name": "update_rfq",        "fn": update_rfq_status},
    {"name": "update_tag",        "fn": update_visitor_tag},
    {"name": "generate_content",  "fn": call_ai_engine},
    {"name": "analyze_rfq",       "fn": call_ai_rfq_analysis},
]
```

---

## 六、通知通道整合

### Telegram Bot（推薦 Phase 1 首選）

| 項目 | 說明 |
|------|------|
| 成本 | 免費 |
| 開發難度 | 低（Bot API + webhook） |
| 即時性 | 即時推送 |
| 互動能力 | 支援（sendMessage + 接收 update） |
| 圖片/按鈕 | 支援 Inline Keyboard |
| 適合 | 開發者、技術型老闆 |

```python
# Telegram Bot 基本架構
# POST https://api.telegram.org/bot{TOKEN}/sendMessage
# Webhook: 設定 setWebhook → ForgeBase API 接收使用者回覆

class TelegramChannel:
    async def send(self, chat_id: str, message: str, buttons: list = None):
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        await httpx.post(f"{BOT_URL}/sendMessage", json=payload)
    
    async def handle_incoming(self, update: dict):
        text = update["message"]["text"]
        chat_id = update["message"]["chat"]["id"]
        # → 送進 AI Copilot 對話引擎
        response = await copilot_engine.process(chat_id, text)
        await self.send(chat_id, response)
```

### LINE Official Account Messaging API（Phase 2）

| 項目 | 說明 |
|------|------|
| 成本 | 免費額度 500 則/月，超過 ¥5,000/月起 |
| 開發難度 | 中（需 Channel Access Token + Webhook） |
| 即時性 | 即時推送（push message） |
| 互動能力 | 支援（reply + push + flex message） |
| 適合 | 台灣客戶、傳統製造業老闆 |

```python
# LINE Messaging API 基本架構
# POST https://api.line.me/v2/bot/message/push
# Webhook: LINE Platform → ForgeBase API

class LineChannel:
    async def send(self, user_id: str, message: str):
        await httpx.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {LINE_CHANNEL_TOKEN}"},
            json={"to": user_id, "messages": [{"type": "text", "text": message}]}
        )
```

### Email（已有）

現有 `email_service.py` 已支援 Resend / SendGrid。  
AI 專員可以直接用現有通道發送摘要報告。

### 站內通知中心（Phase 2）

Admin 後台增加通知 icon + 下拉面板，存放所有歷史通知。

---

## 七、資料模型新增

```sql
-- 通知偏好（每個 user 設定接收管道和頻率）
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    channel TEXT NOT NULL,           -- 'telegram' | 'line' | 'email' | 'in_app'
    channel_config JSONB NOT NULL,   -- {"chat_id": "123456"} or {"line_user_id": "U..."}
    enabled BOOLEAN DEFAULT true,
    -- 通知類型開關
    notify_new_rfq BOOLEAN DEFAULT true,
    notify_hot_visitor BOOLEAN DEFAULT true,
    notify_daily_summary BOOLEAN DEFAULT true,
    notify_churn_risk BOOLEAN DEFAULT true,
    notify_content_suggestion BOOLEAN DEFAULT false,
    -- 頻率控制
    quiet_hours_start TIME,          -- 例如 22:00
    quiet_hours_end TIME,            -- 例如 08:00
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- AI 專員對話歷史（Telegram / LINE 的對話記錄）
CREATE TABLE copilot_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    channel TEXT NOT NULL,
    channel_user_id TEXT NOT NULL,    -- telegram chat_id / line user_id
    role TEXT NOT NULL,               -- 'user' | 'assistant'
    content TEXT NOT NULL,
    tool_calls JSONB,                 -- function calling 記錄
    created_at TIMESTAMP DEFAULT now()
);

-- 通知發送記錄（審計 + 防重複）
CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    channel TEXT NOT NULL,
    event_type TEXT NOT NULL,          -- 'new_rfq' | 'hot_visitor' | 'daily_summary' | ...
    event_ref_id UUID,                 -- 關聯的 rfq_id / visitor_id
    message_preview TEXT,
    status TEXT DEFAULT 'sent',        -- 'sent' | 'delivered' | 'failed'
    sent_at TIMESTAMP DEFAULT now(),
    error_detail TEXT
);
```

---

## 八、後端新增模組

```
api/app/
├── services/
│   ├── copilot/
│   │   ├── __init__.py
│   │   ├── engine.py           # AI 對話引擎（LLM + tool use）
│   │   ├── tools.py            # 可呼叫的 ForgeBase tools 定義
│   │   ├── monitor.py          # 事件監測 + 觸發判斷
│   │   ├── digest.py           # 每日/每週摘要生成
│   │   └── formatter.py        # 訊息格式化（Telegram / LINE / Email）
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── base.py             # Channel 抽象介面
│   │   ├── telegram.py         # Telegram Bot 實作
│   │   ├── line.py             # LINE Messaging API 實作
│   │   ├── email_channel.py    # Email 通道（複用 email_service）
│   │   └── in_app.py           # 站內通知
│   └── notification_router.py  # 統一發送路由（偏好查詢 → 多通道分發）
├── api/v1/endpoints/
│   ├── copilot.py              # 管理端 API（偏好設定、歷史查詢）
│   ├── webhook_telegram.py     # Telegram Bot webhook 接收
│   └── webhook_line.py         # LINE webhook 接收
├── models/
│   ├── notification_preference.py
│   ├── copilot_conversation.py
│   └── notification_log.py
```

---

## 九、前端新增（Admin 後台）

```
admin/src/app/(dashboard)/notifications/
├── page.tsx                     # 通知中心（歷史記錄）
└── settings/
    └── page.tsx                 # 通知偏好設定
                                  - Telegram 綁定（掃 QR / 輸入驗證碼）
                                  - LINE 綁定（OAuth 授權）
                                  - 各類通知開關
                                  - 靜音時段
```

Sidebar 新增「🔔 通知」入口，含未讀 badge。

---

## 十、分階段實施計畫

### Phase 1 — 被動通知 + Telegram（最小可行版）

**目標**：讓使用者不用開後台，就能收到最重要的通知  
**預估工時**：5-7 天

| 步驟 | 內容 | 依賴 |
|------|------|------|
| 1 | DB migration：3 張新表 | — |
| 2 | `notification_router.py`：統一發送路由 | 表結構 |
| 3 | `channels/telegram.py`：Telegram Bot 推送 | Bot Token |
| 4 | `copilot/monitor.py`：事件監聽掛鉤 | router |
| 5 | 新 RFQ 通知（含 AI 摘要） | monitor + ai_rfq |
| 6 | Hot visitor 警報 | monitor + intent_scoring |
| 7 | 每日摘要排程 | APScheduler + digest |
| 8 | Admin 通知設定頁（Telegram 綁定） | frontend |
| 9 | 流失預警通知 | score_decay hook |

**Phase 1 交付物**：
- Telegram Bot 可收到 4 種通知
- Admin 後台可設定 Telegram 綁定 + 通知開關
- 通知記錄可在後台查看

### Phase 2 — 對話式互動

**目標**：使用者可以直接在 Telegram 問問題、下指令  
**預估工時**：5-7 天

| 步驟 | 內容 |
|------|------|
| 1 | `copilot/engine.py`：LLM + Function Calling 引擎 |
| 2 | `copilot/tools.py`：10 個 ForgeBase 查詢/操作 tools |
| 3 | `webhook_telegram.py`：接收使用者訊息 → engine |
| 4 | 對話歷史存儲 + 上下文視窗管理 |
| 5 | 安全性：tenant 隔離 + 操作確認機制 |
| 6 | Inline Keyboard 快捷操作按鈕 |

**Phase 2 交付物**：
- 使用者可在 Telegram 與 AI 專員對話
- 支援查詢 RFQ、訪客、產品數據
- 支援指令式操作（回覆 RFQ、更新標籤等）

### Phase 3 — LINE 整合 + 站內通知

**目標**：覆蓋台灣客戶常用的 LINE  
**預估工時**：3-5 天

| 步驟 | 內容 |
|------|------|
| 1 | 申請 LINE Official Account + Messaging API |
| 2 | `channels/line.py`：推送 + 接收實作 |
| 3 | `webhook_line.py`：LINE webhook 端點 |
| 4 | LINE 綁定流程（OAuth / 驗證碼） |
| 5 | Flex Message 美化版通知 |
| 6 | Admin 站內通知中心 UI |

### Phase 4 — 進階智慧（可選）

| 功能 | 說明 |
|------|------|
| 智慧靜音 | AI 判斷通知重要性，低重要度自動降頻 |
| 跨租戶洞察 | Platform Admin 收到全平台級摘要 |
| 自動 nurture 執行 | AI 判斷 + 自動發送 re-engagement email（需確認） |
| 語音訊息 | Telegram 語音→文字→AI 回覆 |
| 行動看板 | Telegram Mini App 嵌入簡易 dashboard |

---

## 十一、設定項（新增 env）

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=           # @BotFather 取得
TELEGRAM_WEBHOOK_SECRET=      # webhook 驗證用

# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN=    # LINE Developers Console
LINE_CHANNEL_SECRET=          # webhook 簽名驗證

# Copilot AI
COPILOT_MODEL_NAME=gpt-5.4   # 可獨立於 chat advisor 設定
COPILOT_MAX_TOKENS=2048
COPILOT_DAILY_SUMMARY_HOUR=8 # 本地時間幾點發摘要
COPILOT_TIMEZONE=Asia/Taipei
```

---

## 十二、安全性考量

| 風險 | 對策 |
|------|------|
| Telegram/LINE 帳號被冒用 | 綁定時需後台登入 + 驗證碼雙重確認 |
| AI 誤操作（發錯 email、改錯狀態） | 高風險操作一律要求確認（「確定要發送嗎？回覆 Y」） |
| 跨租戶資料洩露 | copilot engine 的每個 tool call 都帶 tenant_id filter |
| 通知轟炸 | Rate limit：同類型通知每 5 分鐘最多 1 則 |
| Webhook 被偽造 | Telegram：secret_token 驗證；LINE：X-Line-Signature HMAC |
| 對話記錄隱私 | 對話存 DB，不經第三方；可設自動過期刪除 |

---

## 十三、成本預估

| 項目 | Phase 1 月成本 | 備註 |
|------|--------------|------|
| Telegram Bot API | $0 | 免費 |
| OpenAI API（通知摘要 + 對話） | ~$5-20/月 | 取決於租戶數、RFQ 量 |
| LINE Messaging API | $0（500 則內） | 超過需付費 |
| 額外基礎設施 | $0 | 複用現有 API server |

---

## 十四、成功指標

| 指標 | 目標 |
|------|------|
| 後台登入頻率下降 | 使用者不需要天天開後台也能掌握狀況 |
| RFQ 首次回覆時間 | < 2 小時（目前很多超過 24h） |
| Hot visitor 跟進率 | > 80%（目前很多被忽略） |
| 每日摘要開啟率 | > 70% |
| AI 專員對話使用率 | > 3 次/週/用戶 |

---

## 十五、結論

這個功能不是從零開始，而是把 ForgeBase 已有的 AI 分析能力  
**從後台搬到使用者的口袋裡**。

核心程式碼（intent scoring、AI RFQ、content optimizer、webhook）都已到位，  
主要新增的是：

1. **事件監測 → 決策 → 推送** 管線
2. **Telegram / LINE 通道** 整合
3. **LLM Function Calling** 對話引擎
4. **通知偏好 + 歷史** 管理

Phase 1（Telegram 被動通知）預計 5-7 天可交付，  
是驗證「使用者到底想不想被主動通知」的最低成本實驗。
