# ForgeBase 外部系統完整串接教學

本文件的目的不是只列出「可以接哪些服務」，而是教你如何把 ForgeBase 串成一套真正能為 B2B 官網帶來名單、辨識意圖、啟動追蹤、推進成交、持續優化的系統。

如果你的目標是讓 ForgeBase 發揮最大效果，建議不要亂序上線，而是照下面這個順序做：

1. 先完成基礎資料與事件層
2. 再完成 Email / CRM / Webhook 等營運層
3. 再完成 Ads / LinkedIn 等再行銷與名單活化層
4. 最後補 Google Search Console 等 SEO 優化層

## 1. 先理解：ForgeBase 最佳效果來自什麼整合組合

ForgeBase 本身已經有自己的第一方追蹤、訪客意圖分級、AI 對話與 RFQ 流程，但如果沒有外部系統，很多能力只能停留在站內。

真正完整的效果通常是這樣形成：

- 網站事件由 ForgeBase 蒐集，並平行送到 GA4 與 Meta
- 訪客 IP 被解析成公司資訊，讓匿名流量逐步變成可判讀名單
- 聯絡表單、RFQ、對話接手結果同步到 CRM
- 已有名單同步到 Email 平台、LinkedIn、Google Ads 做 nurture 與再行銷
- 重要事件再透過 Webhook 推到 ERP、Slack、內部通知或其他中台
- SEO 表現由 Google Search Console 回灌到後台分析

如果只接其中一兩個系統，效果會是局部的；如果整條鏈接起來，ForgeBase 才會從「官網」變成「成交流水線前端」。

## 2. 目前程式內已實作的外部整合

依照目前程式碼，ForgeBase 已有或已預留下列整合能力：

- GA4
- Meta Conversions API
- Google Ads Customer Match
- LinkedIn Matched Audiences
- HubSpot CRM
- Salesforce CRM
- Resend
- SendGrid
- Mailchimp
- SMTP 通知
- Clearbit Reveal
- ip-api.com
- Google Search Console API
- Outbound Webhook

另外要先注意一件事：目前 api/.env.example 沒有完整列出所有整合所需環境變數。也就是說，很多整合能力程式裡有，但你不能只照 .env.example 填完就期待它會動。

## 3. 建議的上線順序

### 第一階段：基礎必接

- NEXT_PUBLIC_GA_MEASUREMENT_ID
- META_PIXEL_ID
- META_ACCESS_TOKEN
- ESP_PROVIDER + Resend 或 SendGrid
- SMTP_HOST / SMTP_USER / SMTP_PASSWORD
- WEBHOOK_ENDPOINT_URLS
- WEBHOOK_SECRET

這一層解決的是：

- 有沒有事件
- 有沒有信件
- 有沒有通知
- 有沒有可往外推的資料管道

### 第二階段：銷售營運必接

- HUBSPOT_API_KEY 或 Salesforce 一組完整憑證
- Clearbit Reveal
- ip-api.com 備援

這一層解決的是：

- 新名單有沒有進 CRM
- RFQ 有沒有變商機
- 匿名訪客能不能被辨識成公司

### 第三階段：再行銷與受眾活化

- Google Ads Customer Match
- LinkedIn Matched Audiences
- Mailchimp 或 SendGrid Marketing Contacts

這一層解決的是：

- 高意圖名單能不能回流到廣告平台
- 業務還沒成交的名單能不能持續 nurture

### 第四階段：SEO 持續優化

- Google Search Console API

這一層解決的是：

- 哪些頁面有曝光沒點擊
- 哪些關鍵字卡在第 6 到 20 名
- 哪些頁面互搶關鍵字

## 4. 你應該先準備哪些帳號與權限

在正式串接前，先準備以下外部帳號：

- Google Analytics 4 資源
- Google Ads 廣告帳戶與 Customer Match 名單
- Meta Business Manager、Pixel、System User Token
- LinkedIn Campaign Manager 廣告帳戶
- HubSpot Private App 或 Salesforce API 使用者
- Resend 或 SendGrid
- Mailchimp Audience
- Google Cloud Service Account 與 Search Console 權限
- Clearbit Reveal API Key
- 你的內部 Webhook 接收端，例如 n8n、Make、Zapier、Slack 中介服務或自建 API

如果公司內部還沒有這些帳號，你應該先決定誰是 owner。這不是技術細節，而是上線成敗的第一個卡點。

## 4.1 手把手：每一種外部資源到底怎麼拿

