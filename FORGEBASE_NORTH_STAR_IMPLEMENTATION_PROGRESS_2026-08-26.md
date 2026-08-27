# ForgeBase 北極星核心實作與 Code Review 紀錄

> 日期：2026-08-26（持續更新至 2026-08-27）\
> 依據：`FORGEBASE_NORTH_STAR_CORE_GAP_IMPLEMENTATION_PLAN_2026-08-26.md`\
> 原則：每一批必須完成實作、測試、code review、修正審查發現，才可進入下一批。功能完成不代表營運 Gate 自動通過；需要真實樣本或外部合約的 Gate 維持關閉。

## 批次狀態

| 批次 | 範圍 | 程式實作 | Code review | 營運／資料 Gate |
|---|---|---|---|---|
| 1 | Phase 0 契約、狀態、feature flags、資料基礎 | 完成 | 通過 | 新能力預設關閉 |
| 2 | 公司推測、Shadow Mode、POC adapter、平台審核 | 完成 | 通過 | **未通過**：尚需核准供應商資料使用權、真實 Shadow 樣本與 ≥90% 高信心 precision |
| 3 | 聯絡窗口候選與人工確認 | 完成 | 通過 | **未通過**：尚需資料權利、blind POC、persona relevance／verified-email 真實樣本 |
| 4 | 旅程快照與個人化草稿 | 完成 | 通過 | **通過 Review Only Gate**；只可建立與核准草稿，不得寄信 |
| 5 | 受控寄送與事件 | 完成 | 通過 | **程式 Gate 通過；營運 Gate 未通過**：全域寄送 kill switch 維持關閉，尚無真實送達／退訂／投訴樣本 |
| 6 | 回覆、真人接手、RFQ | 完成 | 通過 | **程式 Gate 通過；外部環境 Gate 未通過**：尚需正式收信 domain、DNS、簽名與 mailbox smoke test |
| 7 | 閉環歸因與 Controlled Auto | 完成 | 通過 | **閉環程式 Gate 通過；Controlled Auto 未開放**：尚無法遵核准與真實品質樣本 |
| 8 | 非核心移除、最終稽核 | 完成 | 通過 | **安全退場機制完成；觀察 Gate 進行中**：兩項靜態 dead／unsafe code 已移除，其餘候選仍須 production 30／60 天零使用與零依賴證據 |
| 9 | 結構完整性、單一產品與舊方案移除 | 完成 | 通過 | 固定核心預設開啟；試行、外部依賴及退場觀察能力維持 fail closed |
| 10 | 後台資訊架構與北極星工作中心 | 完成 | 通過 | 側欄聚焦日常入口；受控核心能力仍顯示於北極星流程，不冒充已啟用 |
| 11 | 可配置內容語系與批次草稿審核 | 完成 | 通過 | 日／法／俄內容草稿可用；完整公開網站介面包仍僅英／繁中，未假裝已交付 |
| 12 | 最終架構、schema、依賴、安全與技術債收斂 | 完成 | 通過 | 程式與結構 Gate 通過；外部資料授權、真實品質、正式郵件環境及 30／60 天觀察仍待營運證據 |

## 批次 1：Phase 0 與公司推測資料基礎

### 已實作

- `NetworkObservation`、`CompanyIdentification`、`IdentificationReview`、`ProviderUsage` 核心模型與 0079 migration。
- provider-neutral contract、無網路 mock adapter、只攜帶 observation ID 的 durable job contract。
- 北極星後續能力拆分 feature flags，全部 locked off。
- DB constraint：IP version、信心值、狀態、expiry、成本及用量不可為負。

### Code review 發現與修正

- IP version 原先只靠範圍驗證，補成 DB 僅允許 4／6。
- transient raw IP 可能出現在 dataclass repr，改為 `repr=False`。
- provider mock request ID 改成 deterministic，支援重放稽核。
- Python invariant 同步補入資料庫 constraints。

### 驗證

- Alembic 單一 head。
- 全 API baseline：164 passed、70 skipped。

## 批次 2：公司推測 Shadow Mode

### 已實作

- tenant `GrowthAutomationPolicy`：off／shadow、provider、intent threshold、保留期、每日 quota、每日成本上限、信心門檻、國家 allowlist。
- trusted-proxy-aware client IP 解析；未信任 direct peer 時完全忽略 forwarding header。
- consent、intent、public network、bot、國家、quota eligibility；HMAC IP hash、/24 或 /48 mask、每日 dedupe。
- PDL IP Enrichment POC adapter：僅回傳正規化公司候選及 VPN／proxy／hosting 風險；不保存 raw response、person 或地址資料。
- 真實 provider 只有在資料使用權核准、API Key 與合約單價都設定時才註冊。
- retry／Retry-After、permanent auth failure、circuit breaker、正向 TTL cache、cost guard、provider usage／request ID 稽核。
- provider conflict、人工 confirm／reject／correct、reject reason、平台 audit log。
- Shadow report：match rate、高信心率、unknown、conflict、precision、latency、units、預估成本；match rate 與 precision 分開。
- 平台後台頁：租戶策略、provider readiness、Shadow 指標、候選 review queue。
- consent 撤回與 TTL cleanup：取消 observation job、刪除 provider usage、公司候選與觀察，再刪 analytics；runtime 執行前再次確認 consent。

### Code review 發現與修正

1. trusted proxy 原先可能信任 forged XFF：改為 direct peer CIDR allowlist，並由右向左找最近的不可信 hop。
2. observation 的 select-then-insert 有併發 race：加入 policy row lock、savepoint 與 unique constraint fallback。
3. provider evidence sanitizer 以子字串判定會誤刪 `description`：改成 camelCase／token-aware 敏感欄位判定。
4. provider 可能回傳重複 key 或過長／無效欄位：adapter contract 加入唯一性、長度、domain 與最多 20 候選驗證。
5. job 完成寫入與 outbox 完成不同交易，可能重放 provider：成功 usage replay guard，cache replay 不重複連外。
6. allowed countries 原先只儲存未執行：缺少或不符 allowlist 時標為 `country_not_allowed`。
7. review／policy 修改缺少治理證據：補 platform audit log；reject 必須有原因。
8. Shadow metrics 原先只顯示 raw counts：補 match／precision 分離、unknown、conflict、provider latency 與成本。
9. consent 撤回會先刪 tracking event，與 observation FK 衝突且 queued job 仍存在：補 cascade／set-null 邊界、job 與 usage 清理、runtime consent recheck。
10. DB 測試同一 session 同時新增 visitor／event 可能無法保證 FK flush 順序：測試先 flush visitor，並加入真正 PostgreSQL migration／runtime 驗證。

### 驗證

- Ruff：本批 scoped files 全數通過。
- Admin：TypeScript type-check 與 ESLint 全數通過。
- API 無外部 DB 全回歸：178 passed、73 skipped；skip 為需 PostgreSQL／外部服務的條件測試。
- 隔離 PostgreSQL 16：從空資料庫升級至 0080 成功；0079／0080 downgrade 後再 upgrade 成功。
- 隔離 PostgreSQL 公司推測測試：17 passed，涵蓋 dedupe、replay、cache、quota、country、cost guard、circuit、consent cleanup。
- 相關 DB 整合組：31 passed。
- 全庫 DB 掃描另發現 10 個既有、非本批失敗，集中於舊 feature entitlement 測試假設、保留網域 email 測試資料、Copilot／Growth Ops／RFQ；記錄後於對應批次處理，不影響本批 17/17 與 migration gate。

### 尚未通過的營運 Gate

- PDL（或替代 provider）OEM／Data License／下游展示與保存權利尚未由實際合約核准，因此 `PDL_DATA_USE_APPROVED=false`。
- 尚未取得至少 30 天或足量真實 Shadow 樣本。
- 尚未以人工真值證明高信心 precision ≥90%。
- 因此 production 必須維持 off；可開發後續 locked-off 模組，但不得啟用聯絡人補全、寄送或 Controlled Auto。

