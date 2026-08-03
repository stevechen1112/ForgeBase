# ContentFlow ↔ ForgeBase Publish API Contract

確認日期：2026-08-03  
狀態：草稿（實作前簽核）  
上位計畫：[CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md](./CONTENTFLOW_FORGEBASE_INTEGRATION_PLAN.md) §3.1  
主策略：[DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md](./DIGITAL_MARKETING_LEAD_GROWTH_STRATEGY.md)

**產品前提：** ContentFlow 與 ForgeBase 為**獨立產品**、各自租戶；本契約僅約束**已啟用串接**的 CF project → FB tenant 發佈路徑。未串接租戶不受本契約約束。CF 可同時服務 WordPress／Generic 等其他發行目標。

本契約定義 ContentFlow（客戶端）呼叫 ForgeBase API（服務端）發佈／更新 `blog_post` 時的行為。欄位以現行 ForgeBase `PageCreate` / `PageUpdate` / `PageBriefCreate` 為準；標「待實作」者為串接 Phase 必補。

---

## 1. 認證與租戶

| 項目 | 規範 |
|------|------|
| Header | `X-API-Key: <token>` |
| 對照 | ForgeBase `SERVICE_ACCOUNT_TOKENS=<token>:<user_id>` |
| 租戶 | token 對應 user 的 `tenant_id`；寫入一律落在該 tenant |
| 禁止 | 多租戶共用同一 token；以 API host 推斷公開站網址 |

跨租戶寫入必須失敗（`403` 或資源 `404`），不得靜默寫入他戶。

---

## 2. 公開 URL 與 locale

| 項目 | 規範 |
|------|------|
| `site_url` | 官網公開源，例如 `https://www.client.com`（來自租戶矩陣，非 `api_base`） |
| `api_base` | 例如 `https://api.client.com` 或內部 API URL |
| 預設公開路徑 | `{site_url}/blog/{slug}`（`locale=en`） |
| 其他語系 | `{site_url}/{locale}/blog/{slug}` |
| CF 回寫 `publish_url` | 必須為公開路徑，禁止拼 API host |
| 試點預設 locale | `en`（外銷）；禁止 publisher 寫死 `zh-tw` |

Slug 規則（與 FB schema 一致）：`^[a-z0-9]+(?:[/-][a-z0-9]+)*$`，建議 blog 僅用小寫連字號，避免與產品路徑衝突。

---

## 3. 端點一覽

Base：`{api_base}/api/v1`

| 動作 | Method / Path | 狀態 |
|------|---------------|------|
| Health／探測 | `GET /content/pages?limit=1` | 已有 |
| 建立 Brief | `POST /content/briefs` | 已有 |
| 建立 Page（草稿） | `POST /content/pages` | 已有 |
| 讀取 Page | `GET /content/pages/{id}` | 已有 |
| 更新 Page | `PATCH /content/pages/{id}` | 已有 |
| 發佈 | `POST /content/pages/{id}/publish` | 已有 |
| 下架 | `POST /content/pages/{id}/unpublish` | 已有 |
| 依 slug 查詢 | `GET /content/pages?slug=&locale=&page_type=blog_post` | ✅ 已驗證（2026-08-03）；帶有效憑證時以 caller tenant 查詢 |
| Meta-only 語意 | `PATCH /content/pages/{id}/meta`（專用端點，僅 seo_title／seo_description／og_image_url／canonical_url，夾帶其他欄位 422） | ✅ 已實作（2026-08-03） |
| Revalidate | FB 後端於 publish／update（已發佈頁）／meta／unpublish 後自動呼叫 web `POST /api/revalidate`；環境變數 `WEB_REVALIDATE_URL`＋`WEB_REVALIDATE_SECRET`（web 端為 `REVALIDATE_SECRET`） | ✅ 已實作（2026-08-03），需部署時設定環境變數 |
| Redirect | 既有 redirects API | 已可用：service account token 走 `get_current_user` 即通過 |

---

## 4. 欄位對照

### 4.1 Brief（首發可建；refresh 勿重複堆）

