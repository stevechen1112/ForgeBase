# ForgeBase AI Product Advisor + AI-guided RFQ MVP — 技術規格與 2 Sprint 開發計畫

> 版本：v1.1 MVP | 更新日期：2026-03-16  
> 對應產品：ForgeBase 外銷製造商官網成長系統  
> 目標：在 2 個 sprint 內落地可驗證的 AI Product Advisor + AI-guided RFQ MVP

---

## 1. MVP 定位

### 1.1 為什麼要做 MVP，而不是完整平台

ForgeBase 的核心不是做一個功能很多的聊天工具，而是把前台的高意圖買家更有效地導向 RFQ。

因此第一版 AI 的任務只有三件事：

1. 即時回答產品與 FAQ 類問題，降低跳出率
2. 在高意圖時刻把買家導向 RFQ
3. 為現有意圖分析補上一層「主動提問」訊號

第一版不追求完整知識庫平台、不追求複雜營運分析，也不追求全站全面覆蓋。

### 1.2 產品定義

這份功能不應被定義成泛用 AI 客服，而應被定義成兩個緊密耦合的能力：

1. **AI Product Advisor**：回答產品、FAQ、認證、材質、MOQ、OEM 等問題
2. **AI-guided RFQ**：當使用者出現明確採購訊號時，協助整理需求並導向 RFQ

這樣定義的原因是：

1. 更貼近 ForgeBase 以轉換為核心的產品定位
2. 能控制範圍，不滑向訂單客服或萬用聊天機器人
3. 能讓前台互動直接對接後台的意圖分析與 RFQ 資料

### 1.3 MVP 功能邊界

| MVP 內 | MVP 外 |
|--------|--------|
| 回答產品規格、材質、尺寸、認證、FAQ 問題 | 不做報價 |
| 在產品頁與 FAQ 頁提供 AI 顧問入口 | 不做訂單/售後客服 |
| 對話中引導至 RFQ 頁與預填欄位 | 不做競品比較顧問 |
| 帶入當前頁面上下文回答 | 不做全站知識搜尋平台 |
| 記錄 chat_start 與 chat_rfq_handoff 事件 | 不做複雜聊天分析 dashboard |

### 1.4 MVP 成功標準

MVP 是否成功，只看這 4 個指標：

| 指標 | 目的 |
|------|------|
| Chat 使用率 | 訪客是否願意與 AI 互動 |
| Chat → RFQ 點擊率 | AI 是否有助於推進轉換 |
| Chat 使用者 RFQ 提交率 | 是否優於未使用 chat 的訪客 |
| 無法回答率 | 檢查內容覆蓋是否足夠 |

---

## 2. MVP 範圍

### 2.1 啟用頁面

第一版只在以下兩類頁面啟用：

1. 產品詳情頁 `/products/[categorySlug]/[productSlug]`
2. FAQ 頁 `/faq` 與 `/faq/[tag]`

不在首頁、應用頁、認證頁、聯絡頁全面啟用，避免過早擴散。

### 2.2 使用者可問的問題類型

| 類型 | 例子 |
|------|------|
| 規格問題 | What material is this made of? |
| 認證問題 | Does this product meet ISO requirements? |
| 適用場景 | Is this suitable for automotive repair? |
| 客製需求 | Can you do OEM logo engraving? |
| FAQ 類問題 | What is your MOQ? |

### 2.3 回答原則

AI 只能依據現有資料回答：

1. 當前產品頁資料
2. 相關 FAQ 資料
3. 相關認證資料
4. 產品分類與應用場景的簡短描述

如果資料裡沒有，必須明確說不知道，並導向 RFQ 或 Contact。

---

## 3. MVP 技術設計

### 3.1 簡化架構

```
前台產品頁 / FAQ 頁
        │
        ▼
  ChatWidget（浮動入口）
        │
        ▼
POST /api/v1/chat/sessions
POST /api/v1/chat/sessions/{id}/messages
POST /api/v1/chat/sessions/{id}/handoff
        │
        ▼
ChatService
├─ 讀取當前頁面上下文
├─ 關鍵字查詢 FAQ / 認證 / 產品資料
└─ 呼叫 OpenAI 生成回答
        │
        ▼
RFQ 預填導流
```

