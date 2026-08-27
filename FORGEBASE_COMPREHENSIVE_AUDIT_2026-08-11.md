# ForgeBase 產品全面稽核報告

稽核日期：2026-08-11\
稽核基準：`main` / `c69c7d4b2a1ee04f0885db3b6db0b1dfd64ad8e3`\
產品定位：外銷製造商 B2B 官網、訪客意圖、RFQ 與成長營運平台\
稽核方式：唯讀程式碼與文件檢視、全新資料庫遷移、測試／型別／lint／build、相依套件弱點掃描、桌機與手機實際介面驗證\

> 本報告不包含修復實作。稽核時工作樹已含使用者先前授權的「移除 Legacy Site Intake 與網站內容 AI 產生／翻譯」變更；這些既有變更均被保留，未視為本輪稽核造成的修改。

## 1. 結論摘要

ForgeBase 已不只是概念原型：前台、管理後台、RFQ、意圖追蹤、內容模型、多語骨架、成長儀表板、通知與多種整合都有相當完整的程式基礎。實際前台桌機與手機版的視覺完成度良好，RFQ 表單資訊結構也貼近 B2B 採購情境。全新 PostgreSQL 資料庫可從零遷移到 head，完整後端測試有 132 項通過。

但目前不適合直接作為「多租戶付費 SaaS」正式上市。主要原因不是頁面完成度，而是租戶隔離、輸入信任邊界、背景任務可靠性、相依套件弱點與部署控制仍存在上市阻擋風險。部分行銷與合規文案亦超過目前可證實能力。

本次判定：

- 產品／視覺成熟度：**可展示、可進行受控試點**
- 單一租戶內部使用：**修復 P0 後可小規模運行**
- 多租戶付費上線：**目前 No-Go**
- 大規模行銷導流：**目前 No-Go**
- 建議路線：先做 30 天安全與可靠性封板，再擴大試點，不應先增加新功能

風險統計：

| 等級 | 數量 | 意義 |
|---|---:|---|
| P0 | 8 | 上市阻擋；可能造成跨租戶外洩／修改、遠端攻擊、成本濫用或未經驗證部署 |
| P1 | 18 | 應在付費試點或擴量前完成；會影響資料正確性、轉換、SEO、合規或營運可靠性 |
| P2 | 15 | 60–90 天內完成；主要是可維護性、操作效率、可觀測性與產品一致性 |
| P3 | 6 | 工程衛生與文件整理 |

## 2. 已確認的產品邊界

### 2.1 明確排除

依產品決策，ForgeBase 不應提供：

1. Legacy Site Intake／舊站自動匯入。
2. 由 AI 自動撰寫、翻譯或發布網站內容。

目前前台與 Admin 的網站內容 AI 草稿／翻譯入口已移除，內容多語改為人工維護；舊站匯入相關後台路徑也被導回 Dashboard。這個方向正確，能降低錯誤內容、錯誤翻譯與未審核發布風險。

### 2.2 邊界仍需再定義

系統仍有其他生成式 AI：

- 公開官網 Product Advisor 對話。
- RFQ 分析與回覆草稿。
- Admin Copilot 營運問答與資料寫入工具。
- CTA 推薦、關聯推薦、每日摘要。
- AgentOS 回寫的 RFQ 分析／回覆草稿欄位。

因此「AI 寫內容」目前實際被解讀為「不產生網站發布內容」，不是「完全不產生任何文字」。若產品決策要禁止所有 AI 生成文字，RFQ 回覆草稿、Copilot 摘要與 Advisor 回覆仍不符合。建議正式寫成產品政策：

> AI 可做檢索、排序、摘要與草稿，但不得直接發布網站內容、寄信、改商業狀態或形成合規承諾；所有對外文字與不可逆操作必須人工確認。

## 3. 稽核覆蓋與限制

本次覆蓋 13 個層面：

1. 產品定位、客群、價值主張與定價。
2. 核心使用者旅程與轉換流程。
3. 前台資訊架構、桌機／手機 UX、基本可及性。
4. Admin 資訊架構、角色與日常操作效率。
5. 內容模型、多語、SEO 與發布契約。
6. Capture／Intent／Conversion／Outcomes 成長閉環。
7. AI 使用邊界、grounding、成本與操作安全。
8. 多租戶隔離、認證授權與資料隱私。
9. 資料模型、約束、併發與資料品質。
10. API 契約、架構、效能、背景任務與健康檢查。
11. 外部整合、通知、Webhook 與憑證管理。
12. 測試、建置、CI/CD、相依套件與可重現性。
13. 營運、上市、法務信任與商業可行性。

