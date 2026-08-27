# ForgeBase 多租戶網站交付 SOP

> 代管式客戶網站的逐案執行與簽核，請搭配
> `FORGEBASE_MANAGED_SITE_DELIVERY_CHECKLIST_2026-08-15.md`。本 SOP 不代表客戶可自行修改版型或發布整站。

- 版本：2026-08-15
- 適用階段：受控對外測試，不含自助購買或全自動架站
- 已驗證案例：NorthForge Tools、AxisForm Precision（虛構測試租戶）

## 一、交付原則

1. 每個正式串接網站都必須有獨立 `Tenant`、owner、`SiteProfile`、`SiteBuild`、公開 host 與內容資料。
2. 範本只是設計起點。只有具 CMS adapter 且通過 readiness 的範本可發布；靜態 Demo 不得標成已串接網站。
3. 品牌、文案、圖片、內容、訪客、Chat、RFQ、任務與 outcomes 都必須依 tenant 隔離。
4. 測試公司、能力與證書必須醒目揭露為虛構資料；不得暗示真實工廠、法人或認證。
5. 受控測試預設不寄信、不啟用自動回覆、不把測試詢價當真實 lead。

## 二、交付輸入清單

交付前由平台管理員取得並人工確認：

- 公司名稱、聯絡方式、正式網域與預設語系。
- 範本選擇與允許的有限客製範圍。
- 產品分類、產品、應用、能力、FAQ、證書與頁面資料。
- 圖片與文件的權利、真實性、有效期與公開範圍。
- RFQ 收件欄位、SLA、負責人及是否允許寄信。
- Analytics／Chat／RFQ consent 與資料保留政策。

## 三、標準交付流程

1. 建立 tenant 與 owner；密碼不得寫入原始碼、文件或終端輸出。
2. 建立 `SiteProfile`：品牌、theme、layout、site URL、資產根目錄與 tenant 文案樹。
3. 建立 `SiteBuild`：範本、primary domain、語系、客製資料與 CMS adapter 狀態。
4. 匯入經人工確認的內容與素材，確認所有公開關聯都屬於同一 tenant。
5. 執行 readiness：owner、品牌、聯絡信箱、site URL、domain 一致、語系、範本與 adapter 必須全數通過。
6. 在 staging／測試 host 完成桌面、行動、主要頁面、Chat、RFQ 與後台流程驗收。
7. 執行完整測試與 production build；檢查 secret、破圖、404、fallback 文案與跨租戶資料。
8. 更新 DNS／Caddy、執行 migration、佈署專屬 web build，再執行公開 smoke test。
9. 建立發布映像回復點，完成服務停止／復原演練並記錄結果。
10. 只有在驗收紀錄完整後，才把 `SiteBuild` 保持為 `published`。

## 四、AxisForm 重現命令

AxisForm 是第二個完整動態租戶，用來證明 ForgeBase 不只支援 NorthForge。它使用測試專用網域：

- `https://axisform.172-233-64-5.sslip.io`
- tenant slug：`axisform-precision`
- template：`precision-machining`

在 API 容器內執行以下冪等腳本即可建立或修正資料：

```bash
python scripts/provision_axisform_precision.py
```

公開交付驗證：

```bash
python deploy/verify-multitenant-delivery.py --concurrency 100
python deploy/verify-multitenant-delivery.py --concurrency 100 --exercise-conversions
```

完成 synthetic RFQ 後，在 API 容器內關閉測試 outcome：

```bash
python scripts/verify_axisform_closed_loop.py --email forgebase-axisform-e2e+TIMESTAMP@example.com
```

## 五、發布 Gate

以下任一項未通過就不得發布：

- `alembic upgrade head` 失敗或 migration head 不一致。
- tenant owner、site URL、primary domain、語系或 adapter readiness 未通過。
- 跨 tenant 讀寫沒有回傳 404／403，或相同 model／email 出現在錯誤 tenant。
- 首頁、產品、應用、品質、聯絡、RFQ 或資產 health 非 200。
- tenant 文案或素材出現另一租戶品牌。
- 自動測試、lint、type-check 或 production build 失敗。
- 未確認 auto-reply／ESP 是否符合本次測試政策。
- 沒有可辨識的映像回復點或復原命令。

## 六、網域與部署注意事項

- 每個 public host 都要明確綁定 tenant，不依賴使用者自行傳入 tenant ID 決定網站身份。
- Next.js 的 tenant slug、canonical URL 與 base path 目前是 build-time 設定，因此每個 connected tenant 使用獨立 web image／service。
- Caddyfile 是 bind mount；檔案同步後必須用全新 Caddy 容器驗證，再 force-recreate Caddy，不能只假設 reload 讀到新 inode。
- 正式 API 固定單 worker 執行 scheduler；水平擴展前需拆獨立 worker 或加入 distributed lock。
- 資料庫 schema rollback 需人工審核；一般網站發布優先用 application image rollback。

## 七、回復流程

1. 確認故障只在單一 tenant web、共用 API、Caddy 或資料庫。
2. 單一網站故障時先切回該 web service 的前一個已驗證 image，不動其他租戶。
3. API 故障時檢查 migration 相容性後再切回應用 image。
4. Caddy 變更先驗證設定，再 force-recreate；不得在未驗證時覆蓋目前可用路由。
5. 回復後重跑 tenant profile、內容隔離、資產 health、主要頁面與 RFQ challenge smoke test。

## 八、目前仍非自動化的部分

- 客戶網域 DNS 與憑證確認。
- 範本文案／圖片／內容的人工適配與真實性審核。
- 第三方 ESP、CRM、公司辨識與聯絡人 enrichment 的帳號配置。
- 外部測試公司的招募、同意、真實回饋與商業成效判讀。

這些是受控交付工作，不應在銷售上描述為「客戶自行點選後立即完成架站」。