## 批次 3：聯絡窗口候選與人工確認

### 已實作

- `ContactPersonaPolicy`、`ContactCandidate`、append-only `ContactCandidateReview` 與 0081 migration；模式僅 `off`／`review_only`。
- persona 強制限制部門／職稱、seniority、地區與排除詞；每公司候選、每日查詢、每日成本與 TTL 上限。
- provider-neutral contact search／email verification contracts、deterministic mock、Apollo People Search＋Enrichment POC、Hunter Email Verifier POC。
- 真實 adapter 只有在資料使用權旗標、API key 與合約單價均設定時註冊；production 不註冊 mock。
- `contact_enrich` durable job；payload 只有 company identification ID，不含 IP、visitor 或 email。
- 公司 domain、email 格式、公開商務信箱、persona、地區與第一方產品興趣的可解釋 relevance score。
- email ciphertext、HMAC hash、masked display；一般候選 API 不回傳明文。
- verified／risky／catch-all／unknown／invalid、source freshness、provider、成本、latency、retry 與 circuit breaker。
- pending candidate 的 approve／reject／do-not-contact；只有 approved＋verified＋relevance 合格＋未 suppressed 才可人工轉 `Contact`。
- 轉換後 `Contact.visitor_id` 固定為 null，並保存 `contact_candidate` provenance；UI 明示候選不是匿名訪客本人。
- 平台 Review Only 後台：persona／quota／cost policy、已確認公司 enqueue、候選來源／新鮮度／relevance／verification、審核與轉換、品質指標。
- consent withdrawal／TTL：未轉換候選與外部用量刪除；已人工轉 Contact 的候選去除 visitor/company FK，但保留公司快照與轉換稽核。

### Code review 發現與修正

1. DNC 原可被後續 reject 覆寫：改成 terminal state；立即清空可還原 email、姓名、職稱、地點與個人 source URL，只留 HMAC／mask 供阻擋。
2. 手動 reverify 原未計成本與失敗：補 quota／cost guard、latency、provider usage 與 fail-closed 502。
3. 同 email 的不同 candidate 可能並行建立重複 Contact：轉換前鎖定同 tenant＋email hash 的所有候選，再走 Contact unique key。
4. consent withdrawal 原會讓已轉換 Contact 的來源懸空或把所有候選一起保留：未轉換資料刪除；converted candidate 以 `SET NULL` 切斷匿名旅程並保留公司快照。
5. TTL 原只改 expired 狀態仍保留 PII：改為到期真刪除未轉換 candidate；候選期限不得晚於公司證據期限。
6. provider 成功／失敗與 retry 原未完整入帳：補 partial-failure ledger、retry count、latency 與連續失敗 circuit breaker。
7. rejected 候選會每日重查並浪費 credits：任何尚未過期候選都作 company-level replay guard；過期資料先清理再允許重查。
8. mock verification request ID 原含 email local part：改為不可逆 SHA-256 前綴。
9. Apollo 422 原被當成空結果：改為 permanent filter/config error，避免把 adapter 契約錯誤誤報成 no match。
10. 平台 audit target 原把 policy／enqueue 都標為 candidate：分別改為 persona policy、company identification 與 contact candidate。

### 驗證

- Ruff：第三批 scoped backend／tests 全數通過。
- Admin：TypeScript type-check 與 ESLint 全數通過。
- API 路由：contact policy、providers、enqueue、candidate review／verify／convert、metrics 均存在；OpenAPI app 共 238 routes。
- 隔離 PostgreSQL 16：空資料庫完整升級至 0081 成功；0081 → 0080 → 0081 往返成功；單一 Alembic head。
- 第二／第三批相關整合測試：37 passed；涵蓋 adapter、domain 過濾、加密、去重、DNC、invalid gate、人工轉換、不連 visitor、consent cleanup、retry ledger 與 circuit breaker。
- 全庫 DB 回歸：250 passed、2 skipped、10 個既有非第三批失敗；仍是 adoption reserved email fixture、舊 feature entitlement／Copilot／Growth Ops／intent／RFQ 測試契約，沒有 contact enrichment failure。

### 尚未通過的營運 Gate

- Apollo／Hunter 或替代供應商的 OEM／Reseller、下游顯示、保存與外聯用途尚未取得書面核准。
- 尚未在台灣、日本、北美與歐洲 blind POC 證明 persona relevance、verified email、freshness 與每位核准窗口成本。
- 因此 production policy 必須維持 `off`；即使開發環境可用 mock 驗證，也不得將候選投入寄送。

## 批次 4：旅程快照與個人化外聯草稿

### 已實作

- `OutreachDraftPolicy`、immutable `JourneySnapshot`、versioned `OutreachMessage`、append-only `OutreachMessageReview` 與 0082 migration；模式只有 `off`／`review_only`。
- 旅程 evidence pack：intent score／stage／facets、時間衰減與重複互動權重、已發布產品／頁面／比較、下載、CTA／表單／RFQ／chat 訊號、event IDs、knowledge references、policy／content version 與 TTL。
- 事件中的名稱、URL 或 payload 不作內容真值；每個 product／page／comparison ID 必須重新通過同 tenant、`published`、非 `noindex` 查核。已刪除、未發布、test data 與跨租戶項目不進證據包。
- `journey_summarize` → `outreach_draft` durable jobs；payload 只含 candidate／snapshot reference，不含 email、IP、visitor ID 或旅程明細。
- daily＋policy-version generation key、candidate row lock、job／snapshot replay guard，避免 worker commit 後重跑造成重複快照、草稿或成本。
- 收件人 email 只以 ciphertext／HMAC／mask 保存；API 與後台不回傳明文，並明示聯絡窗口不是匿名訪客本人。
- deterministic grounded template v1：只引用固定已發布知識快照，不需要外部 LLM；保存 subject／HTML／text、content hash、knowledge／prompt／policy／model version 與 personalization evidence。
- 硬內容規則：禁止價格、折扣、規格數值、交期、保證、認證、既有客戶關係、敏感追蹤識別與「我們看到你瀏覽」；禁止未驗證 URL；系統只附加一個 canonical reply CTA。
- HTML 由伺服器對純文字逐段 escape 產生，人工介面不能上傳任意 HTML。
- 草稿只進 `pending_review`；人工修改會建立新 revision 與 diff audit，不覆寫舊 subject／HTML／text；舊 pending revision 標為 `cancelled`。
- approve／reject append-only audit；approve 前重新檢查 latest revision、content hash、policy version、consent、company／candidate／recipient integrity、suppression、TTL、事件仍存在，以及知識仍為同 tenant 已發布且 content version 未改變。
- reject 不受失效證據 gate 阻擋，避免 stale draft 卡死在佇列；approve 不建立任何寄送 job。
- consent withdrawal 刪除 unsent snapshot／message 與兩段 outreach jobs；TTL purge 在寄送能力尚未存在的本批可刪除全部 unsent evidence。
- 平台後台 `/platform/outreach`：tenant policy、合格窗口 enqueue、evidence summary、masked recipient、versioned editor、approve／reject；明示「核准不寄送」，且沒有 send button。

### Code review 發現與修正