### 3.2 不做的技術項目

以下項目明確延後，不進 MVP：

1. pgvector
2. embedding pipeline
3. 自動重建知識索引
4. Chat analytics dashboard
5. 滿意度評分
6. A/B testing framework
7. 對話主題意圖分類模型

### 3.3 檢索方式

MVP 採用「RAG-lite」，不是完整 RAG 平台。

回覆組裝順序：

1. 先抓目前頁面實體資料
2. 再用 SQL / 關鍵字匹配抓相關 FAQ
3. 如有認證關鍵字，再補認證內容
4. 將這些資料片段組成 prompt context

這樣的好處：

1. 不需要 pgvector
2. 不需要新基礎設施
3. 可直接利用現有內容 API 與資料表
4. 對 ForgeBase 目前內容量已足夠

---

## 4. 資料設計

### 4.1 新增最小資料表

MVP 只新增兩張表：

#### `chat_sessions`

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id UUID NOT NULL REFERENCES visitors(visitor_id),
    session_id UUID,
    context_page VARCHAR(500),
    context_entity_type VARCHAR(30),
    context_entity_id UUID,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    message_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `chat_messages`

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.2 為什麼保留 chat_messages

雖然 MVP 要收斂，但仍建議保留 `chat_messages`，原因很實際：

1. 要能回頭檢查 AI 是否答錯
2. 要能分析無法回答的問題
3. 要能重建單一對話流程

但不落 token_count、latency_ms、satisfaction 等營運欄位，先保持最小。

### 4.3 後台資料串接原則

AI 互動資料分兩條線進後台，不能混在同一層：

#### A. 事件資料線

進入既有 `tracking_events`，用途是意圖分析與轉換分析。

MVP 至少記錄：

1. `chat_start`
2. `chat_rfq_handoff`
3. 可選：`chat_no_answer`

建議 properties：

```json
{
  "chat_session_id": "uuid",
  "context_page": "/products/...",
  "context_entity_type": "product",
  "context_entity_id": "uuid",
  "source": "chat_widget"
}
```

#### B. 對話資料線

進入 `chat_sessions` 與 `chat_messages`，用途是品質檢查、內容缺口分析與對話回放。

MVP 至少保存：

1. `chat_session_id`
2. `visitor_id`
3. `context_page`
4. `context_entity_type`
5. `context_entity_id`
6. `role`
7. `content`
8. `sources`
9. `created_at`

這樣後台才能同時回答三件事：

1. 使用者有沒有因為 chat 更容易走向 RFQ
2. AI 到底回答了什麼
3. 哪些問題是目前資料庫答不出來的

### 4.4 AI 回覆如何與 RFQ 關聯

當 AI 偵測到高意圖訊號時，不只是丟一個連結，而是要把對話內容整理成可用於 RFQ 的結構化資料。

MVP 可先抽出以下欄位：

```json
{
  "product_interest": "Adjustable Wrench 8 inch",
  "need_oem": true,
  "need_certification": ["ISO 9001"],
  "quantity_hint": "5000 pcs",
  "message_summary": "Buyer asks for OEM logo engraving and minimum order quantity."
}
```

這些資料不一定立即寫入正式 RFQ，但至少要能組成 `rfq_prefill_url` 或後續表單預填資料。

---

## 5. API 設計

### 5.1 MVP 只做 3 個 endpoint

#### `POST /api/v1/chat/sessions`

用途：建立一場對話，回傳 greeting 與預設建議問題。

**Request**
```json
{
  "visitor_id": "uuid",
  "session_id": "uuid",
  "context_page": "/products/wrenches/adjustable-wrench-8",
  "context_entity_type": "product",
  "context_entity_id": "uuid"
}
```

#### `POST /api/v1/chat/sessions/{id}/messages`

用途：送出問題並取得 AI 回覆。

MVP 可以先用一般 JSON response，不必一開始就上 SSE。