未包含以下正式驗證，不能以本報告取代：

- 專業黑箱／白箱滲透測試。
- 具有真實 OpenAI、HubSpot、Meta、Google Ads、GSC、Telegram、LINE、ESP、R2 帳號的端到端驗證。
- 真實流量壓測、容量規劃與災難復原演練。
- 正式 GDPR、台灣個資法、跨境資料與行銷郵件法務意見。
- 真實搜尋引擎 crawl、Core Web Vitals 與長期 SEO 成效。
- Python 套件 CVE 掃描；本機未安裝 `pip-audit`，僅完成 `pip check`。

## 4. 驗證結果

### 4.1 程式與資料庫

- 程式規模約 47,000 行：API 23,369、Admin 18,708、Web 12,553（不含測試／產出物的粗略統計）。
- 全新 PostgreSQL 16 容器從零執行 Alembic 至 `0060`：**成功**。
- 文件仍宣稱 migration head `0051`：已落後 9 個版本。
- `docker-compose.prod.yml` 使用 PostgreSQL 16，部分架構文件寫 PostgreSQL 17。
- API image／CI 使用 Python 3.12，文件部分位置要求 Python 3.13+。

### 4.2 自動化測試

| 驗證 | 結果 |
|---|---|
| 後端完整 DB 測試 | **132 passed / 1 failed / 2 skipped** |
| 無 DB 測試 | 83 passed / 52 skipped |
| Web TypeScript | 通過 |
| Admin TypeScript | 通過 |
| Web lint | 通過，2 warnings |
| Admin lint | 通過，7 warnings |
| Python compileall | 通過 |
| Python `pip check` | 通過 |
| Web 正式 build（本機 Windows） | 失敗 |
| Admin 正式 build（本機 Windows） | 失敗 |

唯一後端失敗案例是 `test_slug_locale_page_type_query`：查詢不支援的 `locale=ja` 時，`to_content_locale()` 靜默降級成 `en`，API 回傳英文內容，而非拒絕或空結果。這會造成錯誤語言發布／索引，屬 P1 資料契約問題。

測試另產生約 2,513 個 warnings，包含 SQLModel／SQLAlchemy 舊 API、非同步連線取消 coroutine 未 await，以及 Copilot 任務在 event loop 結束時仍 pending。測試雖大多通過，但背景任務生命週期並不乾淨。

兩項 skipped 為需要外部 AgentOS repo／runtime 的整合測試。

### 4.3 建置與相依套件

兩個 Next.js build 在此 Windows 環境因 `C:\Users\User\package-lock.json` 被誤判為 workspace root，接著讀取使用者目錄時發生 EPERM。兩份 `next.config.ts` 都未設定 `outputFileTracingRoot`。這不等同 Linux CI 必然失敗，但表示本機與 monorepo 邊界不可重現。

`npm audit --omit=dev`（2026-08-11，npm 官方 audit endpoint）：

| 專案 | High | Moderate | Low | Total |
|---|---:|---:|---:|---:|
| Web | 5 | 1 | 1 | 7 |
| Admin | 4 | 0 | 0 | 4 |

兩者的直接相依 `next@15.5.15` 命中多項 High advisory，包含 DoS、middleware bypass、SSRF 與 cache 問題；Web 的 `next-intl@4.8.3` 亦命中 open redirect／prototype pollution advisory。另有 `sharp`、`postcss`、`nanoid` 等間接弱點。npm 回報均有修復版本可用。這些是上市前必須處理的 P0。

Python requirements 多數直接 pin，但 `langfuse>=2.0.0` 無上限、也沒有完整 transitive lock／hash；本機 `.venv` 的實際版本又高於 requirements，測試環境不能代表正式安裝結果。

### 4.4 實際介面驗證

本機以獨立 port 啟動 Web 與 Admin，使用內建瀏覽器驗證桌機與 390×844 手機 viewport：

- 英文首頁：桌機視覺層次、CTA、產品／應用／認證敘事完整。
- 手機版：導覽以可操作 dialog 開啟，有 Close 控制，核心 CTA 可見。
- RFQ：欄位語意清楚，包含數量、規格、時程、Incoterm、年量、目標價與同意欄位。
- Admin 登入：版面清楚，但品牌、數據、ISO/GDPR 信任標章為硬編碼示範內容。
- 繁中首頁：導覽文字翻譯，但產品、應用、認證內容大量回退英文，多個 CTA 連到無 locale 前綴的英文路徑。
- 繁中首頁實際 head：canonical 指向英文站根，無 hreflang，title 出現品牌重複。