這一節不是講概念，而是直接告訴你要登入哪裡、按哪個區塊、最後要複製什麼值。

先講一個原則：

- 你要拿的不是「帳號本身」，而是「可被 ForgeBase 使用的識別碼、權杖、清單 ID、權限」
- 每完成一組，就立刻把值先存進密碼管理器或公司祕密管理系統，不要先貼在聊天工具
- 如果是需要其他部門協助的系統，你至少要先知道該找誰要什麼

### 4.1.1 GA4 Measurement ID

你要拿到的最終值：

- NEXT_PUBLIC_GA_MEASUREMENT_ID
- 格式通常是 G-XXXXXXXXXX

實際操作：

1. 用有編輯權限的 Google 帳號登入 https://analytics.google.com/
2. 左下角進入管理
3. 如果還沒有帳戶，先按建立 > 帳戶
4. 建完帳戶後，按建立 > 資源
5. 進入資料收集與修改 > 資料串流
6. 按新增串流 > 網站
7. 輸入網站網址與串流名稱
8. 進入串流詳情，複製評估 ID，也就是 G-XXXXXXXXXX

你應該看到的結果：

- 有一個網站資料串流
- 串流頁面可看到 G- 開頭的 Measurement ID

### 4.1.2 Meta Pixel ID 與 Conversions API Token

你要拿到的最終值：

- META_PIXEL_ID
- META_ACCESS_TOKEN

實際操作：

1. 用有完整控制權或至少可管理整合的帳號登入 https://business.facebook.com/
2. 先確認公司有商家資產管理組合，沒有的話先建立一個
3. 到事件管理工具 https://business.facebook.com/events_manager2/
4. 如果還沒有 Pixel，按連結資料來源 > 網站 > Meta Pixel，建立 Pixel
5. 建立後點進該 Pixel
6. 進入設定頁籤
7. 找到 Conversions API 區塊
8. 點手動設定或產生存取權杖
9. 依畫面指示完成，複製 Pixel ID 與 access token

你應該看到的結果：

- 事件管理工具裡有一個可用 Pixel
- 設定頁能看到 Pixel ID
- Conversions API 區塊能產生 token

### 4.1.3 Google Ads Developer Token、OAuth 與 Customer Match List

你要拿到的最終值：

- GOOGLE_ADS_DEVELOPER_TOKEN
- GOOGLE_ADS_CUSTOMER_ID
- GOOGLE_ADS_CLIENT_ID
- GOOGLE_ADS_CLIENT_SECRET
- GOOGLE_ADS_REFRESH_TOKEN
- GOOGLE_ADS_CUSTOMER_LIST_ID

實際操作分成四段，不要一次想拿完。

第一段，先拿 Developer Token：

1. 用 Google Ads 管理員帳戶登入 https://ads.google.com/
2. 確認你登入的是管理員帳戶，不是單一客戶帳戶
3. 開啟 API Center：https://ads.google.com/aw/apicenter
4. 填 API access 表單並送審
5. 等待頁面顯示 developer token

第二段，拿 OAuth client id / secret：

1. 進入 Google Cloud Console：https://console.cloud.google.com/
2. 建立新專案，或使用既有專案
3. 啟用 Google Ads API
4. 到 API 和服務 > 憑證
5. 建立 OAuth 用戶端 ID
6. 複製 client id 與 client secret

第三段，拿 refresh token：

1. 用剛才的 OAuth client 跑一次 OAuth 授權流程
2. 讓擁有 Google Ads 存取權的 Google 帳號授權
3. 在 OAuth 回傳結果裡取得 refresh token

第四段，拿 customer id 與 list id：

1. 在 Google Ads 後台找到你的 customer ID
2. 進入 Audience Manager 建立一個 Customer Match user list
3. 建好之後記下 user list ID

### 4.1.4 LinkedIn Access Token 與 Ad Account ID

你要拿到的最終值：

- LINKEDIN_ACCESS_TOKEN
- LINKEDIN_AD_ACCOUNT_ID

實際操作：

1. 登入 LinkedIn Campaign Manager
2. 確認你能進入目標廣告帳戶，不是只有 Viewer 權限
3. 先記下廣告帳戶 ID
4. 再確認你是用哪一個 LinkedIn 開發者應用程式來拿 token
5. 該應用程式需要至少有 r_ads 或 rw_ads 類型權限
6. 完成 OAuth 後，複製 access token

實務提醒：

- LinkedIn 這組通常不是行銷人員自己就能完成，常常要和開發者帳號管理人一起處理