**Response**
```json
{
  "data": {
    "reply": "Chrome vanadium steel has better durability and torque resistance than carbon steel.",
    "sources": [
      {"type": "product", "id": "uuid", "name": "Adjustable Wrench 8\"", "url": "/products/..."},
      {"type": "faq", "id": "uuid", "name": "What materials do you use?", "url": "/faq/..."}
    ],
    "suggested_action": "rfq"
  }
}
```

#### `POST /api/v1/chat/sessions/{id}/handoff`

用途：將高意圖對話導向 RFQ，並帶入預填資料。

**Response**
```json
{
  "data": {
    "rfq_prefill_url": "/rfq?message=Need+OEM+engraving&quantity=5000+pcs"
  }
}
```

### 5.2 為什麼不先做 SSE

SSE 體驗更好，但不是 MVP 必需。

先做普通 JSON 回應的理由：

1. 降低前後端串流處理複雜度
2. 降低錯誤面積
3. 更快驗證產品價值

如果第一版互動率與 RFQ 導流證明成立，再升級 SSE。

### 5.3 回覆與後台資料的執行順序

`POST /messages` 的後端處理順序建議固定如下：

1. 驗證 session 是否存在且 visitor_id 一致
2. 寫入一筆 user message
3. 讀取最近 10 則對話
4. 讀取當前頁面上下文
5. 查詢相關 FAQ / 認證 / 補充資料
6. 組 prompt 呼叫 OpenAI
7. 寫入 assistant message
8. 判斷是否應觸發 `suggested_action = rfq`
9. 如為高意圖，允許後續呼叫 handoff endpoint

這個順序很重要，因為它保證後台資料一定能完整還原一次對話，而不是只留下最終結果。

---

## 6. Prompt 與回答策略

### 6.1 系統角色

```text
You are an AI Product Advisor for a B2B manufacturer website.

You may answer only using the provided page and knowledge context.
If the answer is not supported by the context, say you do not have confirmed information and suggest submitting an RFQ or contact request.

Do not provide pricing, delivery promises, legal claims, or competitor comparisons.
Keep answers concise and practical.
```

### 6.2 回答規則

1. 優先回答當前產品頁上的資訊
2. 若問題涉及 MOQ、OEM、custom、timeline，結尾附上 RFQ 引導
3. 若無足夠資訊，不得編造
4. 回答語言跟隨使用者語言

### 6.3 對話體驗設計原則

目標不是讓 AI 看起來像真人聊天，而是讓它在產品諮詢與詢價引導上，比一般第一線客服更快、更準、更會收斂。

#### 原則 1：開場要帶上下文

不能只說「有什麼可以幫您」，而要明確知道使用者現在在看什麼。

例如：

1. 在產品頁：`I can help with material, MOQ, certification, or OEM options for this product.`
2. 在 FAQ 頁：`I can help you quickly find MOQ, customization, or quotation-related answers.`

#### 原則 2：只做必要反問

AI 可以反問，但一次只追一個關鍵缺口，不做冗長盤問。

建議優先順序：

1. 先釐清是標準品還是 OEM
2. 再釐清在意的是規格、認證還是 MOQ
3. 若已明顯接近詢價，再切 RFQ，不繼續聊天

#### 原則 3：答案要短、準、有依據

每次回覆應遵守：

1. 先直接回答
2. 再補一句依據或限制
3. 最後視情況補一個下一步

理想格式：

```text
Yes, this product supports OEM logo engraving.
Based on our current product and FAQ information, OEM branding is available for custom orders.
If you already have target quantity or logo requirements, I can help you prepare an RFQ.
```

#### 原則 4：高意圖時停止長聊，改做導流

當使用者出現下列訊號時，回覆重心應從「回答」切換成「整理需求並導向 RFQ」：

1. 提到 quantity / MOQ
2. 提到 OEM / customization
3. 提到 sample / lead time
4. 提到 certification requirement
5. 明確要 quote / quotation / pricing discussion

#### 原則 5：拒答要專業，不像機器報錯

例如不要說「我無法處理你的請求」，而應說：

`I don't have confirmed pricing or lead-time data in the current product record. The fastest next step is to submit an RFQ, and I can help you prepare it.`

### 6.4 建議問題

MVP 的建議問題不用動態生成，先做固定模板：

#### 在產品頁