```json
{
  "target_page_type": "blog_post",
  "target_slug": "export-torque-wrench-buyer-guide",
  "title_draft": "...",
  "primary_keyword": "...",
  "secondary_keywords": "[\"...\"]",
  "word_count_target": 1500,
  "locale": "en",
  "notes": "cf:article:123"
}
```

| CF | FB | 備註 |
|----|----|------|
| article title | `title_draft` | |
| primary_keyword | `primary_keyword` | |
| article id | **`notes`（定案，試點）** | 強制前綴 `cf:article:{id}`；正式欄位待後續 |

**Brief 策略（契約強制）：**

1. 該 `(tenant, locale, slug)` **尚無 page** → 可 `POST /briefs`，再 `POST /pages` 帶 `brief_id`。  
2. **已有 page**（refresh／重發）→ **禁止**新建 brief；`PATCH` 既有 page，沿用 `page.brief_id`。  
3. CF 以 `forgebase_id`（page id）為準做更新；若只有 slug，先 GET 查既有再決定 create vs patch。

### 4.2 Page Create / Update

```json
{
  "page_type": "blog_post",
  "slug": "export-torque-wrench-buyer-guide",
  "title": "...",
  "body": "<p>HTML...</p>",
  "hero_image_url": "https://cdn.example.com/....jpg",
  "og_image_url": "https://cdn.example.com/....jpg",
  "seo_title": "...",
  "seo_description": "...",
  "structured_data": "{...}",
  "canonical_url": "https://www.client.com/blog/export-torque-wrench-buyer-guide",
  "locale": "en",
  "status": "draft",
  "brief_id": "<uuid-or-omit-on-refresh>"
}
```

| CF | FB | 必填 |
|----|----|------|
| title | `title` | Y |
| slug | `slug` | Y |
| content HTML | `body` | Y（發佈前） |
| meta_title | `seo_title`（≤70） | 建議 |
| meta_description | `seo_description`（≤160） | 建議 |
| hero_image_url | `hero_image_url` | 建議（見媒體策略） |
| （可同 hero） | `og_image_url` | 建議 |
| faq_schema_json 等 | `structured_data` | 可選 |
| — | `canonical_url` | 建議由 CF 或 FB 依 site_url 填 |

`body`：Markdown 由 CF 轉 HTML 後送入。FB 必須 sanitize 後再存或再渲染。

### 4.3 Meta-only（低風險修復）

僅允許更新：

- `seo_title`
- `seo_description`
- （可選）`og_image_url`、`canonical_url`

不得在 meta 修復路徑改 `body`／`slug`／`page_type`。

成功後必須觸發該 path 的 revalidate。

### 4.4 關聯 ID 定案（2026-08-03）

| 階段 | 作法 |
|------|------|
| **試點（現行定案）** | Brief `notes` 使用 `cf:article:{contentflow_article_id}`；CF 仍以 `article.forgebase_id` = Page UUID 為更新主鍵 |
| **後續可選** | ForgeBase 新增 `pages.contentflow_article_id`（或 metadata JSON）再遷移，不阻塞試點 |
| 請求追蹤 | 建議 Header `X-Request-Id`（UUID），兩邊 log 留存 |

---

## 5. 流程

### 5.1 首發（draft → published）

```text
1. GET pages?slug&locale&page_type=blog_post
   - 若已存在 → 改走 5.2
2. POST /content/briefs
3. POST /content/pages  (status=draft, brief_id, hero, body, seo_*)
4. （顧問核准後）POST /content/pages/{id}/publish
5. POST revalidate  /blog/{slug} + /blog + sitemap
6. CF 寫回 forgebase_id = page.id, publish_url = {site_url}/blog/{slug}
```

### 5.2 Refresh／重發（idempotent）

```text
1. 以 forgebase_id 或 slug 定位既有 page
2. PATCH /content/pages/{id}  （全文；不新建 brief）
3. 若仍為 draft 且需上線 → publish
4. revalidate
5. 更新 CF publish_url（若 slug 變更則配合 redirect）
```

### 5.3 下架