1. job 在 snapshot commit 後、outbox 標完成前重跑會重建證據：加入 `generation_key` unique constraint、candidate lock、既有 snapshot／job replay guard。
2. 原先人工正文可能自行加入第二個 CTA：正文拒絕 reply／call／book／contact／URL 等 CTA，唯一 canonical CTA 由伺服器附加並在 approve 時重驗。
3. 原先 approve 只驗 TTL：改為重查 consent、suppression、candidate verified／approved、relevance、confirmed company、recipient hash／domain、policy version、event existence、published status 與 content version。
4. 未發布或跨租戶事件雖不進 event ID，原 aggregate count 仍可能計入：count 移到 entity／signal 驗證之後，無效事件完全不進 journey signals。
5. 知識版本原以產生時間表示，不足以證明內容：改用 canonical knowledge-reference hash，並保存每筆 `updated_at` content version。
6. 內容 policy 原未涵蓋數值規格與認證杜撰：補 unit／percentage 與 certification／compliance patterns。
7. 證據過期時原連 reject 都被 approval gate 阻擋：只對 approve 套完整 current-evidence gate；reject 永遠可清理 pending queue。
8. 建立 revision 後舊 pending 仍顯示待審但不可操作：舊狀態改為 `cancelled`，內容快照保持不變。
9. PostgreSQL timestamp 可能為 timezone-aware，而應用 clock 為 naive：時間衰減前統一正規化，避免 runtime subtraction error。
10. knowledge version 加 hash 後超過原 VARCHAR(80)：migration／model 改為 100，並以真實 PostgreSQL 捕捉修正。

### 驗證

- Ruff：第四批 scoped backend／tests 全數通過。
- Admin：TypeScript type-check 與 ESLint 全數通過。
- API 路由只包含 policy、enqueue、list／detail、revision、review；程式驗證不存在任何 `/send` route，model 亦無 sent/provider-message 欄位。
- 隔離 PostgreSQL 16：空資料庫完整升級至 0082；0082 → 0081 → 0082 往返成功；單一 Alembic head。
- `alembic check` 仍偵測專案早期 migrations 的大量既有 metadata drift；過濾結果沒有 `journey_snapshots` 或 `outreach_*` drift。
- 第四批專屬整合測試：9 passed，涵蓋未發布／已刪除／跨 tenant 排除、加密／遮罩、job idempotency、唯一 CTA、不實主張、revision immutability、approve current-evidence gates、reject stale evidence、核准不寄送與 consent cascade。
- 第二至第四批相關整合組：46 passed。
- 全庫 DB 回歸：260 passed、2 skipped、10 個既有非第四批失敗；失敗集合與前批相同，仍為 adoption reserved email fixture、舊 feature entitlement／Copilot／Growth Ops／intent／platform/RFQ 測試契約，沒有 outreach failure。

### 本批 Gate 結論

- Review Only 程式 Gate 通過，可進入下一批開發。
- production policy 仍預設 `off`；A／B 外部資料權利與 blind POC 尚未通過，因此不可投入真實收件人。
- 本批沒有寄送能力；草稿 `approved` 只代表內容審核完成。

## 批次 5：受控寄送、追蹤、退訂與抑制

### 已實作

- `OutreachDeliveryPolicy` 與 0083 migration；runtime mode 只有 `off`／`approval_send`，provider 固定為具請求冪等能力的 Resend。全域 `EMAIL_EXTERNAL_DELIVERY_ENABLED` 與獨立 `OUTREACH_SEND_ENABLED` 均預設關閉。
- `OutreachMessage` 擴充 queued／sending／sent／delivered／opened／clicked／bounced／complained／unsubscribed／failed 狀態、send request、首次 provider attempt、重試次數、provider message ID、完整寄送快照、退訂 token hash、各事件時間與 `updated_at`。
- 寄送前在 tenant policy row lock 內重驗 feature entitlement、人工核准、latest revision、content hash、公司／窗口／email verification／TTL、consent、DNC、tenant／global suppression、quiet hours、租戶時區每日 quota、recipient frequency cap 與平台設定。
- `outreach_send` durable OperationalJob；排程與訊息共用 deterministic idempotency key。第一次 provider attempt 固定 `sending_at`，23 小時 Resend replay window 內 retry 重用完全相同的 subject／HTML／text／sender／headers／unsubscribe token 與 idempotency key。
- Provider 網路 I/O 前提交 immutable snapshot，不持有 DB lock；呼叫前再做一次 suppression、candidate 與 kill-switch 檢查。timeout／worker retry 不把未確認接受誤標為 sent，dry run 永不算外部送達。
- `EmailDeliveryEvent` 加入 tenant／OutreachMessage FK、reason、安全縮減後 event data 與 unknown-message 標記；Resend webhook 驗證原始 payload 的 Svix HMAC、timestamp、event replay，支援 out-of-order monotonic projection 與 provider-response／early-webhook 雙向 race reconciliation。
- Bounce／complaint／provider suppression 建立全域 suppression；簽名退訂 token 只含 message／tenant／email hash／scope／expiry，不含明文 email。GET 僅顯示確認頁，POST 才變更；tenant／global unsubscribe 立即取消同收件人的 queued jobs。
- `NurtureOutbox` 增加可選 `outreach_message_id`，防止未來整合時從可變 live step 重渲染已核准內容；本批北極星寄送主路徑直接由 `OutreachMessage` 快照發送。
- 管理後台加入 APPROVAL_SEND policy、平台 readiness、quiet hours／quota／frequency／unsubscribe scope、人工 send／cancel／retry 與 delivery event timeline；平台未完整設定時 UI 與 API 均阻擋寄送。
- 平台 readiness 必須同時具備兩個 kill switches、Resend API key、合法 public unsubscribe URL、至少 32 字元退訂 signing secret，以及有效的 Resend webhook signing secret；production public URL 強制 HTTPS。

### Code review 發現與修正

1. migration 從普通 index 改為 unique constraint 後，downgrade 仍刪舊 index：修正 0083 的 upgrade／downgrade 對稱性，並從空 PostgreSQL 完整往返。
2. `EmailDeliveryEvent.provider_event_id` ORM 原把「unique constraint＋普通 index」表達成 unique index：改為具名 constraint 加普通 index，消除本批 metadata drift。
3. readiness 原未要求 webhook signing secret，可能能寄信卻不能可信接收 delivered／complaint／suppression：將有效 Svix secret 納入 UI、queue endpoint 與 worker preflight fail-closed gate。
4. 計畫要求的 `OutreachMessage.updated_at` 原缺漏：補 migration、model、API type，所有 review／revision／queue／retry／cancel／send／event／unsubscribe 狀態變更同步更新。
5. quota 原以 UTC 日計算：改為 tenant IANA timezone 當地日；quiet hours 亦依相同時區計算下一個可寄時間。
6. 多 worker 可能同時越過 quota／frequency：鎖定 tenant delivery policy，將 `sending_at` 視為 reservation 並排除當前 retry。
7. 原本以 queue time 控制 Resend replay window，可能過早失效或 retry 產生新 token／sender：改由首次 provider attempt 起算，並持久化、重用完整 provider payload。
8. Webhook 可能在 provider response 寫回 message ID 前先到：保留 unknown event，provider response 與 webhook commit 後都執行 reconciliation，任一交易後完成都可收斂。
9. Provider response 原可能把已由 webhook 標為 complaint／unsubscribe 的 terminal 狀態降回 sent：採 monotonic event projection，終止狀態不得降級。
10. suppression 取消訊息後，對應 OperationalJob 原可能仍 pending；現在同步標 failed。`outreach_send` 也移出泛用 feature-skip 路徑，由寄送 runtime 自己 fail closed，避免 job completed 但 message 永遠卡 queued。
11. 前置檢查原可能把不明 DB 例外誤判 permanent failure：只捕捉已知 policy／content 錯誤；transient failure 交由 durable retry。
12. 寄送前最後一道 mutable gate 原與 provider 呼叫間隔過大：在 provider I/O 正前方重新檢查 suppression、candidate eligibility 與 kill switches。

### 驗證