1. What material is this product made of?
2. What certifications does this product have?
3. Can you provide OEM or custom branding?

#### 在 FAQ 頁

1. What is your MOQ?
2. Can you support custom specifications?
3. How do I request a quotation?

### 6.5 五個體驗問題如何落成規則

以下五項應直接做進產品設計，而不是只寫在 prompt：

1. **開場語怎麼設計**：依 `context_page` 與 `context_entity_type` 產出固定模板 greeting
2. **什麼時候該反問**：只有在缺關鍵槽位時才反問，例如 OEM / quantity / certification requirement
3. **什麼時候該導 RFQ**：偵測高意圖關鍵字或需求明確時就切 handoff
4. **哪些回答必須拒答或轉真人**：價格、正式交期、法規保證、客訴、訂單查詢
5. **怎樣聽起來專業但不像機器人**：短句、少套話、先回答再導下一步

---

## 7. 前端設計

### 7.1 元件範圍

MVP 前端只需要 4 個核心元件：

```
web/src/components/chat/
├── ChatWidget.tsx
├── ChatPanel.tsx
├── ChatMessage.tsx
└── ChatInput.tsx
```

可選補充：

1. `ChatSuggestions.tsx` 可與 `ChatPanel.tsx` 合併，不必拆檔
2. `useChat.ts` hook 可保留，但不必為了架構拆太細

### 7.2 UI 行為

1. 桌面版為右下角浮動視窗
2. 手機版為全螢幕 sheet
3. 初次打開顯示 greeting + 3 個建議問題
4. 使用者送出後顯示 loading state
5. AI 回覆若適合轉 RFQ，顯示按鈕導向 `/rfq`

### 7.3 細緻互動體驗

若要做到接近真人、甚至比真人更好，前端不只要能送收訊息，還要把互動細節做對：

1. **首輪體驗要快**：第一次打開先顯示 greeting 與建議問題，不要讓使用者面對空白輸入框
2. **輸入時要有任務感**：placeholder 不寫 generic 文案，改寫成 `Ask about material, MOQ, OEM, or certification...`
3. **回答後要有下一步**：若是高意圖答案，直接出現 `Prepare RFQ` 按鈕
4. **來源顯示要克制**：只顯示 1-2 個來源標籤，不要把畫面變成文件檢索器
5. **切頁要保留上下文**：同一個 session 內從產品頁跳 RFQ，前面對話摘要要能帶過去

### 7.4 啟用條件

`layout.tsx` 不直接全站顯示 Widget，而是透過 pathname 判斷：

1. `pathname.startsWith("/products/")`
2. `pathname.startsWith("/faq")`

---

## 8. 意圖評分整合

### 8.1 MVP 只新增 2 個事件

```python
BASE_SCORES.update({
    "chat_start": 8,
    "chat_rfq_handoff": 20,
})
```

### 8.2 為什麼不給每則 chat_message 加分

這是刻意收斂，避免意圖模型被洗高：

1. 愛提問不代表有購買意圖
2. 使用者可能反覆追問同一件事
3. 目前 ForgeBase 的 intent model 還在建立信任，不能太早加噪音

因此第一版只把「主動開啟對話」與「從對話轉 RFQ」視為有效信號。

---

## 9. 安全與限制

### 9.1 MVP 必要限制

| 項目 | 規則 |
|------|------|
| 單則訊息字數 | 500 字以內 |
| 每分鐘訊息數 | 每個 visitor_id 最多 10 則 |
| 對話歷史 | 只帶最近 10 則訊息 |
| 允許話題 | 產品、FAQ、認證、MOQ、OEM、RFQ |

### 9.2 MVP 安全策略

1. 對輸入做長度限制
2. Prompt 中明確禁止編造價格、交期、法規承諾
3. 若問題超出範圍，統一回覆導向 Contact / RFQ

MVP 先不做額外 moderation pipeline，除非上線後觀察到濫用。

---

## 10. 開發計畫：2 Sprint

### Sprint 1：Backend MVP

**目標**：完成最小可用的 chat 後端與資料落地  
**規模**：約 12-15 SP

