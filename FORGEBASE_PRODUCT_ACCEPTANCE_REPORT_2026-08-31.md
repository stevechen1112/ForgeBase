# ForgeBase 產品驗收報告（2026-08-31）

> 本文件是持續更新的正式驗收台帳。它依
> `FORGEBASE_DOCUMENT_AUTHORITY_INDEX_2026-08-28.md` 的權威順序整理，且不把
> 「已有程式」、「測試通過」、「已部署」或「真實商用 E2E」混為一談。

## 1. 本輪重新驗證基準

- Git：`main` 與 `origin/main` 均指向 `c39eccb`。工作樹原有
  `admin/next-env.d.ts` 標記為 modified，但內容 diff 為空；本輪不覆寫、不刪除。
- 正式部署：GitHub Actions `Deploy to Production` #78（run
  `33242102696`）在 `c39eccb` 成功；release gate、migration、API、North Star、
  admin browser/RBAC、五語系公開站、安全、SBOM、備份還原、rollback、六個映像、
  production topology、Linode 部署與健康檢查均為 success。
- 外部健康：`Production External Uptime` #218（run `33381384424`）於
  2026-08-31 成功，仍對應 `c39eccb`。
- 公開瀏覽器實測：
  - `https://pcbrm.tw/`：1280px 與 390px 均可載入，沒有水平溢位，console 無
    error/warning。
  - `https://axisform.172-233-64-5.sslip.io/`：1280px 與 390px 均可載入；商品、
    應用、認證、關於、RFQ、五語系、AI 顧問入口與手機選單存在；沒有水平溢位，
    console 無 error/warning。頁面明確標示為 fictional/demo，沒有冒充真實製造商。
  - 本輪未登入平台後台，因尚未取得本輪正式平台帳號登入授權。
- 公開 DNS（2026-08-31，以 Cloudflare DNS over HTTPS 查詢）：
  - `edge.forgebase.com`：NXDOMAIN。
  - `axisform.forgebase.com`：NXDOMAIN。
  - 隨機租戶子網域：NXDOMAIN，表示 wildcard 尚未建立。
  - `pcbrm.tw` 與 `axisform.172-233-64-5.sslip.io`：均解析至 `172.233.64.5`。
  - `replies.premierbiz.com.tw`：MX 指向 Resend inbound 所需 AWS inbound SMTP；
    DKIM selector 的 TXT 公開存在。本報告不記錄 TXT 值。
- 郵件／供應商：2026-08-28 最近一次 Resend audit、inbound readiness、commercial
  readiness、company policy 與 data quality workflows 均成功。這證明當次設定稽核
  通過，不等於 2026-08-31 已完成真人回覆或零號租戶商用 E2E。

## 2. 狀態定義

| 狀態 | 可宣稱內容 |
| --- | --- |
| 已完成程式實作 | 程式、資料模型、API 或操作流程已存在 |
| 已完成內部測試 | 自動化或受控內部測試通過；可包含 fake/hermetic provider |
| 已完成正式部署 | 對應程式已進入正式環境且 release/health gate 通過 |
| 已完成真實商用 E2E | 在受控真實租戶、真實外部能力與完整證據下完成實際流程 |
| 外部阻塞 | 需要 DNS、供應商權利、真實資料、明確收件人或真人回覆授權 |

## 3. North Star 十七步驗收矩陣

`是` 只代表該欄本身；不會向右自動推導。

