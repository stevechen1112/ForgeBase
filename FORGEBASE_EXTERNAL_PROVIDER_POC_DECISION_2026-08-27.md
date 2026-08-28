# ForgeBase 外部供應商 POC 決策與啟用紀錄

日期：2026-08-27
狀態：程式接入、內部 adapter POC、真實 internal mail 與 provider 設定已完成；production 外部資料、自動外聯與 inbound processing 仍維持 fail closed

## 1. 明確結論

目前只使用三個免費帳號做受控內部 POC：

1. Resend：寄件、送達事件與後續 inbound reply 基礎設施。
2. People Data Labs（PDL）：第一輪聯絡窗口主測來源，使用 Person Search。
3. Hunter：第一輪聯絡窗口對照來源，使用 Domain Search；同時使用 Email Verifier。

Apollo 不在本輪申請、採購或啟用。只有 PDL 與 Hunter 在目標市場的覆蓋、品質或單位成本皆未通過 Gate，才重新評估 Apollo Data Reseller。

免費帳號與 API key 可用，只表示可進行技術驗證；不表示已取得多租戶 SaaS 的下游展示、保存、匯出、外聯或 OEM／Reseller 權利。

## 2. 已提供與已驗證資料

| 項目 | 狀態 | 備註 |
|---|---|---|
| Resend API 認證 | 通過 | 無寄信健康檢查通過 |
| Resend 寄件網域 | 通過 | `premierbiz.com.tw` 狀態為 verified |
| PDL API 認證 | 通過 | Sandbox 查詢成功；尚未作 production 資料 POC |
| Hunter API 認證 | 通過 | Free 帳號可用；查詢與驗證額度可讀取 |
| Adapter 極小量實測 | 通過 | PDL Sandbox 與 Hunter 自有公司網域請求皆正常處理；0 筆候選，不輸出個資 |
| Resend 真實 internal delivery | 通過 | provider accepted、delivered 與 sent／delivered webhook 均確認；只寄 internal allowlist |
| Resend webhook | 通過 | outbound 事件完整，並已加入 `email.received`；既有事件未被覆蓋 |
| Resend inbound domain | 部分通過 | `replies.premierbiz.com.tw` receiving-only；MX verified，DKIM pending，未啟用 production inbound processing |
| API 完整回歸 | 通過 | 乾淨 PostgreSQL：324 passed、3 skipped、0 failed |
| 寄件顯示名稱 | 已指定 | `ForgeBase Business Team` |
| 寄件 Email | 已指定 | `steve_chen@premierbiz.com.tw` |
| 真人接手 Email | 已指定 | `steve_chen@premierbiz.com.tw` |
| GitHub repository secrets | 已保存 | 三組 API key 已安全保存；值不可讀取且未提交 Git |
| GitHub repository variables | 已保存 | 寄件名稱、寄件 Email、接手／通知 Email 與 internal allowlist |
| 實際外寄 | 未執行 | 不用健康檢查信消耗真實名單或影響網域聲譽 |

API key 不記錄於本文件、不提交 Git，也不得出現在 log、URL query string、錯誤訊息或測試 fixture。

## 3. production 設定對應

取得書面資料使用核准及正式 POC 單價前，必須維持：

```dotenv
PDL_DATA_USE_APPROVED=false
PDL_CONTACT_DATA_USE_APPROVED=false
PDL_CONTACT_ESTIMATED_COST=0
HUNTER_DATA_USE_APPROVED=false
HUNTER_CONTACT_ESTIMATED_COST=0
HUNTER_VERIFY_ESTIMATED_COST=0
EMAIL_EXTERNAL_DELIVERY_ENABLED=false
OUTREACH_SEND_ENABLED=false
INBOUND_REPLY_ENABLED=false
```

寄件與真人接手設定在安全注入 production secret 時應對應：

```dotenv
EMAIL_FROM=steve_chen@premierbiz.com.tw
EMAIL_FROM_NAME=ForgeBase Business Team
SALES_NOTIFY_EMAIL=steve_chen@premierbiz.com.tw
MANAGER_EMAIL=steve_chen@premierbiz.com.tw
EMAIL_INTERNAL_RECIPIENT_ALLOWLIST=steve_chen@premierbiz.com.tw
```

`RESEND_API_KEY`、`PDL_API_KEY`、`HUNTER_API_KEY` 只可由 secret store／主機 secret 檔安全注入，以上範例刻意不含任何 key。

