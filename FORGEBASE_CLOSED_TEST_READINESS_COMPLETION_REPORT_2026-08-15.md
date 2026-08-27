# ForgeBase 封閉測試就緒完成報告

- 完成日期：2026-08-15
- 正式環境：Linode `172.233.64.5`
- ForgeBase 官網：`https://pcbrm.tw/`
- NorthForge：`https://pcbrm.tw/northforge-tools/`
- 第二動態租戶：`https://axisform.172-233-64-5.sslip.io/`
- 後台：`https://pcbrm.tw/backend/login`

## 一、結論

ForgeBase 已完成進入「指定租戶、人工監督、不對測試詢價回信」封閉測試所需的本輪工程工作。

本次不只新增第二個畫面，而是讓 AxisForm Precision 具備獨立 tenant、owner、SiteProfile、SiteBuild、host、品牌文案、CMS 內容、圖片、AI Advisor、訪客、Chat、RFQ、任務與 outcome。它與 NorthForge 共用同一 API／PostgreSQL，但公開與轉換資料均受 tenant 邊界保護。

這不代表 ForgeBase 已可自助購買、保證 leads 或正式商用。IP 公司辨識、ESP、CRM、AgentOS 等真實第三方整合，以及外部受測者招募與真實成效，仍是下一階段工作。

## 二、本次完成項目

### 第二個完整動態租戶

- 建立 `axisform-precision` tenant 與隨機密碼 owner。
- `precision-machining` 成為第二個 `cms_connected=true` adapter。
- 新增 precision theme、header、footer、首頁 layout 與 tenant copy adapter。
- 建立 2 分類、3 產品、3 應用、3 能力、2 個虛構品質紀錄、4 FAQ、CTA 與頁面。
- 所有公司、產品、產能與品質內容均揭露為虛構測試資料。
- `auto_reply_enabled=false`，不執行測試詢價回信。

### 白牌與資料隔離

- `SiteProfile.site_copy_json` 讓租戶可覆寫完整前台訊息樹，不只換 logo／顏色。
- 修正產品 CTA 語系，英文站不再出現中文個人化文字。
- 修正 AxisForm Chat greeting／suggestions，不再出現不適合精密加工的 OEM 手工具問題。
- 修正 Contact／RFQ 成功訊息、欄位與 placeholder，不再出現 NorthForge 的工具、包裝或回覆承諾。
- 新增 tenant-scoped asset route；改寫另一 company folder 會得到 404。

### 部署與可靠性

- 新增 `web_precision` 獨立 image／service 與 test-only sslip.io TLS host。
- migration 已升至 `0067_site_profile_tenant_copy`。
- Caddy 修正 `/api/health/*` 路由優先序；兩個 Web 的 asset health 都由正確服務處理。
- AgentOS 未配置時以空值乾淨跳過，不再錯誤呼叫 `localhost:8000/tasks` 並產生 retry。
- 建立 API、NorthForge Web、AxisForm Web release tags。
- 完成 AxisForm service stop／recovery：停止時 AxisForm 為 502，ForgeBase 官網、NorthForge 與 API 持續可用；AxisForm 8 秒內恢復 healthy／200。

## 三、自動化驗證

| 驗證 | 結果 |
|---|---|
| API 完整 PostgreSQL 測試 | **159 passed, 2 skipped** |
| Web lint | 通過 |
| Web TypeScript | 通過 |
| Web production build | 通過 |
| Production migration | `0067_site_profile_tenant_copy (head)` |
| SiteBuild readiness | 9 項檢查全通過 |
| Profile／model 隔離 | 通過 |
| 跨租戶 Chat 寫入 | 404，通過 |
| Asset health | `ok`，0 missing／0 problem |
| 100 併發公開 GET | 0 failure；最終 4.401 秒、22.7 req/s |
| Production dependency audit | production dependency 0 vulnerability；npm 顯示的 4 high 均在 dev dependency |

100 併發結果是本次 smoke baseline，不代表容量上限或 SLA。

## 四、正式瀏覽器驗收

以實際瀏覽器完成：

- AxisForm 首頁、產品總覽、分類、產品詳情、應用、應用詳情、品質、品質詳情、About、Contact 與 RFQ。
- 所有檢查頁面 0 broken image；首頁 disclosure、虛構品質說明與 no-sales-follow-up 可見。
- 產品 `DEMO-M01` 正確顯示 `Al 6061`、`±0.015 mm` 與英文動態 CTA，沒有中文洩漏。
- AI grounded 問題正確回答 DEMO-M01 材質／公差。
- AI 面對「保證每週一百萬件與 ISO 13485」時明確表示證據不足，不自行聲稱能力或認證。
- NorthForge 繁中頁 `lang=zh-TW`，中文提問得到中文回答，圖片正常。
- AxisForm UI 成功送出 `RFQ-20260815-002`；畫面顯示 test-only 與不回信說明。

## 五、轉換閉環證據

`RFQ-20260815-002` 的驗收結果：

- quality score：100。
- contact／RFQ 錄入 AxisForm tenant；錯誤 tenant record：0。
- 建立 7 個 durable jobs：routing、notification、HubSpot adapter、AgentOS adapter、webhook、Copilot、auto-reply。
- 已配置的內部／no-op adapter 正常完成；auto-reply 因租戶設定停用且沒有聯繫行為。
- 最終 outcome：`won-test-only`，僅驗證漏斗，不代表真實 lead、報價或訂單。

## 六、交付文件

- `FORGEBASE_MULTI_TENANT_DELIVERY_SOP_2026-08-15.md`
- `FORGEBASE_CLOSED_TEST_PROTOCOL_2026-08-15.md`
- `FORGEBASE_FUNCTION_MODULE_COMPLETENESS_AUDIT_2026-08-15.md`

完整度重新評估：

- 第一層：84%。
- 第二層：61%（未因本輪虛增）。
- 平台基礎：88%。
- 全產品加權技術完整度：76.03%，四捨五入 **76%**。

## 七、尚未完成但不屬於本輪可單方面完成的工作

- 邀請 3–5 家外部公司／測試者並取得真實回饋。
- 設定真實 IP company／person enrichment provider。
- 驗證 ESP、CRM、GSC、R2、AgentOS 等第三方 sandbox／正式帳號。
- 公開未知流量前配置 Turnstile，並執行長時間 soak、滲透、法務與隱私驗證。
- 累積足夠真實樣本後再定義 qualified lead、去重、歸因、爭議與 by-lead 計費。

因此下一個產品工作不應再擴張一般功能，而應按封閉測試計畫招募受測者、蒐集真實使用證據，並只針對觀察到的失敗修正。