| # | 流程 | 程式實作 | 內部測試 | 正式部署 | 真實商用 E2E | 現況／缺口 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 建立可辨識匿名訪客 | 是 | 是 | 是 | 否 | tracking 與 visitor identity 已存在；尚未為 ForgeBase 零號租戶建立可重現的正式證據包 |
| 2 | 產生真實瀏覽行為 | 是 | 是 | 是 | 否 | 本輪已產生公開站真實瀏覽，但未經授權登入後台／查 DB 對上零號租戶事件 |
| 3 | 顧客旅程完整記錄 | 是 | 是 | 是 | 否 | event、journey snapshot 與 UI 已有；未完成零號租戶正式資料核對 |
| 4 | 重算意圖分數並解釋原因 | 是 | 是 | 是 | 否 | scoring/reasons 有測試；尚無零號租戶真實旅程的正式驗收紀錄 |
| 5 | 真實 IP／供應商公司辨識 | 是 | 是 | 是 | 否 | PDL IP adapter 與 Shadow policy 已部署；尚無可接受 precision 的真實樣本驗收 |
| 6 | 公司可信度與證據 | 是 | 是 | 是 | 否 | confidence/evidence/review 模型存在；缺真實 provider 證據與錯誤樣本評估 |
| 7 | 真實受控聯絡窗口 | 是 | 是 | 是 | 否 | Hunter adapters 已註冊；未取得本輪使用真實聯絡人資料授權 |
| 8 | 第三方授權、品質、錯誤處理 | 部分 | 部分 | 部分 | 否 | 技術 POC 可用；OEM/reseller/資料使用權與 scorecard 尚未通過 |
| 9 | 旅程＋已發布知識產生個人化草稿 | 是 | 是 | 是 | 否 | Review Only 草稿鏈已部署；缺零號租戶真實旅程與已發布知識的正式證據 |
| 10 | 人工審核信件與證據 | 是 | 是 | 是 | 否 | 審核工作台存在但仍屬受控／建置狀態；未做零號租戶正式審核 |
| 11 | 明確授權後寄送 | 是 | 是 | 是 | 否 | 受控內部 delivery probe 曾存在；不是零號租戶完整 E2E，且本輪沒有寄信授權 |
| 12 | 送達、退訂、抑制 | 是 | 是 | 是 | 否 | delivery webhook、unsubscribe、suppression 有程式與測試；缺零號租戶真實寄送證據 |
| 13 | Resend inbound 回覆 | 是 | 是 | 是 | 否 | 公開 MX/DKIM 與 readiness 存在；沒有已授權真人回覆驗收證據 |
| 14 | 回覆轉真人接手任務 | 是 | 是 | 是 | 否 | classification/handoff 有 hermetic E2E；沒有真實 inbound 驗收 |
| 15 | SLA、指派、通知、操作紀錄 | 是 | 是 | 是 | 否 | 工作台與 audit 能力已部署；未在真實回覆後驗證 |
| 16 | RFQ／成交結果 | 是 | 是 | 是 | 否 | RFQ 與 outcome 模型／流程存在；AxisForm 僅為 functional demo，不是商用成交證據 |
| 17 | 匿名至 RFQ／成交閉環歸因 | 是 | 是 | 是 | 否 | attribution link 與 North Star hermetic E2E 已部署；尚無真實外部閉環 |

## 4. 依產品分類的盤點

### 4.1 核心已完善（工程與正式部署層級）

- 匿名 visitor/event 收集、同意與資料保留基礎。
- 意圖分數、階段與 reasons 資料結構。
- 旅程快照、公司辨識證據、聯絡候選、草稿、delivery、inbound、handoff、RFQ、
  attribution 的端到端資料模型與 API 基礎。
- 租戶隔離、RBAC、release gate、備份還原、rollback、安全掃描與外部健康檢查。
- 公開網站、五語系、RFQ 與 AI 顧問入口的已部署 UI 基礎。

「核心已完善」在此節只表示工程基礎可用；不代表整個 North Star 已完成真實商用
E2E。

### 4.2 核心未完善（商用品質／驗收層級）

- 公司辨識 precision、false positive、evidence 可解釋性與實際供應商錯誤處理。
- 聯絡窗口 relevance、freshness、email verification 品質與資料授權。
- 零號租戶真實旅程所驅動的草稿品質與人工審核證據。
- 真實送達、退訂、suppression、inbound 真人回覆、handoff SLA 與成交歸因。
- 專屬零號租戶的明確租戶身份、操作人邊界與可重跑驗收證據包。