目前三組 key 已存入 GitHub repository secrets；production 只注入 adapter／transport 前置憑證，寄件與真人接手資料也已對齊。外部資料授權、正式單位成本與品質 Gate 未通過，因此 `*_DATA_USE_APPROVED`、外部寄送、自動外聯及 inbound processing 仍為 false；「憑證存在」不等於「功能核准啟用」。

## 4. 第一輪 POC 流程

```text
已確認公司 domain＋Persona policy
  ├─ PDL Person Search
  └─ Hunter Domain Search
       ↓
公司 domain／企業 Email／必要姓名欄位過濾
       ↓
ForgeBase 自有旅程與 Persona relevance ranking
       ↓
Hunter Email Verifier／供應商既有驗證訊號
       ↓
人工 approve／reject
       ↓
比較市場覆蓋、Persona relevance、Email 品質、新鮮度與成本
```

任何候選都只能代表「該公司可能相關的公開商務窗口」，不得宣稱是實際造訪網站的匿名訪客。

## 5. 程式安全邊界

- PDL Person Search 只取 `work_email`，不要求或保存 personal email、電話或原始 response。
- PDL 結果必須同時符合已確認公司 domain 與企業 Email domain；PDL 未提供 Person Search likelihood 時不得自造 confidence。
- Hunter Domain Search 限制 personal contact type（對應具姓名的企業窗口）、必要姓名與職稱、目標公司 domain，Free POC 每次最多 10 筆。
- PDL、Hunter、Apollo adapter 都必須同時具備資料使用核准、API key 與非零單位成本才會註冊；production 不提供 mock provider。
- Apollo adapter 保留為可替換能力，不代表已選用或可以繞過資料授權 Gate。
- Resend 寄件與 North Star outreach 各有獨立 kill switch；兩者未同時開啟時不得外寄。
- Inbound reply 使用獨立開關及獨立收信子網域。不得改動 `premierbiz.com.tw` 根網域既有 MX；規劃使用如 `replies.premierbiz.com.tw` 的專用子網域。

## 6. 剩餘可驗證里程碑

1. 向 PDL 與 Hunter 確認 ForgeBase 多租戶情境的展示、保存、刪除、外聯與跨境處理權利。
2. 權利通過後設定實際單位成本，才可在 production 開啟 `review_only` Shadow POC；仍不得寄信。
3. Resend webhook signing、專用 inbound 子網域、`email.received` 訂閱與 internal allowlist 真實信已完成；官方 `dns.email` 可讀取完整 DKIM 且 Tokyo receiving MX 為 Valid，但最新 provider 證據 `33154309882` 的 DKIM 仍 pending。官方文件允許 DNS 全球傳播最長 72 小時，production inbound secret 尚未注入。
4. 等 inbound DKIM verified 後完成真實回覆分類與真人接手；一般外寄仍須以 bounce／complaint／unsubscribe、reputation 與法遵證據通過後，才評估極小量人工核准寄送。

## 6.1 去識別化盲測計分工具（2026-08-28）

- 新增 `scripts/score_growth_provider_poc.py` 與 `config/growth-provider-poc.template.json`，將 A 公司辨識與 B 聯絡窗口的 case-level 盲測資料轉為不含個案、公司、domain、IP、姓名或 Email 的聚合報告。
- A 會分 provider／市場計算 eligible coverage、高信心 precision、conflict、排除網路誤配、成本與延遲；B 會計算 query coverage、Persona relevance、verified business email、新鮮度、不安全候選、成本與延遲。
- 每個 provider 必須各自覆蓋至少兩個市場；公司高信心與聯絡人 reviewed sample 每市場至少 50，並使用 90% precision／70% relevance 既有 Gate。
- 重複 case/provider、無法成立的 count、負數或 NaN／Infinity、PII 欄位與未附 evidence reference 的資料權批准一律拒絕。
- 工具已完成且納入 API CI；目前範本權利值全為 false、樣本為空，因此不宣稱 PDL／Hunter 已通過品質或商用權利 Gate。

## 7. 不需要使用者再提供的項目

目前不需要再提供其他帳號或 API key，也不需要申請 HubSpot 或 Apollo。後續只有在需要修改 DNS 時，才需確認 `premierbiz.com.tw` 的 DNS 管理入口；若 ForgeBase 已具備該環境的控制權，則由系統方直接完成並留下變更紀錄。