### 4.1.5 HubSpot Private App Token

你要拿到的最終值：

- HUBSPOT_API_KEY
- 實際上這裡應放的是 Private App access token，不是舊式 API key

實際操作：

1. 用有 Super Admin 權限的 HubSpot 帳號登入
2. 進入 Development
3. 左側選 Legacy apps 或 Private apps
4. 按 Create private app
5. 填 app 名稱與說明
6. 到 Scopes 頁籤，勾選這個整合要用到的 CRM scopes
7. 建立 app
8. 進入 Auth 頁籤
9. 點 Show token
10. 複製 access token

### 4.1.6 Salesforce Connected App 與 API User

你要拿到的最終值：

- SF_CLIENT_ID
- SF_CLIENT_SECRET
- SF_USERNAME
- SF_PASSWORD
- SF_SECURITY_TOKEN
- SF_INSTANCE_URL

實際操作：

1. 用 Salesforce admin 身分登入 Setup
2. 搜尋 App Manager
3. 按 New Connected App
4. 填 App Name、API Name、Contact Email
5. 啟用 OAuth Settings
6. 設定 callback URL
7. 勾選 API 權限相關 scopes
8. 建立後進入 Consumer Details，取得 client id 與 client secret
9. 另外建立一個專用 API user，避免直接拿真人帳號串接
10. 取得該使用者的 username、password、security token
11. 記下 instance URL，例如 https://your-instance.my.salesforce.com

### 4.1.7 Resend API Key

你要拿到的最終值：

- RESEND_API_KEY

實際操作：

1. 登入 Resend Dashboard
2. 進入 API Keys：https://resend.com/api-keys
3. 按 Create API Key
4. 輸入名稱
5. 選 Full access 或 Sending access
6. 建立後立刻複製 API key
7. 到 Domains 完成寄件網域驗證

### 4.1.8 SendGrid API Key

你要拿到的最終值：

- SENDGRID_API_KEY

實際操作：

1. 登入 SendGrid
2. 左側進入 Settings > API Keys
3. 按 Create API Key
4. 輸入名稱
5. 選 Full Access 或 Custom Access
6. 按 Create & View
7. 立刻複製 API key
8. 完成 sender 或 domain 驗證

### 4.1.9 Mailchimp Audience 與 API Key

你要拿到的最終值：

- MAILCHIMP_API_KEY
- MAILCHIMP_AUDIENCE_ID

實際操作：

1. 登入 Mailchimp
2. 先建立 Audience
3. 建完後進入 Audience settings，找到 Audience ID
4. 再到帳號的 API keys 區域建立 API key
5. 複製整串 key

注意：

- 你的程式目前不需要單獨填 MAILCHIMP_SERVER_PREFIX
- Mailchimp data center 已經包含在 API key 尾碼，例如 us21

### 4.1.10 Google Search Console Service Account 與站點權限

你要拿到的最終值：

- GSC_SERVICE_ACCOUNT_KEY_JSON
- GSC_SITE_URL

實際操作：

1. 到 Google Cloud Console 建立專案
2. 啟用 Search Console API
3. 建立 Service Account
4. 下載 JSON key
5. 打開 Search Console：https://search.google.com/search-console
6. 進入對應網站資產
7. 到設定 > 使用者和權限
8. 把 service account email 加進去，至少給完整權限使用者
9. 把 JSON 內容轉成單行字串後存進環境變數
10. GSC_SITE_URL 要和 Search Console 資產 URL 完全一致

### 4.1.11 Clearbit Reveal API Key

你要拿到的最終值：

- CLEARBIT_API_KEY

實際操作：

1. 到 Clearbit 官方後台申請 Reveal 或 Company API 存取
2. 完成方案開通後，到 API key 區塊建立或複製 key

### 4.1.12 Webhook 測試接收端

你要拿到的最終值：

- 一個或多個 WEBHOOK_ENDPOINT_URLS
- 一組 WEBHOOK_SECRET

最快的做法：

1. 臨時測試就用 webhook.site
2. 流程型測試就用 n8n / Make / Zapier webhook trigger
3. 公司正式環境就準備自家 API endpoint

## 5. 建議直接補進 API 環境變數的整合區塊

下面這份清單可以當作你自己的 api/.env 擴充模板。這不是從 .env.example 複製來的，而是依照目前實際程式碼整理出來的。