- Ruff：第五批 scoped backend／tests 全數通過。
- Admin：Prettier、TypeScript type-check 與 ESLint 全數通過。
- 隔離 PostgreSQL 16：空資料庫完整升級至 0083；0083 → 0082 → 0083 往返成功；單一 Alembic head。
- `alembic check` 對 `outreach_delivery_policies`、`outreach_messages`、`email_delivery_events` 無第五批 metadata drift；專案較早 migrations 的既有全域 drift 仍保留至最終治理批次。
- 第二至第五批相關 PostgreSQL 整合組：57 passed；包含真正 DB locking／FK／unique 行為、人工核准、雙重 queue、provider timeout＋相同 payload retry、early webhook race、signature／replay／out-of-order、unknown message、one-click unsubscribe 與 suppression cascade。
- 完整 API PostgreSQL 回歸：266 passed、2 skipped、10 個既有非第五批失敗；失敗集合與前批相同，沒有 outreach／delivery／webhook failure。
- Code review 使用的 provider 行為依官方文件確認：Resend custom headers、24 小時 idempotency 與 one-click unsubscribe；因此本階段不把缺乏等效 request-idempotency 保證的 SendGrid 宣稱為 APPROVAL_SEND exactly-once provider。

### 本批 Gate 結論

- `APPROVAL_SEND` 程式 Gate 與 code review 通過，可以進入 Inbound Reply／Sales Handoff 開發。
- production 全域與 tenant policy 仍預設 `off`；A／B 外部資料權利、真實 verified recipient 與送達／bounce／complaint／unsubscribe 指標尚未通過，不得對真實名單啟用。
- `CONTROLLED_AUTO` 仍不存在且不得啟用。

## 批次 6：Inbound reply、真人業務接手與 RFQ

### 已實作

- 新增 `InboundReplyPolicy`、`InboundReply`、`SalesHandoff`、`SalesHandoffEvent` 與 0084 migration；回覆內容具保存期限與遮蔽時間，附件只保存最小化 metadata 並一律 quarantine，不保存可直接下載的外部 URL。
- 每封已寄外聯固定一個 HMAC 簽名 Reply-To route；inbound receipt 必須同時通過 provider webhook 驗證、route signature、資料庫中已寄 route 綁定及 tenant ownership，不能只靠可偽造的 mail headers 關聯。
- Resend Receiving adapter 以 bounded streaming 取得信件；區分 retryable 與 permanent provider errors，驗證 provider email identity，並由 durable `inbound_reply_fetch` job 執行、記錄與人工重開失敗工作。
- 回覆正文先將 HTML 正規化為安全純文字、移除控制字元並限制大小；規則式多語分類涵蓋 positive、question、RFQ、not-now、wrong-person、unsubscribe、negative、auto-reply，且 unsubscribe／auto-reply 等安全優先級不受其他字詞覆蓋。
- unsubscribe 回覆即時建立 suppression 並取消同地址所有 queued outreach；positive／question／RFQ 可自動建立具 owner、SLA 與歷程的 `SalesHandoff`，分類不明則保留人工 review。
- 真人業務可接受、改派、開始、標記已聯絡、錯誤窗口、退訂、結案、關聯既有 RFQ，或經人工確認一鍵轉成 `RFQRequest`；轉換具 advisory lock、去重與 idempotency，不虛構 consent，也不把轉寄者誤認成原候選人。
- 管理後台新增買家回信與接手工作台：回信列表、thread、原始外聯／公司／窗口／旅程證據、附件 quarantine 提示、SLA、owner、分類與 RFQ 操作。Marketing 僅能讀取遮罩資訊，不能看到明文 mailto 或執行接手動作。
- Worker maintenance 會依 policy 遮蔽逾期正文，並把超過期限的 handoff 持久標記為 SLA breached；平台另有未關聯回覆佇列及人工 tenant/message link 入口。
- 全域 inbound kill switch、tenant policy 與 feature entitlement 預設不自動啟用；寄送 preflight 在 tenant 開啟 inbound policy 時要求 Reply-To domain／secret 完整，避免寄出後無法可信接收回覆。

### Code review 發現與修正

1. 人工把回覆分類為 unsubscribe 原只更新分類：補上 suppression 與 queued send cancellation，所有入口行為一致。
2. suppression scope 原硬編碼：改依 tenant delivery policy 決定 tenant／global scope。
3. RFQ 轉換 retry 可能重複寫 operational event：以既有 handoff／RFQ 關聯做 idempotent return，並以 tenant advisory lock 配發 RFQ number。
4. 已結案 handoff 原仍能建立 RFQ：改為 fail closed；關聯與轉換都需要可處理狀態及人工角色。
5. Provider response 原可能無上限 buffer：改為逐 chunk bounded streaming，超限立即 permanent reject。
6. 原只有 retention 欄位、沒有實際清除：加入 maintenance redaction，主旨／正文／preview 到期後不可回復地遮蔽並保存稽核時間。
7. SLA 原只在讀取時計算：加入持久 `breached_at` 與 maintenance scan，支援營運查詢與告警。
8. 轉寄回覆原可能沿用原候選人身份：sender 不一致時保留原外聯證據，但 RFQ contact 不繼承原 candidate/contact。
9. route token 原只驗簽未比對寄送時固化值：補 `sent_reply_to`／`reply_route_token_hash`，防止另一個合法 token 被移用。
10. message-id／references fallback 原可能跨 tenant 命中：所有 thread fallback 加 tenant 邊界；platform manual link 另走明確稽核入口。
11. 全域 kill switch 關閉時原仍保存 receipt：改為 webhook 驗證後回覆 ignored，不寫 inbound domain data、不排工作。
12. Marketing UI 原仍可能出現操作或明文地址：API 與 UI 同步為 read-only、遮罩寄件者，外部 mailto 只供 owner／admin／sales。
13. Provider permanent failure 原會讓 reply 長期停在 processing，且 notification failure 可能拖累核心交易：前者明確標 failed 並可人工 retry，後者隔離記錄、不反覆重跑已完成的接手交易。
14. 回覆狀態投影原未把 replied 放入 monotonic rank，event detail 含 UUID 也可能無法 JSON 化：補狀態順序與安全序列化。
15. migration 與 ORM 的附件總位元組型別不一致：統一為 `BigInteger`，消除第六批 metadata drift。

### 驗證

- Ruff：第六批 scoped backend／tests 全數通過。
- Admin：TypeScript type-check 與 ESLint 全數通過。
- 隔離 PostgreSQL 16：0084 → 0083 → 0084 往返成功，最後位於單一 0084 head。
- `alembic check` 仍有專案早期 migrations／已退場 model 的全域既有 drift；過濾後沒有 `inbound_replies`、`inbound_reply_policies`、`sales_handoffs`、`sales_handoff_events`、Reply-To 欄位或 attachment byte 欄位的第六批 drift。
- 第六批與 feature focused regression：15 passed；第四至第六批相關 regression：29 passed。
- 完整 API PostgreSQL 回歸：280 passed、2 skipped、10 個既有非第六批失敗；失敗集合與第五批相同，沒有 inbound reply／handoff／RFQ conversion 新回歸。
- 測試涵蓋 route tamper、重複 receipt、sender mismatch、跨 tenant isolation、惡意 HTML、附件 quarantine、bounded provider payload、kill switch、多語分類、unsubscribe cascade、handoff／RFQ idempotency、內容遮蔽與人工 retry。

### 本批 Gate 結論

- Inbound Reply／Sales Handoff 程式 Gate 與 code review 通過，可進入閉環歸因與成果漏斗批次。
- Production 收信仍需正式 Resend Receiving domain、簽名 secret、DNS／轉寄設定與真實 mailbox 測試；程式完成不代表外部環境 Gate 已通過。
- 自動分類只用於安全停止與建立待人工處理工作，不代表系統可代替真人對買家回信。