## 5. P0 上市阻擋項

### P0-01 ContentAsset 完全缺少租戶隔離

證據：`api/app/models/content_asset.py` 沒有 `tenant_id`；`api/app/api/v1/endpoints/assets.py` 的 list／update／delete 亦不以目前使用者租戶篩選。

影響：任何已登入租戶使用者可能列出、修改或刪除其他租戶素材；上傳時也可關聯任意 product/page UUID。這是直接跨租戶資料外洩與破壞。

要求：Asset 必須有強制 `tenant_id`、所有查詢採 tenant scope、關聯實體必須同租戶，並加入跨租戶負向整合測試。

### P0-02 Integration credential API 信任呼叫者提供的 tenant_id

證據：`CredentialUpsert` 接收 `tenant_id`，list／upsert／delete 以 request tenant_id 查詢，而非 current user tenant。部分角色可看到解密後的 masked preview。

影響：跨租戶列舉憑證存在性、預覽或管理密鑰；若平台管理與租戶管理需求並存，權限模型目前沒有安全分界。

要求：一般租戶 API 不得接受任意 tenant_id；平台管理另設明確 super-admin endpoint、audit log 與 step-up authentication。

### P0-03 公開 visitor/session UUID 可跨租戶重用

涉及：`events.py`、`chat.py`、`chat_service.py`、`contacts.py`、`rfqs.py`。

證據與影響：

- Tracking event 會重用 client 提供的 visitor／session UUID，但未驗證既有記錄是否屬於解析出的租戶。
- Chat message 只驗 body visitor_id 等於 session visitor_id，未驗 session tenant；handoff 也未比較 tenant。
- Contact／RFQ 讀 visitor intent 時未驗租戶。
- RFQ 的 application_id／product_ids 未驗同租戶，可建立跨租戶關聯。
- Chat 建立的 tracking event 部分未寫 tenant_id，造成 NULL tenant 資料與歸因斷裂。

攻擊者若取得或猜到 UUID，可污染其他租戶意圖分數、關聯表與對話流程。visitor 主鍵是全域 UUID，也不利於 tenant-first 約束。

要求：所有 public identity upsert 都必須驗 `(tenant_id, id)`；關聯寫入前檢查同租戶；考慮 server-signed visitor token 或 tenant-scoped opaque ID。

### P0-04 儲存型 XSS 與同源 SVG 風險

證據：前台多處 `dangerouslySetInnerHTML` 顯示 product、application、FAQ、capability、certification 與 flexible block；目前 sanitizer 只在一般 Page.body 路徑套用。Upload 信任 client MIME、允許 SVG，未做 magic-byte sniffing、SVG sanitize 或 malware scan，且 fallback 素材由同網域 `/uploads` 提供。

影響：有內容編輯權限的帳號、遭竊帳號或跨租戶素材漏洞可植入 script／事件屬性／惡意 SVG。Admin token 使用 sessionStorage，且沒有 CSP，成功 XSS 可能取得後台 session 或執行同源 API。

要求：所有 HTML 欄位在寫入端採同一 allowlist sanitizer；SVG 拒收或離線 sanitize 並改成 attachment／獨立無 cookie 網域；加入 CSP、Trusted Types 評估與 XSS regression tests。

### P0-05 兩個 API worker 會重複啟動所有 APScheduler jobs

證據：production compose 以 `uvicorn ... --workers 2` 啟動；`FORGEBASE_SCHEDULER_ENABLED` 預設為 1，compose 沒有為非主 worker 關閉。每個 process 都會建立自己的 scheduler。

影響：score decay、Google Ads sync、自動發布、每日摘要、SLA scan、nurture 發送都可能執行兩次，造成分數重算、重複通知／寄信、重複外部同步與競態。

要求：scheduler 移至單獨 worker／queue，或使用分散式 lock 與 idempotency key；API process 不應兼任 durable scheduler。

### P0-06 公開 AI Advisor 沒有成本與濫用防護

證據：rate limiter 只涵蓋 auth、forms、events；公開 `/chat/sessions` 與 `/messages` 不在規則內，也沒有 plan feature guard、token budget、visitor quota 或 bot challenge。Limiter 本身還是每 worker 記憶體狀態。