```env
# =========================
# Analytics / Ads
# =========================
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
META_PIXEL_ID=123456789012345
META_ACCESS_TOKEN=your_meta_system_user_token

GOOGLE_ADS_DEVELOPER_TOKEN=your_google_ads_developer_token
GOOGLE_ADS_CUSTOMER_ID=1234567890
GOOGLE_ADS_CLIENT_ID=your_google_oauth_client_id
GOOGLE_ADS_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_google_oauth_refresh_token
GOOGLE_ADS_CUSTOMER_LIST_ID=987654321

# =========================
# LinkedIn
# =========================
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
LINKEDIN_AD_ACCOUNT_ID=123456789

# =========================
# CRM
# =========================
HUBSPOT_API_KEY=your_hubspot_private_app_token
HUBSPOT_PORTAL_ID=optional

SF_CLIENT_ID=your_salesforce_connected_app_client_id
SF_CLIENT_SECRET=your_salesforce_connected_app_client_secret
SF_USERNAME=api-user@example.com
SF_PASSWORD=your_salesforce_password
SF_SECURITY_TOKEN=your_salesforce_security_token
SF_INSTANCE_URL=https://your-instance.my.salesforce.com

# =========================
# Email / ESP
# =========================
ESP_PROVIDER=resend
EMAIL_FROM_NAME=ForgeBase
EMAIL_FROM=no-reply@example.com

RESEND_API_KEY=your_resend_api_key
SENDGRID_API_KEY=your_sendgrid_api_key

MAILCHIMP_API_KEY=your_mailchimp_api_key
MAILCHIMP_AUDIENCE_ID=your_mailchimp_audience_id

# =========================
# SMTP Notifications
# =========================
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=smtp-user@example.com
SMTP_PASSWORD=your_smtp_password
SMTP_FROM=alerts@example.com

# =========================
# IP / Company Enrichment
# =========================
CLEARBIT_API_KEY=your_clearbit_api_key

# =========================
# SEO / GSC
# =========================
GSC_SERVICE_ACCOUNT_KEY_JSON={...json string...}
GSC_SITE_URL=https://yourdomain.com/

# =========================
# Webhooks
# =========================
WEBHOOK_ENDPOINT_URLS=https://hooks.example.com/forgebase,https://automation.example.com/forgebase
WEBHOOK_SECRET=your_webhook_signing_secret
```

## 6. 各整合的逐項教學

### 6.1 GA4

用途：

- 讓 ForgeBase 的站內事件同步進 Google Analytics 4
- 用於流量分析、漏斗分析、來源分析、跨頁表現觀察

目前程式如何運作：

- web 端在 layout 中檢查 NEXT_PUBLIC_GA_MEASUREMENT_ID，有值才注入 gtag script
- 前端 analytics SDK 會把 ForgeBase 事件平行送成 GA4 事件

目前已映射的主要事件：

- product_view -> view_item
- category_view -> view_item_list
- rfq_start -> begin_checkout
- rfq_submit -> generate_lead
- form_submit -> form_submit
- spec_download -> file_download
- cta_click -> select_content

設定步驟：

1. 登入 Google Analytics
2. 左下角進入管理
3. 若還沒有帳戶，按建立 > 帳戶
4. 在同一區按建立 > 資源
5. 建立完資源後，進入資料收集與修改 > 資料串流
6. 按新增串流 > 網站
7. 輸入網站網址與串流名稱
8. 進入串流詳情，複製評估 ID，也就是 G-XXXXXXXXXX
9. 填入 NEXT_PUBLIC_GA_MEASUREMENT_ID
10. 重啟 web 與 api

驗證方式：

1. 開啟網站任一產品頁
2. 觸發產品瀏覽、點 CTA、下載規格書、送出 RFQ
3. 到 GA4 Realtime 看是否收到 view_item、file_download、generate_lead 等事件
4. 到管理後台整合狀態頁或打 admin integrations status API，確認 ga4.configured 為 true

注意事項：

- 這個整合只負責平行送事件，不會取代 ForgeBase 自己的第一方事件庫
- 目前是 send_page_view: false，因此主要依賴自定義追蹤邏輯，不要只用 GA 預設頁面檢視來理解整體漏斗

### 6.2 Meta Conversions API

用途：

- 把關鍵站內事件以 server-side 方式送到 Meta
- 用於 Facebook / Instagram 廣告成效追蹤、廣告學習與更穩定的轉換回傳

目前程式如何運作：

- API 端會把部分 ForgeBase 事件轉成 Meta 標準事件
- 事件映射如下：
  - product_view -> ViewContent
  - rfq_start -> InitiateCheckout
  - rfq_submit -> Lead
  - spec_download -> AddToCart