## 批次 7：閉環歸因、成果漏斗與 Controlled Auto Gate

### 已實作

- 新增 `AttributionLink`、append-only `AttributionEvent` 與 0085 migration，穩定串聯 visitor、company identification、contact candidate、contact、journey snapshot、outreach、reply、handoff 與 RFQ。
- 歸因規則只接受資料庫內同 tenant 的可驗證鏈：由 reviewed reply handoff 建立的新 RFQ 為 `direct`；真人將既有 RFQ 關聯至 handoff 為 `assisted`；缺少因果鏈為 `unknown`。禁止以 email 相似或來源頁猜測直接歸因。
- 每次自動推導、重算、人工覆寫與 RFQ outcome 變更均保存決策、前值、信心、證據、actor 與時間；人工覆寫不會被後續 rebuild 覆蓋。
- 公開 RFQ 建立時即產生 deterministic unknown lineage；handoff 建立／關聯 RFQ 時更新 direct／assisted；RFQ 狀態、成交金額與幣別變更寫入 outcome audit。
- 新增 tenant-scoped North Star funnel、provider cost、品質分母／分子、CSV、單筆 RFQ lineage 與批次 rebuild API；舊 RFQ 尚未建立 link 時仍納入 `unknown`，不會從成果報表消失。
- Funnel 以觀察期間首次出現的 visitor cohort 計算 13 層：tracked、intent、company、high-confidence company、qualified contact、approved、sent、delivered、replied、positive reply、handoff、RFQ、won。
- Admin outcomes 頁顯示漏斗、drop-off、歸因數量／成交金額、品質分子分母與 Controlled Auto blockers；RFQ 詳情顯示完整 lineage 及 append-only decision history。
- Controlled Auto 只提供 evidence readiness 評估：tenant 明確 opt-in、法遵核准、region／persona／template allowlist、公司 precision、窗口 relevance、送達樣本、零不實主張、bounce／complaint／unsubscribe、核准量與修改率都必須通過。runtime 的 `activation_available` 固定為 false，寄送模式仍只有 `off`／`approval_send`。

### Code review 發現與修正

1. RFQ attribution GET 原會為舊資料偷偷建立 link 並 commit，違反唯讀語意：改為 404 提示執行明確 rebuild，GET 不再改變狀態。
2. 成果報表原只 inner join 已有 attribution link，legacy RFQ 會消失：改用 tenant-scoped outer join，未建 link 的 RFQ 合併計入 `unknown`。
3. rebuild 原每次只處理最早一批，超過 limit 無法前進：加入 `offset`、`next_offset`、`total`、`has_more`，可完整分頁且重跑不產生重複事件。
4. 自動 derive 原可能每次查詢都新增 recalculated event：完整比較類型、信心、證據與 lineage，未改變時 idempotent return。
5. direct rebuild 原可能依 `source_page` 猜測：改查 `SalesHandoffEvent.created_rfq` 的確切事件；無明確事件最多只能 assisted。
6. 人工可把 unknown 任意改成 direct／assisted：direct 必須已有可驗證 direct chain，assisted 必須已有 handoff，否則 fail closed。
7. 成交金額原可能把非 won RFQ 金額計入：以 conditional sum 只彙總 `status=won`。
8. 公司 precision 原分母可能包含低信心辨識：改為 review 與 high-confidence company identification 的交集。
9. 0% bounce／complaint／unsubscribe 原因 Python truthiness 可能被誤算成 100%：只在 rate 為 `None` 時套 fallback，真實 0 保留。
10. SLA 原只看是否存在 `accepted_at`：改為 `accepted_at <= sla_due_at` 且未 breach 才算達標。

### 驗證

- 第七批新檔 Ruff 全數通過；相關 legacy 檔案 F 規則與 Python compileall 通過。
- Admin TypeScript type-check 與 ESLint 全數通過。
- 隔離 PostgreSQL 16：0085 → 0084 → 0085 往返成功，最後位於單一 0085 head。
- 第七批專屬整合測試 3 passed；第四至第七批及 feature entitlement 交叉回歸 34 passed。
- 完整 API PostgreSQL 回歸：283 passed、2 skipped、10 個既有失敗；失敗集合與第六批相同，沒有 attribution／funnel／Controlled Auto 新回歸。
- 全庫 `alembic check` 仍有歷史 metadata drift；0085 schema 另以 migration 往返與 PostgreSQL catalog 精準核對。

### 本批 Gate 結論

- Closed-loop attribution 與成果漏斗程式 Gate、code review 通過，可進入類別四 telemetry／依賴稽核與安全退場批次。
- Controlled Auto 僅完成評估 Gate，沒有可啟用 runtime；未取得供應商資料權利、法遵核准及真實 30 天品質樣本前，仍只能逐封人工核准寄送。

## 批次 8：類別四 telemetry、依賴稽核與安全退場

### 已實作

- 新增 `RetirementCandidateObservation`、PII-minimal `RetirementUsageEvent` 與 0086 migration，建立候選狀態、觀察期間、使用事件、人工決策與理由的可稽核資料基礎。
- 新增 superuser-only 退場稽核 API 與 `/platform/retirement` 平台頁，整合實際使用、租戶設定依賴、觀察進度、blocker 與人工保留／核准移除決策。
- 移除 phase2 對 ML scoring 的預設開啟；新增獨立 `ai_relation_recommendations` entitlement，預設關閉；ML 與 relation 只有明確 override 後才可使用並留下最小 usage signal。
- AgentOS `automation_runs` 維持 locked off、URL 預設空白，tenantless job 也 fail closed；保留歷史 RFQ 欄位、migration 與可回復 writeback 路徑。
- Telegram／LINE 保持營運，但任何 enabled preference 或 delivery log 都會阻擋移除；通知核心不列為退場候選。
- 靜態確認無 import、route、bundle、job 或資料依賴後，刪除重複且未掛載的 `CopilotFloatingWidget`；保留 `/dashboard/copilot` 專屬頁。
- 刪除無 caller、使用不安全 HTTP fallback、以 ISP `org` 猜測公司名稱的舊 `ip_resolver.py`；正式 `NetworkObservation`／provider 架構不受影響。
- 建立 `FORGEBASE_CATEGORY4_RETIREMENT_AUDIT_2026-08-27.md`，逐項記錄入口、依賴、資料處置、觀察 Gate、刪除順序與回復方式。

### Code review 發現與修正

1. usage ledger 原保存 actor UUID，與「只量測是否使用」目的不相稱：移除欄位，migration、ORM、service 與測試同步改為不保存操作人識別資訊。
2. 通知渠道原只看 delivery log，可能把已設定但近期沒有寄送的租戶誤判為零使用：enabled preference 納入 configured dependency blocker。
3. AgentOS tenantless job 原保有 legacy bypass：改為 tenantless 一律不能通過 locked feature；預設 URL 由 localhost 改為空白。
4. 舊 AgentOS 測試仍假設自動觸發：改測鎖定狀態不觸發；另以明確測試 URL 驗證 dormant writeback 仍可回復，不用刪除歷史能力證明停用。
5. 候選 tenant 數來自 telemetry 與 domain signal 的保守最大值，不宣稱是兩集合精確 union；UI 明示為「至少」以避免錯誤精度。
6. `removed` 狀態設為不可逆，真正刪除必須另開獨立變更集；避免單次 API 操作跳過 forward migration、備份及部署回復窗口。
7. 使用事件記錄採 fail-closed：若無法可靠保存採用訊號，候選功能請求不成功，避免因 telemetry 缺口產生錯誤的零使用結論。

### 驗證

