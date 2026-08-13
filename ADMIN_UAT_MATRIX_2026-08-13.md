# ForgeBase Admin 完整 UAT 矩陣

狀態定義：`PASS` 已在本機 UI 或完整 DB API 回歸驗證；`COND` 需第三方 sandbox 才能執行最終副作用；`N/A` 為方案或可選服務未啟用時的預期降級。

## 角色與共通行為

| 測試項目 | owner/admin | marketing_manager | sales | super-admin | 結果 |
|---|---:|---:|---:|---:|---|
| 登入、session 還原、登出入口 | ✓ | ✓ | ✓ | 平台入口 | PASS |
| 營運總覽、待辦、成果、RFQ、通知 | ✓ | ✓ | ✓ | — | PASS |
| 商品查看／編輯 | ✓ | ✓ | ✓ | — | PASS |
| 內容、意圖規則、成效、Copilot、分群、nurture | ✓ | ✓ | 隱藏＋403 | — | PASS |
| ML 評分、轉址、團隊、網站、整合、帳單 | ✓ | 隱藏＋403 | 隱藏＋403 | — | PASS |
| 平台總覽、租戶、跨租戶用戶、健康 | — | — | — | ✓ | PASS |
| 未登入重新導向、直接網址拒絕、可理解 403 | ✓ | ✓ | ✓ | ✓ | PASS |
| loading、empty、error、重新整理 | ✓ | ✓ | ✓ | ✓ | PASS |
| 桌面與 390×844 手機導覽 | ✓ | ✓ | ✓ | ✓ | PASS |

## 一般後台主選單（33）

| 群組 | 路由 | 主要操作 | 結果 |
|---|---|---|---|
| 每日營運 | `/dashboard` | 30 天摘要、逾期 RFQ、最新 RFQ、快速入口、重新整理 | PASS |
| 每日營運 | `/dashboard/tasks` | SLA／待辦聚合、連往處理頁、重新整理 | PASS |
| 每日營運 | `/dashboard/outcomes` | 合格詢價、速度、來源歸因、重新整理 | PASS |
| RFQ | `/dashboard/rfqs/my` | 指派給我、狀態篩選、分頁、詳情 | PASS |
| RFQ | `/dashboard/rfqs` | 全部、狀態／負責人篩選、統計、詳情 | PASS |
| RFQ | `/dashboard/rfqs/templates` | 建立、編輯、啟用／停用、刪除範本 | PASS |
| 通知 | `/dashboard/notifications` | 管道／狀態篩選、已讀狀態、重新整理 | PASS |
| 買家 | `/dashboard/intent` | 分數、階段、來源篩選、訪客詳情 | PASS |
| 買家 | `/dashboard/ml-scoring` | 模型狀態、訓練前置條件、重新整理 | PASS/N/A |
| 買家 | `/dashboard/intent-rules` | 權重、門檻、還原、驗證、儲存 | PASS |
| 成效 | `/dashboard/content-performance` | 日期範圍、頁面／商品成效、重新整理 | PASS |
| 對話 | `/dashboard/chats` | 狀態／品質篩選、詳情、人工審核 | PASS |
| AI | `/dashboard/copilot` | 對話、歷史、清除、工具結果呈現 | PASS |
| AI | `/dashboard/agent-runs` | 狀態篩選、展開、核准／拒絕入口 | PASS/N/A |
| 分群 | `/dashboard/segments` | 清單、預覽、新增、評估、同步、詳情 | PASS |
| 跟進 | `/dashboard/nurture` | 清單、新增、步驟、核准、詳情 | PASS |
| 跟進 | `/dashboard/nurture/outbox` | 待確認、send/skip 前置條件、重新整理 | PASS；實寄 COND |
| 內容 | `/dashboard/products` | 搜尋、語言、分頁、主推、上下架、編輯、刪除 | PASS |
| 內容 | `/dashboard/categories` | 搜尋、語言、新增、編輯、上下架、刪除 | PASS |
| 內容 | `/dashboard/pages` | 搜尋、語言、新增、編輯、發布、刪除 | PASS |
| 內容 | `/dashboard/assets` | 類型篩選、上傳前置條件、重新整理、刪除 | PASS |
| 內容 | `/dashboard/applications` | 語言、新增、編輯、發布、刪除、關聯 | PASS |
| 內容 | `/dashboard/faqs` | 語言、新增、編輯、發布、刪除、關聯 | PASS |
| 內容 | `/dashboard/certifications` | 語言、新增、編輯、發布、刪除、PDF 欄位 | PASS |
| 內容 | `/dashboard/capabilities` | 語言、新增、編輯、發布、刪除 | PASS |
| 內容 | `/dashboard/comparisons` | 語言、新增、編輯、發布、刪除 | PASS |
| 內容 | `/dashboard/ctas` | 新增、編輯、顯示條件、發布、刪除 | PASS |
| SEO | `/dashboard/redirects` | 新增、編輯、啟停、刪除、來源／目標驗證 | PASS |
| 設定 | `/dashboard/settings/notifications` | 管道綁定、偏好、事件開關、儲存 | PASS；外部通知 COND |
| 設定 | `/dashboard/users` | 邀請、角色、啟停、方案人數限制 | PASS |
| 設定 | `/dashboard/settings/site-profile` | 品牌、導覽、圖示、JSON 驗證、儲存／重載 | PASS |
| 設定 | `/dashboard/integrations` | 憑證新增／刪除、狀態、測試／同步前置條件 | PASS；第三方寫入 COND |
| 設定 | `/dashboard/settings/billing` | 方案、用量、升級／取消前置條件 | PASS；PayPal COND |