影響：匿名攻擊者可大量觸發 LLM，造成 OpenAI 費用與 API／DB 資源耗盡。兩 worker 讓現有限制的有效額度再加倍。

要求：預設關閉公開 AI；需啟用時採 shared rate limit、tenant budget、session quota、輸入／輸出 token cap、timeout、cache、熔斷與成本告警。

### P0-07 前端生產相依套件有已知 High 弱點

證據：npm audit 顯示 Web 5 High、Admin 4 High；直接相依 Next.js 與 next-intl 均有可用修復。

影響：依實際使用路徑不同，可能涵蓋 DoS、認證／middleware bypass、SSRF、cache poisoning 與影像處理弱點。

要求：先在分支升級 Next.js 至已修補版本、next-intl 至修補版本，重新跑 type/lint/build/E2E 與 npm audit；不得只執行 `npm audit fix --force` 後直接部署。

### P0-08 Production deploy 不受 CI 成功條件約束

證據：`deploy.yml` 與 API／frontend CI 都由 push main 各自觸發，彼此沒有 needs／workflow_run 關係；部署可能在測試失敗前開始。部署直接 SSH root、關閉 StrictHostKeyChecking、在原機器執行 `git checkout -- .`、migration、build、restart；沒有原子 release、rollback 或 pre-deploy backup。

影響：失敗程式或破壞性 migration 可能直接進 production；主機驗證關閉增加 MITM 風險；半完成部署難回復。

要求：建立單一 pipeline：CI 全綠 → immutable artifact/image → backup／migration plan → canary/blue-green → readiness smoke → rollback。SSH known_hosts 必須 pin，部署不使用 root。

## 6. P1 重要問題

### P1-01 其他跨租戶缺口

- `public_application_locales` 未解析 tenant，跨租戶查同 slug。
- `unlink_related_application` 沒有驗證兩端租戶即可刪關聯。
- 建議建立「每個 endpoint 都必須選擇 tenant policy」的測試矩陣，避免逐點補洞。

### P1-02 API 方案功能控管不完整

Admin sidebar 有 Starter／Professional 鎖定提示，但 nurture、Copilot、AI RFQ、relation recommend、visitor CTA recommend 等多個 API 沒有對應 `RequireFeature`。使用者可繞過 UI 直接呼叫。

影響：商業方案失效、成本功能被低價方案使用，也增加攻擊面。

### P1-03 RFQ 編號在併發下可能碰撞

`RFQ-YYYYMMDD-NNN` 以當日 count + 1 產生，沒有 sequence、row lock 或 retry；欄位又是 global unique。多租戶同時送件可能撞號並回 500。

### P1-04 不支援 locale 靜默回退英文

`to_content_locale('ja')` 回 `en`，已由實跑測試證實失敗。未知 locale 應 422／404 或回空集合，不能假裝是英文內容。

### P1-05 繁中導覽與內容語系斷裂

實測 `/zh-TW`：多個首頁 CTA、產品卡、分類卡、認證連結仍為 `/products`、`/rfq` 等英文路徑；產品／應用資料大量回退英文。`resolvedLocale` 使用 `zh-tw`，路由則是 `zh-TW`，程式中多處自行拼 URL，造成大小寫與 prefix 漂移。

建議所有連結統一使用 next-intl navigation helper，不自行拼接；內容缺翻譯時要在 Admin 顯示缺口，不在公開頁無聲混語。

### P1-06 SEO metadata 與 sitemap 不正確

- 實測繁中首頁 canonical 指到英文根，沒有 hreflang。
- 首頁 title 已含品牌，root template 再附品牌，造成重複。
- sitemap 註解寫「all locales」，實際 products/applications 只以 `en` 查詢。
- categories/capabilities/certifications 等 dynamic routes 只建立英文 URL。
- static route `lastModified` 每次用 now，對搜尋引擎形成虛假更新。
- `/rfq` 與 `/request-quote` 同時進 sitemap，內容重複且 canonical 未明確統一。

### P1-07 Tracking 未以 consent 為前置條件

`analytics.ts` 在第一次 track 時建立一年期 `fb_vid`、sessionStorage 與離線 localStorage queue；GA script 只要設定 measurement ID 就載入。程式沒有 consent state／CMP gate，Cookie Policy 只說可從瀏覽器管理。

對需要 opt-in 的市場可能不合規。至少要區分 essential 與 analytics，未同意前不得建立 analytics identifier 或載入 GA。

