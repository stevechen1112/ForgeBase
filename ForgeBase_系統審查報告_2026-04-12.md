# ForgeBase 系統與資安審查報告

審查日期：2026-04-12

審查方式：靜態程式碼審查、架構文件抽樣、關鍵流程抽樣、測試與錯誤盤點、資安風險盤點。

審查範圍：

- API（FastAPI / SQLModel / Alembic）
- Web（Next.js）
- Admin（Next.js）
- 追蹤、RFQ、Chat、Intake、多租戶、品牌與部署相關模組

本文件僅為審查報告，不包含修復與程式碼更動。

補充說明：

- 本文件已包含資安審查內容。
- 本次資安審查屬於靜態與架構層審查，不等同於滲透測試、弱掃、紅隊演練或正式第三方資安驗證。

---

## 一、總結判斷

ForgeBase 已具備明確的產品方向與相當完整的功能骨架，不是只有展示型網站，而是朝「外銷製造商 RFQ 成長系統」的方向建構，包含 Capture、Intent、Conversion 三層能力。

但若以正式 SaaS 產品標準來看，目前最大的風險不在 UI，而在以下三件事：

1. 多租戶隔離不足
2. 資料可靠性與可觀測性不足
3. 關鍵轉換入口缺少抗濫用保護

整體判斷：

- 若當作單一品牌站或內部 demo 系統，已具備相當可用性。
- 若當作真正可對外販售的 multi-tenant SaaS，尚未達到穩定可擴張的狀態。

---

## 二、Critical 級問題

### 1. Legacy Site Intake 沒有完整 tenant 隔離

高風險檔案：

- `api/app/models/intake.py`
- `api/app/api/v1/endpoints/intake.py`

問題描述：

- `IntakeProject` 模型沒有 `tenant_id`
- Intake 專案讀取、更新、discover、extract 等端點沒有 tenant filter
- 目前是以 project id 直接存取

風險：

- Tenant A 可能讀到或操作 Tenant B 的 intake project
- 舊站匯入資料、抽取結果、審核流程存在跨租戶污染風險

影響判定：

- 這是 SaaS 級 blocking issue

---

### 2. Site Profile 是全域單例，非 tenant-scoped

高風險檔案：

- `api/app/models/site_profile.py`
- `api/app/api/v1/endpoints/site_profile.py`

問題描述：

- SiteProfile 目前是單一全域資料列的設計
- `GET /site-profile` 與 `PUT /site-profile` 都未以 tenant 區隔

風險：

- 一個 tenant 的品牌名稱、logo、theme、聯絡資訊會覆蓋其他 tenant
- 白標與 demo 場景非常容易互相污染

影響判定：

- 若產品定位是多客戶系統，這是核心架構問題

---

### 3. Redirect 規則是全域的，不適合多租戶

高風險檔案：

- `api/app/models/redirect.py`
- `api/app/api/v1/endpoints/redirects.py`

問題描述：

- Redirect 模型沒有 `tenant_id`
- `from_path` 是全域唯一鍵
- CRUD 端點沒有 tenant 限制

風險：

- Tenant A 的 SEO redirect 可影響 Tenant B
- 多品牌部署時會出現路由與 SEO 汙染

影響判定：

- 與 SiteProfile 問題一起看，代表多租戶設計尚未真正閉環

---

### 4. PageBrief / AI 內容生成也缺少 tenant 邊界

高風險檔案：

- `api/app/models/page_brief.py`
- `api/app/api/v1/endpoints/ai_generate.py`

問題描述：

- `PageBrief` 沒有 tenant_id
- AI 生成端點直接以 `brief_id` 取資料

風險：

- 不同 tenant 之間可能互相讀寫或觸發 AI 成本
- 內容生成結果可能對錯 tenant 生效

影響判定：

- 這會直接影響 AI 成本、資料正確性與客戶隔離

---

## 三、高優先技術債與可靠性問題