- 第八批新檔 Ruff 全數通過；相關 Python app compileall 通過。
- Admin TypeScript type-check 與 ESLint 通過。
- Web TypeScript type-check 通過；ESLint 0 error，僅 `web/src/lib/messages.ts` 一個既有 unused warning。
- 隔離 PostgreSQL 16：0086 → 0085 → 0086 往返成功；catalog 精準確認兩張退場表、PII-minimal usage 欄位與六個觀察候選 seed。
- 第八批 focused regression：4 passed；相關 feature／AgentOS／relation 交叉回歸：22 passed、2 skipped。
- 完整 API PostgreSQL 回歸：286 passed、3 skipped、10 個既有失敗；失敗集合與第七批完全相同，沒有退場稽核、feature lock、AgentOS 或 relation 新回歸。
- 靜態掃描確認已刪項目沒有殘留非文件引用；`git diff --check` 沒有 whitespace error。

### 本批 Gate 結論

- 類別四的程式治理、依賴稽核、最小 telemetry、安全刪除與 code review 已完成；其後再由單一產品、後台 IA、多語與最終收斂批次完成全案。
- 可立即安全刪除的兩項 dead／unsafe code 已移除；AgentOS、ML scoring runtime、Telegram、LINE 與 relation recommender 尚未滿足 production 30／60 天觀察期，因此沒有刪除其歷史資料、migration 或可回復程式。
- production migration 部署日才是觀察起點；只有 telemetry 全期無缺口、零使用、零設定依賴且人工簽核後，才能另案執行下一次實際移除。

## 批次 9：結構完整性與單一產品能力治理

### 已實作

- 補齊 Alembic metadata 所需的 model exports，讓仍在使用的 Copilot conversation、notification 與 redirect tables 不再被誤判為待刪除。
- 將身份關聯統一為 `Visitor.contact_id → Contact.id`；移除反向 `Contact.visitor_id` 循環欄位，支援多個匿名裝置／訪客歸戶至同一聯絡人，並保留 API 相容 alias。
- 新增 0087 migration，先回填不衝突的舊關聯，再移除循環 FK；downgrade 可依首次出現時間選出單一舊 visitor link。
- 移除 tenant 的 `plan`、`product_stage`、產品／管理員 quota 及 PayPal 欄位、設定、服務與 API；新增 0088 migration。
- 將 `subscription.py`、`PlanProvider`、`PlanGate` 等舊語意重構為 `capability_access.py`、`CapabilityProvider` 與 `CapabilityGate`；能力治理只表示成熟度、外部依賴與營運安全，不再表示付費分級。
- 固定核心及成熟能力預設開啟；建置中、pilot、等待 provider、服務依賴與退場觀察能力預設關閉，且不可藉由 crafted override 打開不可配置能力。
- 移除 Admin billing／pricing routes、demo login route、硬編碼示範帳密與相關環境設定；登入只保留正式驗證流程。
- 平台 dashboard 的 RFQ／visitor 指標只計算已歸屬租戶且非測試資料；另列 legacy unassigned backlog，避免全域資料污染正式 KPI。
- 平台既有租戶建立 site build 時會補齊最低可用 `SiteProfile`，並修正跨時區日期排序例外。
- 修正既有測試資料的無效保留網域 email、RFQ email mock 介面與 capability 測試假設；十個既有失敗全數清除。

### Code review 發現與修正

1. 單純移除 `Contact.visitor_id` 會讓 Contact API 失去旅程入口：改為批次查詢 `Visitor.contact_id`，回傳完整 `visitor_ids` 及相容 `visitor_id`。
2. 公開 contact／RFQ 寫入若不驗證 visitor tenant，可能形成跨租戶關聯：所有寫入先檢查 tenant ownership，再建立 visitor → contact link。
3. Sidebar 在 capability 載入時原會暫時隱藏所有受治理入口：改為載入期 optimistic 顯示，完成後才依實際權限裁切；API 仍 fail closed。
4. 第一輪清理只改 UI 文案仍殘留 subscription、plan hook、billing route 與 PayPal config：連同檔名、imports、route、service、tenant schema、provision script 與 README 一併移除。
5. 平台全域 RFQ／visitor 聚合原包含 tenantless legacy rows：正式 KPI 改為只計有效租戶資料，legacy backlog 另行透明揭露，不靜默刪除。
6. migration review 確認 0087／0088 都具可執行 downgrade；以 PostgreSQL 由 0088 降至 0086 再升回 0088 驗證，最後維持單一 head。

### 驗證

- 完整 API PostgreSQL 回歸：**296 passed、3 skipped、0 failed**。
- 前兩批重點整合測試：13 passed；identity 與 capability 專屬測試：4 passed。
- Admin：TypeScript type-check 與 ESLint 通過。
- Web：TypeScript type-check 通過；ESLint 0 error，保留一個既有 unused warning待最終技術債批次清除。
- 新增／重構 Python 檔案的 Ruff `F`／`E9`／`I` 規則通過；全庫較舊 FastAPI `Depends` 與 annotation 風格警告不冒充本批回歸。
- 0087／0088 PostgreSQL downgrade／upgrade 往返成功；`git diff --check` 無 whitespace error。
- `Connection._cancel was never awaited` 的 asyncpg 測試 teardown warning 與全域 Alembic metadata drift 仍列入最終技術債批次，未宣稱已清除。

### 本批 Gate 結論

- 結構完整性與單一產品能力治理 code review 通過，可進入後台導覽與 UIUX 重構。
- 產品不再有 Starter／Professional 或第一／第二階段方案；Capability Gate 僅用於外部依賴、試行安全、建置狀態與退場觀察。
- ML scoring、公司辨識、聯絡人補全與受控外聯仍依北極星分類保留；其中外部資料權利與真實品質 Gate 未通過者維持關閉，並非刪除候選。

## 批次 10：後台導覽與工作中心 UIUX

### 已實作

- 租戶後台側欄由約 30 個模組入口收斂為 11 個日常入口，分成「核心工作、官網營運、帳號與支援」三組。
- 新增「買家管線」工作中心，直接呈現匿名訪客 → 追蹤 → 意圖 → 公司 → 窗口 → 個人化信件 → 寄送 → 回覆 → 接手 → RFQ／成交；各節點依 capability 顯示「運作中／受控中」。
- 新增「內容中心」，集中商品、分類、頁面、網站文案、素材、應用、FAQ、認證、廠能、比較內容與 SEO 轉址。
- 新增「成長工具」，集中內容成效、分群、CTA、培育郵件、AI 業務助理、進階評分、ML 與外部服務；未啟用能力不製造升級牆或付費提示。
- 每日總覽的快速入口同步改指向買家管線、內容中心、待辦與通知，降低使用者在模組名稱間尋路的成本。
- Hub 卡片同時套用角色與 capability 可見性；實際 route 仍由既有 `RouteGuard`／`FeatureAccessGuard` 強制執行，不能藉直接網址繞過。
- 保留平台營運方的公司推測、聯絡窗口與外聯審核專屬頁；租戶端只看可信流程狀態，不接觸 provider 設定或未遮罩候選資料。

### Code review 發現與修正

1. 初版精簡側欄時，網站文案與圖片入口只存在舊深層 route：補入內容中心，避免精簡導覽造成實際功能不可發現。
2. Capability 載入中的 hub 若立即裁切會產生卡片閃爍：載入期保持穩定，資料完成後才移除未啟用項目；API 與 route guard 仍 fail closed。
3. Hub 隱藏角色不符卡片不能取代授權：確認並保留 `/dashboard/growth` 及各深層 route 的角色檢查，Sales 直接輸入網址仍為 403。
4. 北極星流程若只顯示目前可操作項，會再次把公司辨識／窗口／外聯誤分類為非核心：流程節點完整保留，以「受控中」表達品質或外部 Gate。
5. 本機 3001 已由其他專案占用，瀏覽器檢查改用獨立埠並遵循 Admin `basePath=/backend`；未把其他專案畫面誤判為 ForgeBase 驗收結果。