設定步驟：

1. 登入 Meta Business Suite 或 Events Manager
2. 建立或確認網站 Pixel 已存在
3. 點進該 Pixel 的設定頁籤
4. 找到 Conversions API 區塊
5. 用 Events Manager 直接產生 access token，或用自己的 app + system user 產生 token
6. 複製 Pixel ID 與 token
7. 填入 META_PIXEL_ID 與 META_ACCESS_TOKEN
8. 重啟 API

驗證方式：

1. 觸發產品瀏覽、RFQ 開始、RFQ 送出、規格下載
2. 到 Meta Events Manager 檢查是否收到 ViewContent、InitiateCheckout、Lead、AddToCart
3. 若未收到，先檢查 API log 是否有 meta_capi.error

注意事項：

- 這裡是 server-side forwarding，不是單純前端 pixel
- 若你未來同時上 client-side pixel，應保留 event_id 一致，避免重複計算

### 6.3 Google Ads Customer Match

用途：

- 把高意圖訪客對應的 email 雜湊後同步到 Google Ads 名單
- 用於高意圖名單再行銷與相似受眾策略

目前程式如何運作：

- 會抓取 hot / sales_ready 的訪客
- 找到其對應 contact email
- 做標準化後 SHA-256 雜湊
- 透過 Google Ads REST API v17 的 offlineUserDataJobs 上傳到 Customer Match 名單

設定步驟：

1. 用 Google Ads 管理員帳戶登入
2. 到 API Center 申請 developer token
3. 到 Google Cloud Console 建立 OAuth client
4. 完成一次 OAuth 授權流程，拿到 refresh token
5. 在 Google Ads 建立一個 Customer Match user list
6. 記下 customer id 與 user list id
7. 填入：
   - GOOGLE_ADS_DEVELOPER_TOKEN
   - GOOGLE_ADS_CUSTOMER_ID
   - GOOGLE_ADS_CLIENT_ID
   - GOOGLE_ADS_CLIENT_SECRET
   - GOOGLE_ADS_REFRESH_TOKEN
   - GOOGLE_ADS_CUSTOMER_LIST_ID
8. 重啟 API

驗證方式：

1. 先讓測試資料中有 hot 或 sales_ready 且帶 email 的訪客
2. 觸發同步排程或手動呼叫對應 service / 任務
3. 查 API log 是否出現 uploaded 數量
4. 到 Google Ads Audience Manager 觀察名單是否開始累積資料
5. 到整合狀態 API 確認 google_ads.configured 為 true

注意事項：

- Google Ads 需要接受名單政策與帳號資格，並不是技術上填完就一定能用
- 此整合目前是高意圖 email 名單同步，不是全站所有訪客同步

### 6.4 LinkedIn Matched Audiences

用途：

- 把 Email 名單或 Company 名單同步到 LinkedIn 廣告帳戶
- 特別適合 B2B 名單再行銷與 Account-Based Marketing

目前程式如何運作：

- 可建立 audience sync job
- 可選 EMAIL 或 COMPANY
- 可選 segment 或 contacts_all 當資料來源
- 背景任務會建立 DMP segment，然後上傳 email hash 或 company name

設定步驟：

1. 到 LinkedIn Campaign Manager 確認你能管理目標廣告帳戶
2. 記下該廣告帳戶 ID
3. 以有廣告帳戶權限的 LinkedIn 使用者完成 Marketing API OAuth 授權
4. 確保應用程式具備 r_ads 或 rw_ads 類型權限
5. 取得 LINKEDIN_ACCESS_TOKEN
6. 填入 LINKEDIN_ACCESS_TOKEN 與 LINKEDIN_AD_ACCOUNT_ID
7. 重啟 API
8. 再透過 audience API 建立受眾工作

建議建立兩種 audience：

- 高意圖 email audience
- 已辨識公司名稱 audience

驗證方式：

1. 建立 audience job
2. 呼叫 /api/v1/tracking/linkedin-audiences
3. 觸發 /api/v1/tracking/linkedin-audiences/{id}/sync
4. 查 job 狀態是否從 pending -> syncing -> synced
5. 到 LinkedIn 後台確認 segment 存在且有資料

注意事項：

- COMPANY 型名單仰賴資料品質，尤其公司名稱要夠標準
- 若公司名稱來源混亂，LinkedIn 匹配率會很差