## 新增、詳情與編輯路線

| 類型 | 已驗路由／操作 | 結果 |
|---|---|---|
| 新增表單 | applications、capabilities、categories、certifications、comparisons、ctas、faqs、nurture、pages、products、segments 的 `/new` | PASS |
| 同頁新增 | RFQ templates | PASS |
| 代表性 CRUD | 分類 create/update/delete；商品 create/update/delete；驗收資料精確清理 | PASS |
| 商品驗證 | 名稱、型號、slug、短描述、分類必填；分類為有效選單 | PASS |
| 內容編輯 | 所有內容 entity 的 `/:id/edit` 路由建置；代表性商品／分類實機編輯 | PASS |
| RFQ 詳情 | `/:id` 聯絡／需求／分數／時程／事件／AI／狀態／指派／跟進 | PASS |
| 對話詳情 | chats `/:id` 記錄、品質與人工審核 | PASS |
| 訪客詳情 | visitors `/:id` 行為、分數與 RFQ 關聯 | PASS |
| Segment 詳情 | steps、evaluate、sync、enroll 路徑 | PASS |
| Nurture 詳情 | steps、approve、enroll、process 與 outbox 路徑 | PASS；實寄 COND |

## 平台管理（4）

| 路由 | 主要操作 | 結果 |
|---|---|---|
| `/platform/overview` | 跨租戶指標、RFQ 趨勢、前五租戶 | PASS |
| `/platform/tenants` | 搜尋、狀態、方案、租戶詳情與編輯入口 | PASS |
| `/platform/users` | 跨租戶使用者、角色／狀態檢視 | PASS |
| `/platform/health` | API、資料庫、服務健康與重新整理 | PASS |

## API 與資料契約

| 契約 | 結果 |
|---|---|
| tenant isolation、auth/team、role、plan gate | PASS |
| 商品／分類／頁面／內容 CRUD、locale、slug、status、relation | PASS |
| 不支援 locale 回空結果，不回退英文 | PASS |
| RFQ status、assign、follow-up、quality、SLA、templates、events | PASS |
| intent、analytics、chat review、segments、nurture、notifications | PASS |
| site profile、subscription、platform admin | PASS |
| 完整 DB 回歸 | 133 PASS / 2 optional AgentOS SKIP |

## 尚需第三方 sandbox 的最終案例

| 系統 | 必要測試資料 | 最終驗證 |
|---|---|---|
| PayPal | sandbox merchant／buyer | checkout、approve callback、cancel、方案更新 |
| Email/ESP | sandbox API key、測試收件人 | outbox send、退信、重試、unsubscribe |
| Telegram/LINE | 測試 bot/channel | 綁定、事件通知、失敗重試 |
| HubSpot/Google Ads | 測試 portal/account | credentials、test、sync、去重、錯誤回復 |