### P1-08 表單與法律文案不符合實際資料流

RFQ 頁寫「We will never share your data with third parties」，但產品可將資料送往 HubSpot、Meta、Google Ads、ESP、OpenAI／Langfuse、Telegram／LINE 等處理者。Privacy/Cookie 文案沒有完整列出 controller、processor、目的、保存期間、跨境、刪除／存取權與聯絡方式。

「不出售」與「不分享」法律意義不同，不應混用。需由法務按實際啟用整合產生 tenant-specific policy。

### P1-09 行銷頁與登入頁有不可證實承諾

實測內容包含：

- 「AI 基於你的產品資料回答，不會亂講」。
- 「30 分鐘搞定上線」。
- 「現有官網就能開始…」但已移除舊站匯入，且實際需要人工建內容／多語、DNS、素材與設定。
- Admin 登入頁硬編碼「40+ 國家、500+ 商品、98% 滿意度、ISO 27001、GDPR 合規」。
- 前台 demo 使用 ISO、CE、SGS 等證明與下載文件；若沒有醒目 demo 標示，容易被誤認為真實客戶證明。

這些不只是 copy 問題，而是銷售、合規與客戶信任風險。應改為可量測、有條件且可提出證據的說法。

### P1-10 AI 回覆缺少嚴格 schema 與可靠性控制

AI 服務主要依賴 `response_format=json_object` 後直接 `json.loads`，沒有 Pydantic schema、enum／UUID 驗證、candidate ownership 驗證或 confidence calibration。失敗時 RFQ analysis 回傳看似真實的 50 分／medium，而不是明確 unavailable，可能誤導業務。

OpenAI 呼叫沒有每 workflow 明確 timeout／retry／budget；多個 module 在 import 時建立 client，未設 key 可能讓應用啟動失敗。

### P1-11 Copilot 可由模型直接執行寫入

Copilot prompt 要求「使用者明確要求」，且 server 有角色與 tenant 檢查，這是正向設計。但 `_execute_tool` 會立即執行模型選出的 status update、first-response、reminder 等 action，沒有獨立的 server-side confirmation token／preview step。

模型誤判、模糊語句或 Telegram 帳號遭接管時可能立即改商業資料。應採 propose → user confirms exact diff → execute，confirmation 要由後端狀態機驗證，不能只靠 system prompt。

### P1-12 Fire-and-forget 工作不可持久化

RFQ 建立後使用 `asyncio.create_task` 執行 routing、通知、HubSpot、Copilot、auto-reply；page revalidate、hot visitor、webhook 也相同。Process restart／deploy 會丟工作，無 retry ledger，部分測試已看到 pending task。

Webhook retry 更在 process 內 sleep 60／300 秒；auto-reply 可 sleep 最長 12 小時。這不是可靠的背景工作模型。

### P1-13 Upload 信任 client MIME 並整檔讀入記憶體

最大 50MB 檔案被一次讀入，未做 streaming quota、magic bytes、AV scan、tenant quota；可造成 worker 記憶體壓力與惡意檔案託管。

### P1-14 成長 funnel 的轉換率不具 cohort 一致性

`growth_ops.get_funnel` 的 traffic 依 session start、high intent 依 visitor last_seen、RFQ 依 created_at、quoted 依 quote_sent_at、won 依 closed_at。它們不是同一批 visitor／RFQ 的逐層轉換，`count / previous count` 可能超過 100% 或被誤讀為真實 funnel。

應改為 cohort-based funnel，清楚定義 entity、entry date、window 與去重規則。

### P1-15 Outcome feedback 有重複樣本與 outcome leakage

同一 visitor 有多筆 RFQ 時會重複進樣本；分析使用 visitor 現在的 facet score，而非 RFQ 提交時 snapshot。成交後的後續行為可能反向抬高 score，卻被解讀為成交 lift。報告雖標 observational，但任務佇列仍把 lift ≥ 1.5 直接轉成建議工作。

建議保存 submit-time feature snapshot、每 visitor/RFQ 明確去重，設最低樣本與信賴區間，避免把相關性當因果。

### P1-16 Production health check 過淺

`/health` 固定回 `{"status":"ok"}`，不檢查 DB、migration、queue/scheduler、OpenAI 或必要儲存；deploy health 只看這個值。Web asset health 也未納入 deploy pipeline。

應拆 liveness/readiness，readiness 至少驗 DB query、migration head、必要儲存與關鍵設定。