### 驗證

- Admin TypeScript type-check、ESLint 與 production build 全數通過。
- Production build 成功產生 73 個頁面，確認新增 `/dashboard/buyers`、`/dashboard/content`、`/dashboard/growth` routes。
- 本機瀏覽器確認受保護 route 正確導向 `/backend/login`、頁面無 console error，且 demo login backdoor 不存在；未使用真實或既有帳號繞過驗證。
- 側欄靜態入口 11 個；所有被收納的深層 route 仍存在於 build route manifest。
- 全 Admin 原始碼無 Starter／Professional、第一／第二階段、billing、PlanGate、PlanProvider 或 usePlan 殘留。
- `git diff --check` 無 whitespace error。

### 本批 Gate 結論

- 後台 IA／UIUX 重構與 code review 通過，可進入可配置多語系與批次審核批次。
- 這次精簡是把低頻功能收進工作中心，不是刪除應保留能力；安全退場候選仍依 telemetry 與 30／60 天 Gate 處置。

## 批次 11：可配置內容語系與批次草稿審核

### 已實作

- 將 CMS 內容語系目錄由英文／繁中擴充為英文、繁中、日文、法文與俄文；AI 客服回覆語言仍獨立支援更廣泛的訪客語言，不受網站語系目錄限制。
- 明確拆分「內容草稿語系」與「完整公開網站介面語系包」：目前完整介面包仍為英文／繁中，日／法／俄可產內容草稿與審核，但介面包完成前不宣稱整站已完整在地化。
- 翻譯草稿服務改用共用語系目錄驗證與標籤，維持不覆寫已發布內容、不自動發布、保留規格／數值／網址且禁止捏造主張的政策。
- 新增 tenant-scoped `locale-settings` 與任意支援目標語系的 coverage API；覆蓋率包含完整 missing 分母、草稿、已發布與來源更新後過期數。
- 新增每次最多 25 筆的批次草稿 API，逐筆回傳成功／失敗，部分失敗不掩蓋已完成項目，且固定回報自動發布 0 筆。
- 新增「內容中心 → 多語內容」工作中心，可切換目標語系、查看覆蓋率與缺漏、批次建立缺少草稿，再回到原內容頁逐筆審核發布。
- 各內容編輯表單與語系切換器可建立日／法／俄草稿，並呈現 missing／draft／stale／ready 狀態。

### Code review 發現與修正

1. 初版 coverage 的 missing 總數使用最多 100 筆的樣本陣列，內容超過 100 筆時會少算：改以完整 `source_total - translated` 計算，樣本陣列只作 UI 摘要。
2. 原單筆草稿 API 只檢查 capability，Sales 若直接呼叫 API 仍可能建立草稿：單筆、批次、settings 與 coverage 均新增內容編輯角色 Gate；Admin route 同步阻擋 Sales。
3. 批次中的非預期 DB／服務錯誤可能留下失敗 transaction：逐筆失敗先 rollback，保留先前已 commit 的成功草稿並回傳明確失敗項。
4. 多語工作中心的 target state 原會造成初次載入後再發一次重複請求：移除 callback 對 target state 的依賴，改由呼叫端明確傳入目標語系。
5. 「可產內容草稿」若直接等同「整站公開語系已就緒」會形成產品誤導：API 與 UI 均顯示 `public_shell_ready`，日／法／俄目前清楚標示介面包待交付。

### 驗證

- 多語草稿與 AI 客服語言專屬測試：26 passed。
- 全 API 回歸：298 passed、3 skipped、0 failed。
- Admin TypeScript、ESLint 與 production build 通過；build 成功產生 `/dashboard/content/locales`，總頁面數 74。
- 本批 Python scoped Ruff 通過，`git diff --check` 無 whitespace error。
- 全回歸仍可觀察到既有 asyncpg `Connection._cancel was never awaited` teardown warning；保留至最終技術債批次處理，未當作已清除。

### 本批 Gate 結論

- 可配置內容語系與批次草稿審核的程式 Gate、code review 與完整回歸通過，可進入最終 operational jobs、依賴／文件一致性與技術債收斂批次。

## 批次 12：最終架構、schema、依賴、安全與技術債收斂

### 已實作

- 所有 North Star operational jobs 在 worker 執行前再次檢查對應 capability；即使舊 job 已排入佇列，能力被關閉後也不能繞過公司辨識、窗口補全、旅程個人化、草稿審核、寄送或回覆 Gate。
- 測試資料庫改用 `NullPool`，rate-limit fixture 改由正式 async driver 清除共享資料，清除跨 event loop 的 asyncpg teardown 警告與無同步 PostgreSQL driver 時的隱性 flake。
- 新增 `verify_schema_contract.py` 並接入 API CI，核對 code head／DB head、North Star 關鍵表、欄位、FK `ON DELETE` 與唯一索引，避免只看測試與版本號。
- 全面校準 ORM metadata 與 migration schema：補正既有 FK 行為、命名 constraint、唯一／非唯一／partial／GIN 索引、nullable 與 generated TSVECTOR 定義；`alembic check` 已無結構漂移。
- 新增 0089 migration，將退場觀察的無時區 timestamp server default 統一成 UTC，並只修復不可能成立的未來觀察起點，保留合法歷史紀錄。
- 應用程式與測試的 SQLModel async 查詢全部由已棄用的 `execute()` 遷移至 `exec()`；位置參數與 scalar result 語意一併靜態核對。
- API Docker build 新增 `.dockerignore`，排除 `.env`、快取、coverage 與虛擬環境；重建後直接驗證映像內不存在 `.env`，且 `pip check` 無破損依賴。
- Admin／Web 的 npm lockfile 更新至非破壞性修補版本，最新 audit 由各 4 個 high 收斂為 0；未使用 `--force` 或跨 major 更新。
- Admin／Web 明確設定 Turbopack workspace root，移除錯誤向上尋找使用者目錄 lockfile 的建置警告。
- 後台 hub 深層頁面補上 active-prefix 導覽狀態；買家、內容、成長與 RFQ 的子頁都會保持正確主選單高亮。
- README、服務帳號腳本、CI、營運 outbox、UI copy scanner 路由及單一產品文案同步更新；移除 live code 的 Phase 1／2 採用敘述，歷史 migration 名稱保留為不可任意改寫的資料庫歷史。

### Code review 發現與修正

1. 初次完整測試只設 Pydantic `DATABASE_URL`、未設 process env，migration fixture 會誤判為無 DB：最終驗證明確注入同一 URL，先 upgrade／contract check 再跑所有 DB 測試。
2. 本機 DB 位於 0077，而先前驗證環境已在 0088；版本不一致會讓模型查詢誤報缺欄：按正式 migration 升至 head，契約檢查準確攔出並確認所有 North Star 表與 FK。
3. 退場觀察 seed 使用資料庫本地 `NOW()`，但 runtime 事件使用 naive UTC；Asia/Taipei 會讓起點比事件晚 8 小時：0089 改為 `TIMEZONE('utc', NOW())` 並加入既有資料修復。
4. ORM 曾長期缺少多個 migration 已建立的 constraint／index 定義：逐表對照實際 PostgreSQL catalog 後補齊，不以關閉 autogenerate 或維護 ignore list 掩蓋 drift。
5. Docker `COPY . .` 曾把 API `.env` 放入本機映像：新增 build-context 排除並以容器內檔案斷言驗證；舊 image ID 已不再可執行，但 BuildKit cache 不做可能影響其他專案的全域 prune。若主機共用、舊映像曾外推或密鑰可能外洩，仍必須另行清 cache 並輪替密鑰。
6. 前端 audit 在最終日取得新 advisory 後出現 4 high：以 lockfile 相容更新修補並重跑 type-check、lint、build、audit；兩個 workspace 均為 0 vulnerability。
7. Web production build 在 API 未啟動時會記錄連線失敗，但依設計使用空內容 fallback 且 build 成功；正式部署仍須以健康 API 完成 deployment smoke test，不能把離線 fallback 當成端到端驗收。
8. 剩餘 Python warnings 來自鎖定相依套件內部：本機 Starlette 422 常數 4 次、Python 3.12 容器的 `python-jose` `utcnow()`；ForgeBase app／tests 自身的 SQLModel 與 datetime 棄用警告已清零。