### 6.5 IP-to-Company 與公司資料補全

用途：

- 把匿名訪客轉成可判讀的公司層級線索
- 協助業務辨識哪些公司正在看哪些產品與內容

目前程式如何運作：

- 先試 Clearbit Reveal
- 失敗時退回 ip-api.com
- 解析結果可包含 company_name、domain、industry、country、city、linkedin handle、logo、description 等欄位

實務上你應該怎麼做：

1. 先接 Clearbit Reveal 當主要資料源
2. 把 ip-api.com 當無 key 備援
3. 在後台或 CRM 中把 company_name / domain 作為後續分群與路由依據
4. 若有重要目標帳戶，手動覆寫公司資訊也很值得做

設定步驟：

1. 申請 Clearbit Reveal API Key
2. 填入 CLEARBIT_API_KEY
3. 保留 ip-api.com 備援，不需額外 key
4. 重啟 API

驗證方式：

1. 以真實外網 IP 產生測試訪客事件
2. 檢查 visitor / account 資料是否帶入公司資訊
3. 觀察 enrichment_source 是 clearbit 或 ip_api

注意事項：

- 私有 IP、內網 IP、localhost 不會有有效公司識別
- ip-api.com 的資料較粗糙，不應作為高信賴度公司辨識主資料源
- Cloudflare 提供的是基礎 IP 與地理資訊脈絡，不等於 IP-to-Company

### 6.6 HubSpot CRM

用途：

- 把表單聯絡人與 RFQ 直接同步進 HubSpot
- 讓業務不需要手動抄資料

目前程式如何運作：

- contact 可同步為 HubSpot Contact
- RFQ 可同步為 HubSpot Deal
- Deal 會依 ForgeBase priority 映射到不同 HubSpot stage

設定步驟：

1. 以 Super Admin 進入 HubSpot
2. 進入 Development > Legacy apps 或 Private apps
3. 建立 private app
4. 在 Scopes 頁面勾選 CRM 相關權限
5. 建立後進入 Auth 頁籤
6. 點 Show token 並複製 token
7. 填入 HUBSPOT_API_KEY
8. 若要在 log 或外部流程使用 portal 參考，可填 HUBSPOT_PORTAL_ID
9. 重啟 API

驗證方式：

1. 新增一筆 contact
2. 送出一筆 RFQ
3. 確認 contact.hubspot_contact_id 與 rfq.hubspot_deal_id 有值
4. 到 HubSpot 檢查 contact 與 deal 是否已建立

注意事項：

- 雖然變數名稱叫 HUBSPOT_API_KEY，但程式實際上是用 Bearer token 方式呼叫，實務上請放 Private App token
- 若你公司已經重度使用 Salesforce，請避免 HubSpot 與 Salesforce 同時作為主 CRM，否則你會把同步衝突問題帶進來

### 6.7 Salesforce CRM

用途：

- 將 Contact 與 RFQ 轉成 Salesforce Contact / Opportunity
- 把成交階段反拉回 ForgeBase，完成雙向同步

目前程式如何運作：

- 可推單筆 contact
- 可推單筆 RFQ 為 Opportunity
- 可批次同步全部 contacts
- 可把 Opportunity stage 拉回更新本地 RFQ status

設定步驟：

1. 進入 Salesforce Setup
2. 搜尋並打開 App Manager
3. 建立 Connected App
4. 啟用 OAuth 設定並給 API 需要的 scopes
5. 建立一個專用 API user
6. 取得並填入：
   - SF_CLIENT_ID
   - SF_CLIENT_SECRET
   - SF_USERNAME
   - SF_PASSWORD
   - SF_SECURITY_TOKEN
   - SF_INSTANCE_URL
7. 重啟 API

驗證方式：

1. 呼叫 /api/v1/tracking/crm/sf/sync-contact
2. 呼叫 /api/v1/tracking/crm/sf/sync-rfq
3. 呼叫 /api/v1/tracking/crm/sync-logs 檢查成功與失敗記錄
4. 到 Salesforce 檢查 Contact / Opportunity 是否建立
5. 用 /api/v1/tracking/crm/sf/pull-opportunity 測試 stage 反寫

注意事項：

- Salesforce 是這套系統最值得做雙向同步的 CRM，因為程式裡已經有 stage 回寫
- 若你的業務流程依賴 Salesforce，這組整合優先度通常比 HubSpot 更高

### 6.8 Email 平台與名單同步

ForgeBase 的 Email 整合分成兩層，不要混在一起看。