### P1-17 CI build 沒有驗證真實 API 契約

Frontend CI 設 `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`，但 client 自己再附 `/api/v1`；CI 又沒有啟動 API。Web 的 non-strict fallback 會把 API failure 轉成空資料，build 仍可能綠燈。

文件宣稱 strict fail-fast，`web/Dockerfile` 實際註明 non-strict fallback，屬契約矛盾。Production build 應用 strict mode，並在 smoke test 驗證至少一個真 API response。

### P1-18 部署缺少備份、復原與 migration 相容策略

檢視到的 compose／deploy 文件沒有自動 DB backup、restore drill、RPO/RTO、向前／向後相容 migration 或 asset backup 流程。對承載 RFQ 與客戶資料的 SaaS 不足。

## 7. P2 改善項目

1. **API response 不一致**：有標準 envelope、有 raw list/dict、有 `{"error":...}`；SDK 與錯誤處理成本高。
2. **Auth refresh token 無 server revocation**：rotate 但沒有 session/device ledger，遭竊 token 最長可用 30 天。
3. **Service account token 為靜態明文 env mapping**：無 hash、expiry、scope、rotation audit。
4. **Rate limit IP 解析策略不一致**：middleware 與 events 對 X-Forwarded-For 取值不同，應由單一 trusted proxy resolver 處理。
5. **Admin 使用 raw UUID**：RFQ 指派、nurture enroll、product category 等要求輸入系統 ID，不適合日常營運。
6. **Site Profile 大量 raw JSON textarea**：header/footer/assets 需非技術使用者編輯 JSON，容易配置錯誤。
7. **Admin 路由與角色策略主要在 client guard**：後端大多有 dependency，但需用 endpoint matrix 自動驗證，不應依 sidebar 隱藏。
8. **單一來源多語架構不足**：default locale 與 `[locale]` 各有 wrapper／duplicate routes，易發生內容與 metadata 漂移。
9. **Sitemap 上限固定 5,000 且無 index 分片**：大型租戶會漏頁；需 sitemap index。
10. **沒有 CAPTCHA／honeypot／email verification**：RFQ 只靠 IP limiter，廣告導流後容易被 spam。
11. **Content attribution 只 match Page slug**：product/application/category landing 多數會落入 unmatched，與產品「內容成效」承諾不符。
12. **金額與 revenue model 不完整**：RFQ 有 target_price 字串，沒有 quote amount、currency、won revenue、margin 或訂單真值；無法真正計算 ROI／pipeline value。
13. **GSC 無憑證時回 mock data**：若 UI 未明確標 Demo，使用者可能把示範值當真實成效。
14. **安全 headers 不完整**：缺 CSP、HSTS、Permissions-Policy；Caddy 也未集中加入。
15. **無可觀測 SLO**：有 request log／Langfuse／run log，但缺統一 metrics、error budget、queue depth、external delivery success 與告警門檻。

## 8. P3 工程與文件衛生

1. README／Architecture／deploy 文件的 DB、Python、migration head、build strictness 已漂移。
2. Next.js `next lint` 已 deprecated；應改 ESLint CLI。
3. lint 尚有 unused imports、hook dependency 與未優化 `<img>` warnings。
4. SQLModel／SQLAlchemy 使用舊 API，產生大量 deprecation warnings。
5. `WorkflowType` 還保留 INTAKE、TRANSLATE、CONTENT_OPTIMIZE 等已停用概念，容易讓新開發誤判產品邊界。
6. 缺少 ADR／威脅模型／資料處理清冊，跨團隊很難持續守住已定產品邊界。

## 9. 各層評估

### 9.1 產品定位與定價

優點：對外銷製造商的核心痛點描述明確，RFQ、產品資料、意圖訊號與業務 follow-up 的組合有差異化；比純 CMS 或形象站更接近可量化商業結果。

問題：目前 $149／$699 的方案差異主要靠 UI 顯示，API entitlement 未封好；Professional 的 AI 與追蹤成本缺 usage-based guard。若公開 AI 無限使用，毛利不可預測。

建議：Starter 聚焦「可信賴內容＋RFQ 收件箱＋基本轉換追蹤」；Professional 才開 intent、dynamic CTA、整合、受控 Advisor，並以 session／token／event 使用量限制。

### 9.2 前台轉換與 UX

優點：Hero、信任、產品、應用、流程、認證、RFQ 的敘事順序合理；RFQ 欄位貼近工業採購；手機 menu 基本可用；圖片都有 alt 的抽樣結果良好。