### 1. API fallback 設計可能讓前台長時間輸出空資料

高風險檔案：

- `web/src/lib/api.ts`

問題描述：

- 會先對 API 做 health check
- `apiAvailabilityPromise` 被快取後，若首次失敗，後續請求會直接走 fallback
- fallback 後頁面可能正常回 200，但內容是空資料或預設資料

風險：

- 暫時性的 API 抖動可能被放大成整個前台進程長時間輸出錯誤內容
- 監控不一定能立即看出問題
- SEO 也可能抓到空白或 fallback 頁面

---

### 2. 追蹤事件離線佇列存在資料遺失風險

高風險檔案：

- `web/src/lib/analytics.ts`
- `api/app/api/v1/endpoints/events.py`

問題描述：

- 前端 queue 最多保留 50 筆
- flush 時先刪 localStorage，再送 batch
- 後端 batch 上限只有 20 筆

風險：

- 若離線累積事件超過 20 筆，或 batch 傳送失敗，資料可能直接遺失
- intent scoring、漏斗分析、CTA 成效判斷會變得不可信

---

### 3. 關鍵 side effects 失敗被靜默吞掉

高風險檔案：

- `api/app/api/v1/endpoints/contacts.py`
- `api/app/api/v1/endpoints/rfqs.py`
- `api/app/api/v1/endpoints/events.py`

問題描述：

- webhook、通知、HubSpot、事件後處理等失敗時，多處使用 `except Exception: pass`

風險：

- 表單看似成功，但後續營運流程可能根本沒接住
- 容易形成「漏單但無告警」

---

### 4. Chat 與 analytics 身分識別邏輯重複實作

高風險檔案：

- `web/src/lib/analytics.ts`
- `web/src/components/chat/ChatWidget.tsx`

問題描述：

- visitor_id / session_id 在 analytics 與 chat widget 各自實作一套
- cookie 與 sessionStorage policy 不完全共用

風險：

- visitor attribution 容易分裂
- chat、tracking、RFQ handoff 可能無法完全對齊同一訪客旅程

---

### 5. 品牌預設值與殘留字串仍偏硬編碼

高風險檔案：

- `web/src/lib/siteConfig.ts`
- `web/src/lib/demoAssets.ts`
- `web/src/app/favicon.ico/route.ts`
- `web/src/app/careers/page.tsx`

問題描述：

- 仍存在 `NorthForge Tools`、`northforgetools.com`、`northforge` 類型預設值
- 某些頁面與 demo asset 命名仍帶舊品牌殘留

風險：

- 白標站、demo tenant、臨時展示環境容易殘留錯誤品牌資訊
- onboarding 難以完全自動化

---

### 6. Intake 腳本工具鏈維護性不足

高風險檔案：

- `api/scripts/intake_pipeline_king_a.py`
- `api/app/services/intake_engine.py`

問題描述：

- 目前靜態分析可見 unresolved import 問題
- 依賴執行時手動調整 `sys.path`

風險：

- IDE、CI、部署或腳本重構時容易出現不可預期問題
- 這些腳本能跑，不代表它們是穩定可維護的模組化工具

---

## 四、安全與營運風險

### 1. 公開入口缺少 anti-abuse 防護

高風險檔案：

- `api/app/api/v1/endpoints/auth.py`
- `api/app/api/v1/endpoints/contacts.py`
- `api/app/api/v1/endpoints/rfqs.py`

問題描述：

- login / register / contact / RFQ 都是公開入口
- repo 中沒有看到 rate limit、captcha、honeypot、Turnstile 等保護

風險：

- 容易遭受暴力嘗試、spam 表單、垃圾 RFQ、假訪客事件污染

---

### 2. 開放註冊策略偏危險

高風險檔案：

- `api/app/api/v1/endpoints/auth.py`

問題描述：

- 若未設定 `REGISTRATION_KEY`，系統允許 open registration

風險：

- 只要部署設定失誤，就可能被任意註冊 tenant 與帳號