第一層是 transactional / nurture 發送：

- Resend
- SendGrid

第二層是 marketing audience / contacts 管理：

- Mailchimp
- SendGrid Marketing Contacts

#### 6.8.1 Resend / SendGrid 發信

用途：

- 發送交易型信件
- 發送 nurture sequence
- 發送測試信件

設定步驟：

1. 決定 ESP_PROVIDER 用 resend 或 sendgrid
2. 若用 Resend，進 Resend Dashboard > API Keys 建立 key，填入 RESEND_API_KEY
3. 若用 SendGrid，進 Settings > API Keys 建立 key，填入 SENDGRID_API_KEY
4. 先完成寄件網域或 sender 驗證
5. 補齊 EMAIL_FROM_NAME 與 EMAIL_FROM
6. 重啟 API

驗證方式：

1. 呼叫 /api/v1/esp/status
2. 呼叫 /api/v1/esp/test-email
3. 確認收到測試信

注意事項：

- 目前 active provider 是由 ESP_PROVIDER 控制，不是同時雙寫
- 建議先用 Resend 上線交易信，再視名單規模評估是否轉 SendGrid

#### 6.8.2 Mailchimp / SendGrid 名單同步

用途：

- 把聯絡人名單同步到行銷平台
- 讓你做滴灌、電子報、名單分群

設定步驟：

1. Mailchimp：先建立 Audience，再填 MAILCHIMP_API_KEY、MAILCHIMP_AUDIENCE_ID
2. SendGrid 名單同步：填 SENDGRID_API_KEY
3. 重啟 API

驗證方式：

1. Mailchimp：呼叫 /api/v1/esp/mailchimp/sync-contacts
2. SendGrid：呼叫 /api/v1/esp/sendgrid/sync-contacts
3. 觀察 success / failed 數量
4. 再查 /api/v1/esp/mailchimp/stats 或 /api/v1/esp/sendgrid/stats

注意事項：

- Mailchimp 較適合偏電子報與 nurture
- SendGrid 較適合同時兼做 transactional + contacts 管理
- 若你已經用 Salesforce Marketing Cloud 或 HubSpot Marketing Hub，Mailchimp 未必是最佳解

### 6.9 SMTP 通知

用途：

- 提供較基礎、可自管的 email 通知管道
- 適合內部通知、備援告警或特定自有郵件主機場景

設定步驟：

1. 填入 SMTP_HOST、SMTP_PORT、SMTP_USER、SMTP_PASSWORD、SMTP_FROM
2. 重啟 API

驗證方式：

1. 先看整合狀態 API 的 smtp.configured
2. 實際觸發通知流程，確認信件是否發出

注意事項：

- SMTP 與 Resend / SendGrid 不同，它偏通知管道，不是整體行銷郵件平台
- 若要追蹤開信、點擊、退信，還是應以專業 ESP 為主

### 6.10 Webhook

用途：

- 把 ForgeBase 的關鍵事件推給外部系統
- 這是你把 ForgeBase 接進公司內部中台、ERP、Slack、Line Bot、n8n、Make、Zapier 的最通用方式

目前可推送的主要事件：

- rfq.created
- rfq.status_changed
- contact.created
- contact.intent_stage_changed
- visitor.became_hot

目前程式如何運作：

- 支援多個端點
- 支援 HMAC-SHA256 簽章
- 失敗時會重試三次

設定步驟：

1. 建立一個或多個接收端 URL
2. 將 URL 以逗號串成 WEBHOOK_ENDPOINT_URLS
3. 設定 WEBHOOK_SECRET 啟用簽章
4. 重啟 API

驗證方式：

1. 建一個測試接收端，例如 n8n webhook 或 webhook.site
2. 送出 contact 或 RFQ
3. 確認是否收到 JSON payload
4. 驗證 headers：
   - X-Webhook-Event
   - X-Webhook-Id
   - X-Webhook-Signature
5. 到整合狀態 API 檢查 endpoint_count 與 signing_enabled

注意事項：

- 如果你的公司還沒有決定主 CRM 或 ERP，先把 Webhook 接起來通常是最保險的做法
- Webhook 是整體整合架構裡最便宜、也最能保留彈性的出口

### 6.11 Google Search Console API

用途：

- 讓後台能讀到 SEO 真實曝光、點擊、CTR、平均排名
- 幫你找出可補強頁面與關鍵字機會

目前程式如何運作：

- 用 service account JSON 走 JWT 換 token
- 查 Search Analytics API
- 提供 page performance、keyword opportunities、cannibalization 等資料