問題：首頁過長且 demo claim 很多；Advisor 浮動 CTA 與 RFQ CTA 同時競爭；多語掉回英文會直接破壞信任；RFQ 頁出現巢狀 main landmark；consent 文字中的 Privacy Policy 不是清楚可操作連結。

### 9.3 Admin 日常作業

優點：內容、RFQ、intent、outcomes、notifications、integrations 已形成完整功能面；Copilot action 有角色檢查與 audit event 的基礎。

問題：資訊架構偏大，進階功能很多但 onboarding／empty state／operator workflow 未統一；raw UUID／JSON 讓非技術使用者難操作；硬編碼 NorthForge 與 demo 統計會讓 white-label SaaS 顯得未完成。

### 9.4 成長閉環

Capture 與 Conversion 最成熟：event、visitor、contact、RFQ、SLA、routing 已連起來。Intent 有 rule facets 與 ML 入口，但公開 event 可被 spoof、sample 少時模型可信度不明。Outcomes 有 funnel／attribution／feedback，但統計定義不足，尚不能作為可靠投資決策。

建議先把「事件可信 → RFQ 關聯 → outcome 真值 → cohort 報表」做對，再談 ML 或 AI 最佳化。

### 9.5 AI 邊界

優點：Advisor system prompt 明定只用提供 context、不發明價格／交期／合規；Copilot 寫入有角色與 tenant guard；部分外寄信走 outbox／人工核准。

問題：行銷宣稱「不會亂講」不成立；公開成本無 guard；AI JSON 無 schema；fallback 會製造看似有意義的分數；Copilot 寫入只靠 prompt 判定 explicit intent；生成文字範圍與「不要 AI 寫內容」決策仍有語意落差。

### 9.6 多租戶與安全

Tenant_id 已廣泛存在，是可修好的結構；但只要少數 global query／client tenant_id 漏洞存在，整體多租戶承諾就不成立。安全不能以「多數 endpoint 有 scope」計分，必須做到 100% deny-by-default。

### 9.7 架構與營運

FastAPI＋Postgres＋Next.js＋Caddy 適合目前規模；問題在 API worker 同時扮演 web server、scheduler、queue worker。應把同步 request、durable job、scheduled job 三種生命週期拆開。

## 10. 建議的目標架構與控制原則

1. **TenantContext 強制化**：repository/service 層所有讀寫都要求 tenant context；global platform query 使用不同型別與 router。
2. **資料庫第二道防線**：關鍵表補 tenant_id、composite FK／unique；評估 PostgreSQL RLS，至少先在 assets、credentials、visitors、sessions、events、relations 落地。
3. **Durable job layer**：RFQ 通知、HubSpot、webhook、revalidate、auto-reply、nurture 全部進 queue/outbox；每個 job 有 idempotency key、retry、dead-letter 與操作記錄。
4. **AI gateway**：集中 timeout、retry、schema validation、budget、tenant quota、PII policy、fallback state 與人工確認。
5. **可信事件模型**：server 簽發 visitor identity，event allowlist＋schema＋anti-replay，商業 outcome 由後台或 CRM 真值寫入。
6. **Release gate**：immutable image、SBOM／dependency scan、DB backup、migration compatibility、readiness、smoke、rollback。
7. **Content safety pipeline**：統一 sanitize、asset inspect、CSP、獨立素材網域。

## 11. 30／60／90 天路線

### 0–30 天：封住上市阻擋項

目標：可進行少量、受控、單一或少數租戶試點。

1. 修復 assets、credentials、visitor/session/chat/forms/relations 的 tenant isolation。
2. 建立跨租戶 security test suite；每個 CRUD 含 read/write/delete 負向測試。
3. 統一 HTML sanitize；停用 SVG 或隔離處理；加 CSP。
4. 將 scheduler 改為單一獨立 process；RFQ／webhook 先導入 DB outbox。
5. 公開 Advisor 預設關閉；加入 shared rate limit、quota、timeout 與 cost alert。
6. 升級 Next.js／next-intl／sharp 等，npm audit high 歸零或形成有期限風險接受單。
7. 讓 deploy 等待 CI；加入 known_hosts、非 root、backup、readiness 與 rollback。
8. 修正繁中 URL、canonical、hreflang、sitemap 與 locale fallback。
9. 移除／改寫無法證實的 AI、ISO、GDPR、數據與 30 分鐘上線文案。