| # | Task | 類型 | 優先級 | 說明 |
|---|------|------|--------|------|
| 1.1 | 建立 `chat_sessions` / `chat_messages` migration | Backend | P0 | 最小資料表 |
| 1.2 | 建立 SQLModel 模型 | Backend | P0 | ChatSession / ChatMessage |
| 1.3 | 實作 `chat_service.py` | Backend | P0 | 讀取頁面上下文、FAQ、認證並組 prompt |
| 1.4 | 實作 3 個 chat endpoints | Backend | P0 | sessions / messages / handoff |
| 1.5 | 將 `chat_start`、`chat_rfq_handoff` 接入 intent_scoring | Backend | P0 | 不加 `chat_message` |
| 1.6 | 加入基本 rate limit 與輸入長度檢查 | Backend | P1 | 簡單實作即可 |
| 1.7 | 撰寫 API 測試 | Test | P1 | session 建立、message 回答、handoff URL |

**Sprint 1 交付標準**：

1. API 可從產品頁上下文回答問題
2. 可正確儲存 session 與 message
3. 可回傳 RFQ handoff URL

### Sprint 2：Frontend MVP + 上線驗證

**目標**：完成前端 widget、接入 RFQ 導流，並上線驗證  
**規模**：約 12-15 SP

| # | Task | 類型 | 優先級 | 說明 |
|---|------|------|--------|------|
| 2.1 | 建立 ChatWidget / ChatPanel / ChatInput / ChatMessage | Frontend | P0 | 最小元件集 |
| 2.2 | 接入 chat API | Frontend | P0 | 建立 session、送出訊息、顯示回覆 |
| 2.3 | 在產品頁與 FAQ 頁條件式顯示 widget | Frontend | P0 | 僅兩種頁面 |
| 2.4 | 接入 `track("chat_start")` 與 handoff tracking | Frontend | P0 | 追蹤最小訊號 |
| 2.5 | 顯示 RFQ CTA 並導向預填 URL | Frontend | P0 | 核心轉換行為 |
| 2.6 | UI 微調與手機版適配 | Frontend | P1 | 可用即可，不追求過多動畫 |
| 2.7 | 生產部署與 smoke test | Full-stack | P0 | mitselect.com 驗證 |

**Sprint 2 交付標準**：

1. 產品頁與 FAQ 頁可正常使用 chat
2. 使用者可被引導到 RFQ
3. 後台資料庫可看到 chat 事件與 session 記錄

---

## 11. 工程實作規格

### 11.1 API Schema

#### `POST /api/v1/chat/sessions`

**Request Schema**

```json
{
  "visitor_id": "uuid",
  "session_id": "uuid",
  "context_page": "/products/wrenches/adjustable-wrench-8",
  "context_entity_type": "product",
  "context_entity_id": "uuid",
  "locale": "en"
}
```

**Response Schema**

```json
{
  "data": {
    "chat_session_id": "uuid",
    "greeting": "I can help with material, MOQ, certification, or OEM options for this product.",
    "suggestions": [
      "What material is this product made of?",
      "What certifications does this product have?",
      "Can you provide OEM or custom branding?"
    ]
  }
}
```

#### `POST /api/v1/chat/sessions/{id}/messages`

**Request Schema**

```json
{
  "visitor_id": "uuid",
  "content": "Can you do OEM logo engraving?",
  "locale": "en"
}
```

**Response Schema**

```json
{
  "data": {
    "reply": "Yes, OEM logo engraving is supported for custom orders.",
    "sources": [
      {
        "type": "product",
        "id": "uuid",
        "name": "Adjustable Wrench 8\"",
        "url": "/products/wrenches/adjustable-wrench-8"
      }
    ],
    "suggested_action": "rfq",
    "handoff_ready": true,
    "handoff_prefill": {
      "message": "Need OEM logo engraving",
      "product_ids": ["uuid"]
    }
  }
}
```

#### `POST /api/v1/chat/sessions/{id}/handoff`

**Request Schema**

```json
{
  "visitor_id": "uuid",
  "intent_reason": "oem_and_quantity",
  "prefill": {
    "message": "Need OEM logo engraving",
    "quantity": "5000 pcs",
    "product_ids": ["uuid"]
  }
}
```

**Response Schema**