### 4.3 非核心但應保留

- 網站／內容管理、模板、五語系、AI 顧問、平台管理、監控、備份還原與交付工廠。
  這些不是 North Star 的每一步，但直接支撐試行租戶交付與風險控制。

### 4.4 非核心可以刪除

- 本輪沒有足夠正式使用證據支持刪除任何模組。刪除需另做 runtime usage、資料依賴、
  路由與客戶交付影響分析，不能只依名稱或測試覆蓋率判斷。

## 5. 可在不對外寄信下先完成的項目

- 明確定義零號租戶 slug 與允許操作的 actor；任何受控探針不得再由
  `PUBLIC_TENANT_SLUG` 或硬編碼租戶帳號推導。
- 在三個全域開關維持 false 下執行 read-only commercial/provider/policy audit。
- 產生匿名真實瀏覽、核對 event/journey/intent reason 與資料保留，不呼叫聯絡人供應商。
- 對公司辨識使用 Shadow 模式與去識別 evidence，先做 precision 標註；不得把 mock
  當成商用證據。
- 使用零號租戶已發布知識與已核准的非個資測試輸入產生 Review Only 草稿，檢查引用、
  CTA、空狀態、錯誤狀態、RBAC 與操作紀錄。
- 驗證 unsubscribe/suppression 的 fail-closed 邏輯、idempotency、重試與稽核，不送信。
- 持續做 DNS、TLS、公開站、health 與 console 的唯讀監測。

## 6. DNS、Resend 與資料供應商實際狀態

| 項目 | 實際狀態 | 可宣稱範圍 |
| --- | --- | --- |
| ForgeBase tenant DNS | `edge`、AxisForm 與 wildcard 皆 NXDOMAIN | 尚未啟用；不得宣稱 `axisform.forgebase.com` 對外可用 |
| 既有正式網址 | `pcbrm.tw`、AxisForm sslip.io 解析且可瀏覽 | 可作現有公開驗收入口 |
| Caddy/TLS 新 host | 因 DNS 不存在，尚不能驗證新 host routing、憑證與 308 canonical redirect | 外部 DNS 阻塞 |
| Resend outbound | adapter/prerequisites audit 曾通過；全域開關應維持 false | 僅能宣稱受控就緒，不可宣稱已開通自動外聯 |
| Resend inbound | MX/DKIM 公開存在，readiness workflow 曾通過 | 尚未完成本輪真人回覆 E2E |
| 公司辨識 | PDL adapter 已部署、Shadow 模式工程完成 | 缺真實 precision/rights 驗收，不可宣稱商用品質 |
| 聯絡人 | Hunter search/verification adapters 已部署 | 缺真實聯絡人授權、品質 scorecard 與資料權利核准 |

## 7. 零號租戶完整商用驗收批次計畫

1. **Batch 0 — 證據基線與安全邊界**：完成本報告；修正受控 inbound probe，要求顯式
   tenant slug 與 actor，驗證 actor/tenant 邊界，並把 prepare 改成必須勾選當次寄信＋
   真人回覆授權。全程不寄信、不改 production 開關或資料。
2. **Batch 1 — 零號租戶唯讀 preflight**：經平台登入授權後確認專屬零號租戶是否存在、
   slug、domain、actor、feature/policy 全關閉與三個 global switches 全 false；產出不含個資
   的 readiness artifact。若不存在，另列建立租戶所需變更，不建立高權限帳號。
3. **Batch 2 — 匿名旅程與意圖**：用可辨識但不含個資的瀏覽 session 走公開內容/RFQ 前
   旅程，從 DB/API 對上 events、journey、score、reasons、retention 與 audit；桌機／手機
   後台驗收。
4. **Batch 3 — 公司辨識 Shadow**：使用真實 IP/provider，建立 precision 樣本、證據、
   false-positive、timeout/rate-limit/no-match 測試；在資料使用權未核准前不進 contacts。