---

### 3. 加密主金鑰有 dev fallback

高風險檔案：

- `api/app/core/encryption.py`

問題描述：

- 若未設定 `ENCRYPTION_MASTER_KEY`，會從 `SECRET_KEY` 派生 fallback key

風險：

- 本機開發可接受，但 production 容易因環境設定失誤留下弱點

---

## 五、產品層缺漏

### 1. 多租戶產品承諾與實際資料模型尚未對齊

目前產品明顯朝 SaaS 化、白標化、多客戶化發展，但以下核心資料仍未完全 tenant-scoped：

- IntakeProject
- SiteProfile
- Redirect
- PageBrief
- 部分 chat / tracking session 關聯

這意味著產品宣稱與架構實況之間仍有落差。

---

### 2. 營運可觀測性不足

作為 RFQ 成長系統，真正重要的不只是「表單送出成功」，而是：

- 是否有通知出去
- 是否有 CRM 同步成功
- 是否有 webhook 成功送達
- 是否有 routing 正確指派
- 是否有追蹤事件完整寫入

目前這些鏈路失敗時，系統可觀測性不足，營運層會很難快速定位問題。

---

### 3. 付費閉環成熟度需再確認

系統已有 plan、quota、PayPal subscription 相關結構，但從審查結果看，仍需要進一步確認以下是否完整閉環：

- 升級與降級實際是否影響 tenant 權限
- PayPal approval / activate / webhook 是否在真實環境完整驗證
- 付款失敗、取消、退款後的 plan 狀態是否正確回收

目前較像「已有能力骨架」，但離完全商業閉環仍需更嚴格驗證。

---

### 4. 前後台測試護欄不足

目前可見測試集中在 API 少數模組，web / admin 幾乎沒有自動化測試。

直接風險：

- i18n 回歸不易被攔下
- CTA、RFQ、chat handoff、SEO 頁面容易因修改出現非預期退化
- 多租戶資料邊界沒有被測試保護

---

## 六、測試與品質現況

目前可見測試檔案數量偏少，主要集中於：

- `api/tests/test_health.py`
- `api/tests/test_categories.py`
- `api/tests/test_chat.py`
- `api/tests/test_intake.py`
- `api/scripts/test_intake_king_a.py`

本次審查未看到：

- web 自動化測試
- admin 自動化測試
- tenant isolation 測試
- public form abuse 測試
- redirect / site profile 多租戶測試
- tracking queue 與 batch 一致性測試

結論：

- 自動化測試目前不足以保護核心產品邏輯

---

## 七、優先級建議

若以「是否值得繼續投資開發」來排序，建議優先級如下：

### P0

- 補齊 tenant isolation
- SiteProfile 改為 tenant-scoped
- Redirect 改為 tenant-scoped
- PageBrief / IntakeProject 補 tenant 邏輯

### P1

- 補公開入口 anti-abuse 保護
- 改善 side effects 的錯誤可觀測性
- 修正 tracking queue 與 batch 資料遺失風險

### P2

- 移除品牌殘留硬編碼
- 清理 onboarding / intake 腳本模組邊界
- 建立 web / admin 最基本 smoke tests

### P3

- 擴大產品體驗與商業閉環驗證
- 強化監控、告警、營運報表可靠性

---

## 八、最終結論

ForgeBase 不是空殼產品，已經有相當程度的功能深度，尤其在 RFQ、tracking、chat、content、SEO、admin workflow 的產品意圖上是明確的。

但它目前最需要面對的，不是再多做功能，而是先把「多租戶邊界、資料可靠性、營運觀測、公開入口防護」打穩。

若不先處理這些根問題，後續新增更多功能只會提高系統複雜度與維護成本，也會讓產品在真正對外時承受不必要風險。

---

## 九、資安審查補充

本章節補充說明本次審查中，已經涵蓋與尚未涵蓋的資安範圍，避免將一般技術債與正式資安問題混為一談。