```json
{
  "data": {
    "rfq_prefill_url": "/rfq?message=Need+OEM+logo+engraving&quantity=5000+pcs",
    "prefill": {
      "message": "Need OEM logo engraving",
      "quantity": "5000 pcs",
      "product_ids": ["uuid"]
    }
  }
}
```

### 11.2 Backend State Machine

MVP 雖然簡化，但對話流程仍應有明確狀態，避免前後端各自猜測。

#### Chat Session 狀態

| 狀態 | 說明 | 進入條件 | 離開條件 |
|------|------|----------|----------|
| `active` | 正常對話中 | 建立 session 後 | handoff 或超時結束 |
| `handoff_ready` | 已達高意圖，可導 RFQ | AI 回覆判定 `suggested_action = rfq` | 使用者進入 handoff |
| `handoff_completed` | 已產出 RFQ 預填資料 | handoff endpoint 成功 | 使用者離站或提交 RFQ |
| `closed` | 對話結束 | 超時或人工關閉 | 無 |

#### Message Flow 狀態機

```text
open widget
  -> create session
  -> greeting shown
  -> user sends message
  -> validate input
  -> save user message
  -> retrieve context
  -> build prompt
  -> call OpenAI
  -> save assistant message
  -> decide next action
      -> normal reply
      -> rfq handoff ready
```

### 11.3 Frontend State Machine

前端 widget 至少要有以下狀態，避免 UI 錯亂：

| 狀態 | 說明 |
|------|------|
| `idle` | widget 尚未展開 |
| `opening` | 正在建立 session |
| `ready` | 已可輸入，顯示 greeting 與 suggestions |
| `sending` | 使用者送出訊息中 |
| `answered` | 已收到 AI 回覆 |
| `handoff-ready` | 顯示 RFQ CTA |
| `error` | API 失敗或回覆異常 |

建議前端狀態資料：

```typescript
type ChatUiState =
  | "idle"
  | "opening"
  | "ready"
  | "sending"
  | "answered"
  | "handoff-ready"
  | "error";
```

### 11.4 Prompt Template

#### System Prompt

```text
You are the AI Product Advisor for a B2B manufacturer website.

Your job is to help buyers understand product specifications, certifications, OEM capability, MOQ, and quotation process.

Rules:
1. Use only the supplied context.
2. Never invent pricing, lead time, legal compliance, or unsupported claims.
3. If information is missing, say it is not confirmed and suggest RFQ or contact.
4. Keep answers concise, practical, and professional.
5. Ask only one clarifying question at a time when needed.
6. If the buyer shows clear purchase intent, shift toward preparing an RFQ.
```

#### User Prompt Assembly

```text
CURRENT PAGE:
{context_page}

ENTITY TYPE:
{context_entity_type}

ENTITY DATA:
{entity_summary}

RELATED FAQS:
{faq_summary}

RELATED CERTIFICATIONS:
{cert_summary}

RECENT CHAT HISTORY:
{recent_messages}

USER QUESTION:
{user_question}
```

#### Response Contract

後端不要只拿自然語言結果，應要求模型輸出結構化 JSON：

```json
{
  "reply": "text",
  "needs_clarification": false,
  "clarifying_question": null,
  "suggested_action": "none",
  "handoff_reason": null,
  "prefill": {}
}
```

可接受的 `suggested_action`：

1. `none`
2. `rfq`
3. `contact`

### 11.5 Handoff Rules

AI-guided RFQ 不是單純塞一顆按鈕，而是依明確規則觸發。

#### 觸發 handoff 的條件

任一條件成立即可：

1. 使用者明確提到 `quote`, `quotation`, `RFQ`, `price`, `MOQ`
2. 使用者提到 `OEM`, `custom`, `branding`, `private label`
3. 使用者提供了數量、應用場景、規格需求中的任兩項
4. 使用者問 lead time / sample / certification requirement 且已鎖定產品

#### 不應立即 handoff 的情況

1. 使用者仍在做基礎產品理解
2. 使用者只問單一規格點，沒有採購訊號
3. 使用者問題超出知識範圍，但沒有明顯詢價意圖

#### Handoff 後要整理的資料