設定步驟：

1. 在 Google Cloud 建立專案
2. 啟用 Search Console API
3. 建立 Service Account
4. 下載金鑰 JSON
5. 到 Search Console 打開該網站資產
6. 到設定 > 使用者和權限
7. 把 service account email 加為該站資產的使用者
8. 把整份 JSON 壓成單行字串，填到 GSC_SERVICE_ACCOUNT_KEY_JSON
9. 填入 GSC_SITE_URL，例如 https://yourdomain.com/
10. 重啟 API

驗證方式：

1. 呼叫對應 SEO 工作台功能或 service
2. 若沒資料，先檢查 Search Console 權限是否真的加到 service account
3. 再檢查 GSC_SITE_URL 是否與 Search Console property 完全一致

注意事項：

- 這不是流量追蹤，而是搜尋表現資料
- GSC 通常有約 2 天延遲，不適合用來看即時行為

## 7. 如何驗證整套整合是否真的通了

建議不要一個一個單點測，而是跑一條完整驗收路徑：

1. 開一個產品頁
2. 觸發 product_view
3. 點 CTA
4. 下載規格書
5. 開始 RFQ
6. 送出 RFQ
7. 檢查以下結果：

- ForgeBase 站內事件有寫入
- GA4 收到 view_item / generate_lead
- Meta 收到 ViewContent / Lead
- 若訪客 IP 可解析，公司資料有補上
- Contact / RFQ 有進 HubSpot 或 Salesforce
- Webhook 接收端有收到 rfq.created
- Email 測試可成功寄出
- 若名單同步已設定，高意圖受眾可進 Google Ads 或 LinkedIn

只要這條路徑走得通，你就不是「接了很多服務」，而是真的把漏斗打通。

## 8. 目前你最需要知道的風險與缺口

### 8.1 .env.example 不完整

目前很多整合需要的環境變數存在於程式碼，但沒有完整出現在 api/.env.example。這代表後續若交給其他工程師或 DevOps，只照範本部署，很容易漏掉整合設定。

### 8.2 HubSpot 變數命名容易誤導

程式裡叫 HUBSPOT_API_KEY，但實際上是拿來做 Bearer token。實務上請使用 HubSpot Private App token，不要再找傳統 API key。

### 8.3 Google Ads / Meta / Webhook 多數以環境變數直接控制

這些整合不像某些 SaaS 有完整 UI 設定頁，目前主要靠環境變數與 API 驅動。也就是說，你要把部署流程與密鑰管理設好，不能只期待後台點一點。

### 8.4 IP-to-Company 的匹配率不是 100%

這件事本質上跟流量來源、IP 類型、對方網路環境有關。匿名流量越偏個人網路、VPN、手機網路，匹配率越差。

### 8.5 不是所有外部整合都應該同時上

如果你現在只有一個小型銷售團隊，優先順序通常會是：

1. GA4
2. Meta CAPI
3. Resend 或 SendGrid
4. Webhook
5. Salesforce 或 HubSpot 擇一
6. Clearbit
7. Google Ads / LinkedIn
8. GSC

## 9. 我給你的實務建議

如果你要以「最快讓 ForgeBase 真正變強」為目標，而不是只追求整合數量，建議你分兩批做。

### 第一批，兩週內一定要上

- GA4
- Meta CAPI
- Resend 或 SendGrid
- Webhook
- HubSpot 或 Salesforce 擇一
- Clearbit

這一批上完，你已經能做到：

- 事件有追蹤
- 名單有流向
- RFQ 有通知
- 匿名流量開始能被識別

### 第二批，再補強成長飛輪

- Google Ads Customer Match
- LinkedIn Matched Audiences
- Mailchimp 或 SendGrid contacts
- Google Search Console

這一批上完，你才能真正進入：

- 站內高意圖 -> 廣告回流
- 新名單 -> nurture
- SEO -> 持續優化

## 10. 最後結論

ForgeBase 要發揮最大效果，關鍵不是「把所有系統都接上」，而是接對順序。

正確順序是：

1. 先把事件蒐集與通知打穩
2. 再把 CRM 與公司辨識接起來
3. 再把廣告受眾與 Email 名單活化補上
4. 最後用 GSC 做內容與 SEO 持續優化

如果你照本文件執行，ForgeBase 才會從一個具 AI 能力的 B2B 官網，變成一套真正能把流量、名單、RFQ、業務跟進與再行銷串起來的成長系統。