```text
POST /content/pages/{id}/unpublish
→ revalidate
→ 前台 404 或 noindex；移出 sitemap
```

### 5.4 Slug 變更

```text
1. PATCH 新 slug 或建新 page（依實作選一，契約選定後寫死）
2. POST redirect: old path → new path
3. revalidate 舊新 path
```

建議試點：**禁止隨意改 slug**；若改，必須建 301。

---

## 6. 錯誤碼與重試

| HTTP | 含義 | CF 行為 |
|------|------|---------|
| 401 | 認證失敗 | 不重試；告警 |
| 403 | 租戶／權限 | 不重試；告警 |
| 404 | 資源不存在 | refresh 時改 create 或告警 |
| 409 | slug 衝突（他頁占用） | 改 slug 後重試一次，或人工 |
| 422 | 欄位驗證失敗 | 不重試；修 payload |
| 429 | 限流 | 指數退避重試 ≤3 |
| 5xx | 伺服器 | 指數退避重試 ≤3 |

Idempotency 鍵（✅ 已實作 2026-08-03）：Header `Idempotency-Key: cf-article-{id}-v{n}`；`POST /content/pages`（及其他 content POST）重送同 key 時回傳首次結果（同 page id），不重複建頁。紀錄存於 `idempotency_keys` 表（migration 0049）。

---

## 7. 媒體

| 規則 | 說明 |
|------|------|
| URL | 必須公開 HTTPS，FB／爬蟲可 GET 200 |
| Hero | Create／Update 應傳送；無圖時 verification 可標 `no_img` |
| 清空圖 | refresh 若要去圖，送空字串或 null（兩邊對齊後寫死） |
| 私有桶 | 禁止 |

---

## 8. 安全與快取

| 規則 | 負責 |
|------|------|
| HTML sanitize（禁 script／on*） | ForgeBase 寫入或渲染層 |
| 發佈／更新／meta／unpublish 後 revalidate | ForgeBase（CF 可再呼叫一次） |
| Log 不印完整 API Key | 雙方 |
| `contentflow_article_id` 可對帳 | CF notes／未來 FB 欄位；request 帶 `X-Request-Id` |

---

## 9. Capabilities（CF Publisher 應誠實宣告）

試點目標能力：

```json
{
  "create": ["blog_post"],
  "update": ["blog_post"],
  "update_meta": true,
  "unpublish": true,
  "redirect_301": true,
  "revalidate": true
}
```

未實作完成前，對應項必須為 `false`，避免 CF auto_remediate／merge 誤判。

---

## 10. 驗收（Contract 層）

FB 接收端已驗證（`api/tests/test_cf_publish_contract.py`，2026-08-03）：

- [x] A token 無法寫 B tenant（publish／meta 回 404）  
- [x] 同 slug 第二次發佈 = 同 page id（Idempotency-Key）；brief 數量不增加 → **CF 端流程驗證待補**  
- [x] slug+locale+page_type 查詢可用且 tenant 隔離  
- [x] XSS payload 被剝除（script／on*／javascript:）  
- [x] meta-only 不改 body；夾帶 body 回 422  

部署後待驗（需環境）：

- [ ] `publish_url` host = site_url（CF 端寫回邏輯）  
- [ ] hero 有值時前台圖 200  
- [ ] publish 後 60s 內前台非舊快取（需設定 `WEB_REVALIDATE_URL`／`REVALIDATE_SECRET`）  
- [ ] unpublish 後 sitemap 不含該 URL

---

## 11. 修訂紀錄

| 日期 | 變更 |
|------|------|
| 2026-08-03 | 初稿：對齊整合計畫 §3.1–3.4 |
| 2026-08-03 | 關聯 ID 定案（notes）；slug 查詢改 Phase 0 必測 |
| 2026-08-03 | **Phase 2a FB 接收端落地**：slug 查詢驗證通過（auth tenant 覆寫）、meta-only 專用端點、HTML sanitize、revalidate（FB→web）、Idempotency-Key（migration 0049）；驗收 §10 五項轉為已驗證 |