MVP 至少整理下列欄位：

1. `product_ids`
2. `application_id`（若可判斷）
3. `quantity`
4. `specifications`
5. `message`
6. `need_oem`
7. `need_certification`

### 11.6 細緻體驗的技術落點

若要做到「像真人甚至更好」，真正要落在工程規則上的，是以下幾點：

1. **開場 contextualized**：session 建立時依 `context_entity_type` 選 greeting 模板
2. **單輪單問題澄清**：後端若回傳 `needs_clarification = true`，前端只顯示一個澄清問題
3. **回答與導流分離**：先回答，再決定是否顯示 RFQ CTA，不要一開口就推表單
4. **切到 RFQ 時保留上下文**：handoff 產生的 prefill 要帶前述對話摘要
5. **後台可回放**：每輪 user / assistant message 都落庫，供 QA 與優化使用

---

## 12. 上線後驗證方式

### 12.1 第一週只看 3 類資料

1. `tracking_events` 中 `chat_start` 的數量
2. `tracking_events` 中 `chat_rfq_handoff` 的數量
3. 使用過 chat 的 `visitor_id` 是否更常提交 RFQ

### 12.2 第一週也要抽查對話品質

除了事件量，也要抽查 `chat_messages`：

1. 回答是否真的引用當前產品資料
2. 是否出現編造價格或交期
3. 是否太快導 RFQ，造成體驗太像表單機器
4. 是否太晚導 RFQ，導致高意圖對話拖長
5. 哪些問題最常答不出來

### 12.3 建議 SQL 驗證

```sql
SELECT event_name, COUNT(*)
FROM tracking_events
WHERE event_name IN ('chat_start', 'chat_rfq_handoff')
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY event_name;
```

```sql
SELECT COUNT(DISTINCT visitor_id)
FROM rfq_requests
WHERE visitor_id IN (
  SELECT DISTINCT visitor_id
  FROM tracking_events
  WHERE event_name = 'chat_start'
);
```

```sql
SELECT context_page, role, content, created_at
FROM chat_messages cm
JOIN chat_sessions cs ON cs.id = cm.chat_session_id
WHERE cm.created_at > NOW() - INTERVAL '7 days'
ORDER BY cm.created_at DESC
LIMIT 50;
```

---

## 13. 延後到 V2 的項目

以下項目不是不要做，而是等 MVP 證明有效再做：

1. SSE 串流輸出
2. pgvector / embeddings
3. Chat analytics dashboard
4. 對話主題分類與更細的 intent bonus
5. 多語 greeting 自動化
6. 滿意度評分
7. A/B testing framework
8. 自動 embedding 更新 pipeline

---

## 14. 建議檔案範圍

### 新增檔案

```
api/app/models/chat.py
api/app/services/chat_service.py
api/app/api/v1/endpoints/chat.py
api/app/db/migrations/versions/xxx_add_chat_tables.py
api/tests/test_chat.py

web/src/components/chat/ChatWidget.tsx
web/src/components/chat/ChatPanel.tsx
web/src/components/chat/ChatMessage.tsx
web/src/components/chat/ChatInput.tsx
```

### 修改檔案

```
api/app/api/v1/router.py
api/app/services/intent_scoring.py
web/src/app/layout.tsx
web/src/lib/analytics.ts
```

---

## 15. 最終結論

這份 MVP 規格的核心是：

1. 先驗證 AI 是否能提升前台轉換
2. 先用最輕的技術方案落地
3. 先只在最有價值的頁面啟用
4. 等數據證明有效，再擴到完整 AI 客服平台

而且這個 MVP 的本質不是泛用客服，而是：

1. 用 **AI Product Advisor** 做更準的產品與 FAQ 回覆
2. 用 **AI-guided RFQ** 把高意圖訪客往詢價轉換推進
3. 把使用者提問、AI 回覆與 handoff 全部接回後台資料，形成可分析、可優化的閉環

這樣的範圍對 ForgeBase 現階段是恰如其分的，能在 2 個 sprint 內交付，也保留未來往完整版本演進的空間。

---

*文件結束 — ForgeBase AI Product Advisor + AI-guided RFQ MVP 技術規格 v1.2*