5. **Batch 4 — 聯絡人供應商 POC**：取得真實聯絡人使用授權後，完成 rights、relevance、
   freshness、verification、錯誤與刪除/保留 scorecard；不寄信。
6. **Batch 5 — 個人化草稿與人工審核**：以真實旅程、已發布知識與已核准候選產生
   Review Only 草稿；人工核對引用、推論、CTA、語系、抑制與稽核。
7. **Batch 6 — 送達、退訂與抑制**：取得明確測試收件人授權後，只對該地址開一次受控
   視窗，驗證 delivery webhook、unsubscribe、suppression、idempotency，立即復原開關。
8. **Batch 7 — 真人回覆與接手**：另取得真人回覆與 inbound 開關授權，驗證 route、
   classification、handoff、SLA、指派、通知、audit，完成後關閉 inbound。
9. **Batch 8 — RFQ／成交與歸因**：由接手任務建立 RFQ 與受控 outcome，核對匿名 visitor
   到 company/contact/outreach/reply/handoff/RFQ/outcome 的完整 attribution evidence。

每批都必須依序完成：實作、相關測試、type-check/lint/build、code review、修正、提交、
部署與正式瀏覽器驗收；未完成的欄位不得向右提升狀態。

## 8. 第一個受控試行租戶交付就緒度

目前結論：**工程與部署基礎接近試行就緒，但尚未達完整產品承諾交付就緒**。

- 已就緒：網站／RFQ／管理基礎、租戶隔離、release/security/recovery、核心資料模型與
  受控 provider/outreach/inbound 工程鏈。
- 尚未就緒：ForgeBase 專屬零號租戶身份與證據包、公司 precision、聯絡人權利與品質、
  真實送達／回覆／handoff／成交歸因。
- 外部阻塞：ForgeBase wildcard DNS、真實聯絡人資料授權、明確測試收件人、真人回覆與
  開關授權。
- 目前允許的產品主張：已完成程式實作、內部測試與正式部署的受控試行基礎。
- 目前不允許的產品主張：完整 North Star 已完成真實商用 E2E、
  `axisform.forgebase.com` 已啟用、公司／聯絡人資料已達商用品質、外聯與 inbound 已全面
  開通。

## 9. Batch 0 變更紀錄

- 已完成程式實作：移除 inbound probe 對 `admin@forgebase.com` 與 public tenant fallback 的隱含
  依賴。
- 已完成程式實作：要求顯式 actor email 與零號租戶 slug；tenant-bound operator 只能操作其自身
  tenant，tenantless operator 必須是 `is_superuser=true`。
- 已完成程式實作：workflow `prepare` 必須明確確認當次外部寄信與真人回覆授權，預設模式改為
  `close`。
- 已完成內部測試：完整 API suite `315 passed, 101 skipped`；目標 probe suite
  `25 passed, 1 skipped`；目標 Ruff check/format、workflow YAML parse、四個前端
  type-check/lint/build 全部通過。Web build 的本機 API fallback 為預期行為，build exit 0。
- Code review 已修正：既有 idempotency lookup 原可在解析目標租戶前命中相同 probe id；
  現已加入 `tenant_id` 條件，避免跨租戶重用既有 message。
- 第一次 production run #79（run `33384020635`）在 release gate 內停止，未部署到
  Linode：91 個 operational contract tests 中有一個仍比對舊的 close CLI 字串。已同步
  更新契約測試並在本機重跑同一組合為 `91 passed, 1 skipped`；應用、North Star、容量、
  隱私及其餘 release jobs 在 #79 均已通過。
- 尚未完成正式部署：本節會在對應 GitHub Actions production run 成功後補入 run/commit
  證據。
- 尚未執行任何 production probe、外部寄信、真人回覆、DNS 修改、租戶政策修改或全域
  開關變更。