### 1. 本次已涵蓋的資安面向

- 多租戶資料隔離
- 權限邊界與 tenant-scoped 設計
- 公開端點抗濫用能力
- 帳號註冊與登入入口風險
- webhook / side effects 的失敗處理與可觀測性
- 金鑰與憑證保護策略的風險訊號
- 品牌與 site profile 全域設計造成的跨租戶污染風險
- 追蹤事件與 visitor/session 關聯的資料完整性風險

### 2. 本次資安審查的主要結論

#### A. 多租戶隔離是目前最大的資安問題

從 SaaS 資安角度看，最嚴重的不是單一表單驗證，而是 tenant boundary。

目前下列模組仍有明顯的 cross-tenant 風險：

- IntakeProject
- SiteProfile
- Redirect
- PageBrief
- 部分 chat / tracking session 關聯

這類問題一旦成立，其風險層級通常高於一般 XSS 或表單驗證瑕疵，因為它直接影響客戶資料隔離與商業信任。

#### B. 公開入口抗濫用能力不足

目前 repo 中未看到完整的：

- rate limiting
- CAPTCHA / Turnstile
- honeypot
- login attempt throttling
- registration abuse protection

因此以下入口都有被濫用的可能：

- login
- register
- contact form
- RFQ form
- tracking event ingestion

這不只是安全問題，也會直接污染營運數據與 sales funnel。

#### C. 失敗不可見本身就是安全與營運風險

多處使用 `except Exception: pass`，雖然可避免主流程中斷，但也造成以下風險：

- webhook 送失敗但無法及時發現
- CRM / HubSpot 同步失敗但業務不一定知道
- routing / notification 失敗時沒有足夠追蹤線索

這類問題在資安分類中常落在 detection / monitoring / incident response 不足，而不只是程式風格問題。

#### D. 機密與加密設計仍需 production hardening

目前看到的明顯風險訊號：

- `ENCRYPTION_MASTER_KEY` 未設定時會 fallback 到由 `SECRET_KEY` 派生的 key
- 若 production 環境設定鬆散，會讓「本來只該存在於開發環境的容錯邏輯」流入正式環境

這不一定代表當下已被攻破，但代表 security posture 還不夠硬。

### 3. 本次尚未完整覆蓋的資安範圍

以下項目本次沒有做成完整獨立審查，因此不應宣稱已完成正式資安驗證：

- OWASP Top 10 全項對照
- JWT / refresh token 全生命週期安全性驗證
- CSRF 風險逐頁驗證
- SSRF / command injection / template injection 深度測試
- 檔案上傳與外部 URL 擷取的惡意內容驗證
- 第三方套件弱點掃描與供應鏈審查
- 依賴版本 CVE 盤點
- 正式弱點掃描
- 滲透測試
- production infra hardening 驗證

### 4. 目前的資安成熟度判斷

若以成熟度分層來看：

- 作為單一 tenant 或 demo 系統：可接受，但仍有公開入口防護不足問題。
- 作為多客戶 SaaS：目前不建議視為已完成資安就緒。
- 若要對外商業化上線：至少需先補完 P0 的 tenant isolation 與 P1 的 anti-abuse / observability。

---

## 十、資安上線判定

若以「能不能安全地作為正式 multi-tenant SaaS 對外提供」來判定，結論是：

### 目前不建議直接宣稱已通過資安準備

原因如下：

- 多租戶隔離尚未收斂
- 公開入口缺少足夠 anti-abuse 保護
- 部分關鍵整合失敗時過於靜默
- 自動化測試不足以保護授權與隔離邊界

### 目前較合理的定位

- 可作為產品原型 / demo / 單租戶內部驗證系統
- 不宜直接視為已完成商業級資安準備的 SaaS 平台

### 建議對外說法

- 可以說已完成初步系統與架構審查
- 不應說已完成完整資安驗證
- 若要對外募資、售前、合作或正式上線，應再補正式資安盤點與驗證流程