30 天出口條件：P0=0；跨租戶負向測試全綠；npm High=0；單一 job 不重複；可在 staging 完成一次 backup→deploy→rollback→restore 演練。

### 31–60 天：把資料與營運做可信

1. 完成 queue／outbox，移除 request process 的長 sleep 與裸 `create_task`。
2. 重做 cohort funnel、submit-time outcome snapshot 與 content attribution。
3. 補 quote amount、currency、won revenue／order truth，才能計算 pipeline 與 ROI。
4. 建立 consent management、data retention、export/delete workflow 與真實 subprocessor 清冊。
5. 把 Admin raw UUID／JSON 改成 picker、builder、preview 與 validation。
6. AI output 全面 schema validate；Copilot 寫入改兩階段確認。
7. 建立 metrics/dashboard：RFQ submit success、first-response SLA、job retry、integration delivery、LLM cost、tenant errors。

60 天出口條件：關鍵事件／RFQ 可追溯；報表定義有資料字典；外部送達可重試與查帳；使用者不用輸入 UUID/JSON 完成核心作業。

### 61–90 天：準備擴量

1. 執行正式滲透測試、壓測與災難復原演練。
2. 建立 E2E 測試：註冊／登入、內容發布、繁中切換、RFQ、指派、狀態、nurture approval、方案鎖定。
3. 建立租戶 onboarding、內容完整度、SEO readiness 與上線 checklist。
4. 以真實試點資料校準 intent rules，不急著訓練 ML；樣本門檻不足時明確停用。
5. 依真實成本設定方案用量、超額與毛利警戒線。
6. 法務完成 Terms、Privacy、DPA、subprocessor、AI disclosure 與 marketing consent。

90 天出口條件：通過外部安全測試；RTO/RPO 演練達標；至少 2–3 個試點租戶完成完整 closed-loop 且數據可對帳。

## 12. 建議驗收清單

### 安全與租戶

- [ ] Tenant A 永遠無法讀／改／刪 Tenant B 的 asset、credential、visitor、session、event、chat、relation、RFQ link。
- [ ] 所有 public UUID reuse 測試回 404／403，不污染資料。
- [ ] 所有 HTML／SVG payload 無法在公開站與 Admin 執行。
- [ ] 公開 AI、forms、events 都有 shared quota 與 abuse telemetry。

### 可靠性

- [ ] 2+ API replicas 下，每個 scheduled job 只執行一次。
- [ ] API restart 不會丟 RFQ notification／webhook／HubSpot／revalidate。
- [ ] 相同 job 重跑不會重複寄信、重複改狀態或重複同步。
- [ ] Readiness 在 DB 不可用／migration 落後時失敗。

### 多語與 SEO

- [ ] `/zh-TW` 所有內鏈保留 locale。
- [ ] 缺翻譯時公開策略明確，不混合語言或錯回英文。
- [ ] 每個 indexable 頁有正確 canonical、hreflang、x-default。
- [ ] Sitemap 含所有 published locale variants，使用真實 updated_at。

### 產品與數據

- [ ] RFQ、qualified、quoted、won funnel 使用同一 cohort 定義。
- [ ] Revenue／currency／CRM outcome 可對帳。
- [ ] Starter API 不能使用 Professional 功能。
- [ ] AI unavailable 顯示 unavailable，不回傳假 confidence／假分數。

### 上市與交付

- [ ] CI 全綠才可部署；artifact 不在 production 現場重建。
- [ ] npm production High=0；Python CVE scan 已納 CI。
- [ ] backup、restore、rollback 已實際演練。
- [ ] 所有對外成效、AI、ISO、GDPR 文案都有證據與 owner。

## 13. 建議決策

短期最有價值的策略不是擴充更多 AI 或整合，而是把 ForgeBase 收斂成一個可信的 RFQ Growth OS：

- 網站內容由人負責，系統負責結構、發布、追蹤與轉換。
- AI 只在有邊界、有額度、有 schema、有人工確認時協助。
- 所有 growth insight 必須能追溯到可信事件與商業 outcome。
- 所有多租戶資料存取預設拒絕，不依開發者記得加 filter。
- 所有對外承諾都以可量測、可驗證、可稽核為前提。

完成 P0 與關鍵 P1 後，ForgeBase 有條件成為可收費的垂直 SaaS；在此之前，最合適的使用方式是受控 demo 與少量 design partner 試點，而不是公開自助式上線。