### 最終驗證

- 本機完整 API PostgreSQL 回歸：**298 passed、3 skipped、0 failed**；`RuntimeWarning` 設為 error，僅 4 次 Starlette 相依套件棄用提醒。
- 鎖定 Python 3.12 Docker 映像完整 API 回歸：**298 passed、3 skipped、0 failed**；`pip check` 通過，映像內 `.env` 不存在。
- Alembic 單一 head：`0089_retirement_timestamps_utc`；0089 → 0088 → 0089 往返成功；`alembic check` 回報 `No new upgrade operations detected`；North Star schema contract 通過。
- Admin：type-check、ESLint、production build 全通過，74 routes；npm audit 0 vulnerability。
- Web：type-check、ESLint、production build 全通過；npm audit 0 vulnerability；API 離線時 fallback 路徑如設計運作。
- Python compileall、Ruff fatal rules、`git diff --check`、刪除符號掃描與單一產品 runtime copy 掃描通過；已刪 PayPal／subscription／billing／pricing／demo login／PlanGate／usePlan／舊 IP resolver／重複 Copilot widget 均無 live-code caller。

### 本批 Gate 結論

- 已知程式結構、migration drift、測試 teardown、應用層棄用介面、Docker secret 包裝及已公告前端 high vulnerability 均已收斂；目前沒有已知會阻斷北極星流程的內部結構技術債。
- 不能據此宣稱所有 production 營運條件已完成：外部資料合約與真實 precision、正式 ESP／DNS／mailbox、送達與投訴品質、法遵核准、真實 deployment smoke test，以及非核心候選 30／60 天觀察仍須取得外部證據。
- 上述外部 Gate 持續 fail closed；它們不是第二套產品方案，也不是可用付費升級繞過的限制。

## 批次 13：登入後後台 UIUX 與瀏覽器驗收

### 驗收方式與範圍

- 以一次性本機 QA Owner 帳號實際完成登入，不再只檢查未登入 redirect 或靜態 build manifest。
- 逐一開啟 50 個已知後台 route，涵蓋 11 個日常側欄入口、工作中心、深層管理頁、設定頁與所有新增表單；全部具有正確頁面標題，無 404、空白頁或桌面版橫向溢位。
- 由清單頁實際取得資料連結，驗收訪客旅程、AI 客服對話與商品編輯三種既有動態明細；另建立具 `is_test_data`／`test_run_id` 標記的一次性本機 RFQ 與 Contact，補驗 RFQ 動態案件頁的公司、聯絡人、案件階段、備註、歷程、品質分數與貿易條件，驗收後精確刪除。
- 以 390 × 844 viewport 驗收每日總覽、買家管線、詢價案件、RFQ 動態明細、內容中心與網站支援；功能選單可展開三個導覽群組，以實際點擊進入內容中心後會自動收合，所有受測頁面均無橫向溢位。
- 實際操作詢價案件的階段篩選與搜尋欄位；未執行寄信、邀請、儲存內容、改設定或其他會改變營運資料的動作。
- 另開乾淨瀏覽器頁籤重新登入，依正常等待節奏重跑儀表板、多語內容、訪客旅程、對話明細、商品編輯與支援頁；browser console 為 0 error、0 warning。

### 驗收發現與修正

1. 「網站修改與支援」在未設定環境變數時會顯示個人 Gmail：改為產品官方 `hello@forgebase.co`，並在 `.env.local.example` 明列 `NEXT_PUBLIC_SUPPORT_EMAIL`。
2. Next.js 16 偵測全域 smooth scroll 時會產生 route transition warning：依框架規範在根 `<html>` 加入 `data-scroll-behavior="smooth"`；乾淨頁籤重測後警告消失。
3. 以 0.9 秒連續切換 50 頁的壓力式巡檢曾看到少量 `Failed to fetch`；逐頁等待 3.5 至 5 秒、全新頁籤及直接 API 重測均正常，確認為切頁取消中的開發模式請求，不是穩定可重現的頁面或 API 故障。
4. 後台精簡導覽符合單一產品定位：日常入口維持 11 個，低頻功能收納於內容中心／成長工具，北極星核心步驟仍完整呈現在買家管線，沒有重新引入方案分級。

### 正式環境唯讀預檢

- `https://pcbrm.tw/health/ready` 回傳 200，database、migration、storage、scheduler 均為 `ok`；正式首頁與 `/backend/login` 也回傳 200，頁面標題分別為 ForgeBase 產品官網與 ForgeBase 管理後台。
- 內建瀏覽器連線正式網域被 client policy 阻擋，因此本輪只能完成 HTTP／HTML 唯讀健康檢查，未把它冒充為正式環境視覺或登入驗收。
- 發布前盤點時，GitHub `deploy.yml` 會在 `main` push 後自動部署；遠端 `main` 與當時已部署成功的 commit 都仍是 `9273c301d2406518006499f57d92627d7d30795c`，本次完整改造尚未進入 commit／push。
- 發布前工作樹共有 585 個未提交項目（355 modified、36 deleted、194 untracked）；本機也刻意沒有正式 `deploy/api.env`，根目錄未設定 production `DOMAIN`。因此該次 production compose 預檢依設計 fail closed，不能在未整理提交、備份、secrets 與正式部署授權前直接上線。
- 部署 code review 發現 GitHub workflow 原本直接 build／up，未依文件在 migration 前執行 PostgreSQL 與映像備份，也沒有重建 `web_precision`、`marketing`、`templates`；已改為統一呼叫 `deploy/safe-deploy.sh`，並在 rsync 排除 `backups/`，防止下一次 `--delete` 移除 rollback artifacts。Bash 語法與 whitespace 檢查通過；本段記錄的是正式發布前的 gate 狀態，部署結果以對應的 GitHub Actions release run 與後續 production smoke test 為準。

### 本批 Gate 結論

- 本機登入後 UIUX、主要導覽、資料載入、四類動態明細（含 RFQ）與行動版驗收通過；本批發現的兩項可重現問題已修正並完成 code review。
- 本批屬於 production deployment 前置驗收；正式發布結果不由本段預先宣稱，應以對應的 GitHub Actions release run 與發布後 smoke test 為準。正式 ESP／外部資料供應商與真實 RFQ 營運證據仍是獨立外部 Gate。

## 整體實作結論

- 北極星流程「匿名訪客 → 行為追蹤 → 意圖評分 → 推測公司 → 尋找公司相關聯絡窗口 → 依旅程產生個人化信件 → 寄送與追蹤 → 對方回覆 → 真人業務接手 → RFQ／成交」所需的程式結構、治理邊界、人工審核與閉環歸因均已依前十二個實作批次完成。
- 各批均依序經過實作、測試、code review 與修正後才進入下一批；第 13 批另補齊實際登入後的桌面版、行動版與動態明細瀏覽器驗收，完整回歸未新增失敗。
- 仍未完成的是外部營運 Gate，而不是缺少程式入口：公司／聯絡資料授權與真實 precision、正式寄送與收信環境、送達／bounce／complaint／unsubscribe 指標、法遵核准，以及類別四 30／60 天 observation。這些 Gate 在取得證據前持續 fail closed。
