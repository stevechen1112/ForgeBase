# AI Product Advisor 測試紀錄 2026-03-16

## 1. 後台串接確認

- Production DB 實查結果：
  - chat_sessions = 8
  - chat_messages = 6
  - tracking_events.chat_start = 8
  - tracking_events.chat_rfq_handoff = 3
- 結論：前台 chatbot 不只是 UI，session、message、handoff event 都有落到後端資料庫。

## 2. Production LLM 串接狀態

- 初始檢查時，production API log 曾出現 OpenAI AuthenticationError 401 invalid_api_key。
- 2026-03-16 已更新 production API 的 OPENAI_API_KEY，並成功重啟 forgebase-api。
- 更新後再次做 production 對話驗證，category 與 application context 都已回傳真實內容回答，不再是 fallback。

## 3. Production 深度 Smoke Test

### Category context

- 建 session：成功
- 送 message：成功
- handoff：成功

#### Session greeting

```json
{
  "chat_session_id": "8d53dffb-a5d4-4383-bd12-b9ce07704d80",
  "greeting": "I can help you compare options in Torque and Socket Tools, narrow down fit, and move toward an RFQ.",
  "suggestions": [
    "Which products in this category fit OEM projects?",
    "What certifications are common in this category?",
    "How do I request a quote for this category?"
  ]
}
```

#### Message reply

User:

```text
We distribute torque tools in Europe. Which sub-types in this category are best for workshop service kits and what OEM options do you support?
```

Assistant:

```json
{
  "reply": "I don't have confirmed information for that in the current record. The fastest next step is to submit an RFQ or contact request.",
  "suggested_action": "contact",
  "handoff_ready": true,
  "sources_count": 5
}
```

#### Handoff reply

```json
{
  "rfq_prefill_url": "/rfq?name=Martin+Keller&email=martin.keller%40example.com&company_name=MK+Industrial+Supply&message=Interested+in+torque+tools+for+European+workshop+kits+and+OEM+branding."
}
```

### Application context

- 建 session：成功
- 送 message：成功
- handoff：成功

#### Session greeting

```json
{
  "chat_session_id": "8ff6f2f0-84eb-444f-9d3e-6fba0994fa0a",
  "greeting": "I can help you evaluate products, requirements, and RFQ next steps for Automotive Aftermarket Service.",
  "suggestions": [
    "Which products fit this application best?",
    "Can you support OEM or customization for this use case?",
    "What should I include in an RFQ for this application?"
  ]
}
```

#### Message reply

User:

```text
For automotive aftermarket service, which tool categories should we start with for a mid-range distributor assortment, and can you support private label packaging?
```

Assistant:

```json
{
  "reply": "I don't have confirmed information for that in the current record. The fastest next step is to submit an RFQ or contact request.",
  "suggested_action": "contact",
  "handoff_ready": true,
  "sources_count": 0
}
```

#### Handoff reply

```json
{
  "rfq_prefill_url": "/rfq?name=Laura+Stein&email=laura.stein%40example.com&company_name=Autotec+Distribution+GmbH&message=Needs+a+starter+assortment+for+automotive+aftermarket+with+private+label+options."
}
```

## 4. 本輪程式補強

- 已補強 category context：
  - 帶入更多 representative products
  - 聚合 category 內 product FAQ
  - 聚合 category 內 product certifications
  - 清理 HTML 噪音
- 已補強 application context：
  - 帶入 application 相關 products 與 category 名稱
  - 聚合 product FAQ + application FAQ
  - 聚合 product certifications
  - 清理 description / challenge / solution 的 HTML 噪音

## 5. 真實 LLM 品質測試狀態

- 使用者於 2026-03-16 提供有效 OpenAI API key 後，已完成本機真實對話測試。
- 本機真實多輪 transcript 檔案：
  - AI_Product_Advisor_真實對話測試_2026-03-16.json
- Production 驗證結果：
  - category context 已回傳具體 sub-types、產品類型建議、OEM 包裝支援與 RFQ 導向
  - application context 已回傳 distributor starter mix、產品組合邏輯、private-label 與 durability 確認項目

### 本機真實對話品質摘要

#### Category context

- 優點：
  - 能明確列出 TW-500、SK-94M、DTA-120
  - 會主動做 shortlist 與 bundle 建議
  - 會在 RFQ 前要求 SKU、OEM、包裝、CE 文件需求等具體資訊
- 缺點：
  - `suggested_action` 仍偏保守，沒有主動切到 rfq

#### Application context

- 優點：
  - 能以 distributor starter bundle 的方式回覆，不只是抽象類別
  - 會把 torque-critical service work 收斂到 TW-500
  - 會主動列出 private-label、packaging、durability expectation 等 RFQ 前置確認項
- 缺點：
  - 仍偏向整理式回答，clarifying question 使用不足

### Production 真實對話摘要

#### Category context

- Production 已回覆：
  - socket tool sets
  - ratchet handles
  - torque wrenches
  - digital torque adapters
  - fastening accessories
- 並回傳：
  - `suggested_action = rfq`
  - `handoff_ready = true`
  - 5 筆 product sources

#### Application context

- Production 已回覆：
  - torque tools
  - ratchets
  - socket systems
  - extraction tools
  - service kits
  - workshop-ready packaged assortments
- 並回傳：
  - `suggested_action = rfq`
  - `handoff_ready = true`

## 6. 測試檔案位置

- 測試總報告：AI_Product_Advisor_測試紀錄_2026-03-16.md
- 本機真實多輪對話 transcript：AI_Product_Advisor_真實對話測試_2026-03-16.json

## 7. 下一步

- 建議下一輪優化：
  1. 提高 clarifying question 使用率，讓對話更像顧問而不是整理器
  2. 在高意圖問題下更穩定地輸出 `suggested_action = rfq`
  3. 對 application context 補更多具體 SKU 級 sources，避免 sources 為空