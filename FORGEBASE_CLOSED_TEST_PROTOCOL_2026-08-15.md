# ForgeBase 受控對外測試計畫

- 版本：2026-08-15
- 目標：用真實瀏覽與操作驗證完整產品，不把虛構公司或測試詢價誤認為真實商業成果。
- 測試站：NorthForge Tools 與 AxisForm Precision。

## 一、測試範圍

本輪驗證：網站導覽、內容維護、素材、語系、SEO、訪客追蹤、意圖、動態 CTA、AI Product Advisor、Chat → RFQ、RFQ 收件、品質、SLA、任務、漏斗、outcome 與 tenant isolation。

本輪不驗證：真實寄信、主動聯繫訪客、公司／人物辨識供應商、CRM 正式同步、自動產生網站內容、舊站自動匯入、付費與自助開通。

## 二、測試資料政策

- 自動測試信箱一律使用 `forgebase-axisform-e2e+時間戳@example.com`。
- 姓名、公司、數量與需求必須明示 `Synthetic`、`Automated QA` 或 `TEST`。
- 訊息必須包含 `DO NOT REPLY`。
- AxisForm `auto_reply_enabled=false`；測試人員不得人工回信。
- synthetic RFQ 最終以 `won-test-only` 關閉，只為驗證 outcomes，不得計入 lead、報價或營收。
- 外部參與者只提交其同意提供的測試資料，不使用機密圖面、真實採購規格或不必要個資。

## 三、測試角色

- 平台管理員：確認租戶、網站、部署、隔離與系統健康。
- 內容管理者：驗證產品、應用、證書、FAQ、頁面、素材及語系維護。
- 測試訪客：完成指定採購旅程並提供可用性回饋。
- 業務測試者：只在後台處理 synthetic RFQ；不得對外寄信。
- 觀察者：記錄任務、SLA、漏斗與 outcome 是否正確形成。

## 四、核心測試腳本

每名測試者至少完成一條完整旅程：

1. 從首頁理解公司、產品範圍與測試聲明。
2. 進入產品分類與產品詳情，確認規格、關聯應用、品質證據與 CTA。
3. 向 AI Advisor 詢問一個可由公開內容回答的問題，再問一個證據不足的問題。
4. 將 Chat 內容帶入 RFQ 或直接開啟 RFQ。
5. 填寫明確 synthetic 資料並送出。
6. 管理員確認 RFQ 位於正確 tenant、品質分數合理、任務與 outbox 已建立。
7. 管理員更新狀態、SLA、結果與原因，確認漏斗／outcomes 同步。
8. 確認整個流程沒有寄信或寫入另一 tenant。

## 五、多租戶與安全驗證

- AxisForm API 回傳 AxisForm 品牌與 `DEMO-M01／T08／M14`，NorthForge 不得出現這些 model。
- 使用 NorthForge tenant 嘗試寫入 AxisForm Chat 必須被拒絕。
- 改寫資產 URL 的 tenant folder 不得讀到其他 connected tenant 圖片。
- RFQ 的 visitor、Chat draft、產品與應用關聯不得跨 tenant。
- 停用 tenant 後，公開與後台存取必須被封鎖。
- consent 撤回會刪除 tracking identity；RFQ／Chat／Contact 依業務與稽核政策保留。

## 六、效能與復原驗證

- 公開 smoke：兩站首頁、產品、應用、RFQ、API readiness 與 asset health 全部為 200。
- 基準負載：100 個併發 GET，五條主要路徑零失敗；記錄總時間與 request/sec，但不把單次結果宣稱為容量上限。
- 單一 tenant web service 停止後，其他站與 API 仍應可用。
- 重新啟動該 service 後，health 與公開頁必須恢復。
- 建立已驗證 image tag；下一次發布起執行真正的前一版 image rollback。

## 七、外部封閉測試安排

建議先邀請 3–5 家熟悉 B2B 採購或傳產網站的人員，每家 1–2 位；提供測試聲明與固定任務，不把他們當銷售名單。測試期間可蒐集真實曝光、流量與操作行為，但不得主動聯繫或把被辨識企業直接計為 lead。

每位測試者記錄：

- 是否在 30 秒內理解網站是做什麼、是否為測試公司。
- 是否能找到符合需求的產品／應用與規格。
- 是否理解 AI 回答的證據邊界。
- RFQ 完成時間、放棄欄位與錯誤訊息。
- 對「一般形象網站」與 ForgeBase 差異的理解。
- 願意在真實企業網站使用哪些功能，以及不願使用的原因。

## 八、進入條件

- 兩個 connected tenant 在正式環境可用且隔離驗證通過。
- 完整 API DB 測試、Web lint／type-check／build 通過。
- synthetic visitor → Chat → RFQ → task／outbox → outcome 閉環通過。
- 破圖、主要 404、跨品牌文案與重大操作阻擋為零。
- `auto_reply_enabled=false` 且測試團隊理解不回信政策。
- 已有 SOP、復原方式與測試資料清除／標記規則。

## 九、退出條件

至少累積 30 個有效測試工作階段及 10 次完整 synthetic RFQ 旅程後，才做第一次成效判讀；同時要求：

- P0 安全、資料隔離與資料遺失事件為 0。
- 主要旅程成功率至少 90%。
- 主要頁面與 API 無持續性 5xx。
- AI 未把虛構證書／能力當成真實主張，且證據不足時能限縮回答。
- 所有測試 RFQ 均標示 test-only，無任何外寄。

若未達條件，就延長封閉測試並修正，不把曝光、公司辨識紀錄或自動化建立的 contact 宣稱成 leads。

## 十、Lead 與計費口徑

- 被辨識的公司或可能聯絡人只是 account/contact signal，不是 lead。
- 有 RFQ 但尚未證實真實需求時，是 inquiry 或 MQL，不應直接以成交型 lead 計費。
- 建議只有在對方主動提交可聯繫資料、表達具體需求、符合資格且非垃圾／測試後，才列為 qualified lead。
- 封閉測試階段不做 by-lead 計費；先驗證定義、去重、歸因、爭議與人工覆核流程。
