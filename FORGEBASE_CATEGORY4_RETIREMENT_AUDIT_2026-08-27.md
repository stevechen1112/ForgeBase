# ForgeBase 類別四安全退場稽核

> 建立日期：2026-08-27\
> 依據：`FORGEBASE_NORTH_STAR_CORE_GAP_IMPLEMENTATION_PLAN_2026-08-26.md` 第 15 節\
> 原則：功能不是北極星不等於可以刪除；必須先關閉入口、完成依賴與資料稽核、累積 30／60 天實際證據，再以獨立變更集移除。

## 1. 本批結論

本批完成安全退場的「可執行治理機制」，但沒有把尚未完成觀察期的候選誤標為已可刪除。

- 已立即移除：完全無 import、route、bundle 或資料依賴的重複 Copilot floating widget；完全無 caller、且以公開 ISP `org` 猜公司名稱的不安全舊 IP resolver。
- 已關閉新入口並開始觀察：AgentOS runtime、ML scoring online runtime／UI、AI relation recommendation API。
- 保持營運並觀察：Telegram、LINE 通知渠道；只要有啟用設定或送達紀錄就不可核准移除。
- 明確保留：Copilot 專屬頁、規則式意圖評分、通知核心、人工內容關聯、公司辨識、窗口補全、外聯、回覆、RFQ、歸因及歷史 migration／資料欄位。

## 2. 候選逐項決策

| 候選 | 入口／依賴稽核 | 目前處置 | 觀察 Gate | 資料處置與回復 |
|---|---|---|---|---|
| AgentOS／automation runtime | RFQ outbox、`agentOS.py`、歷史 RFQ agent 欄位、未導覽的 agent-runs 頁仍存在 | `automation_runs` locked off；tenantless job fail closed；URL 預設空白；保留最小可回復服務 | 至少 30 天；不得有新 `agent_run_id` 使用證據 | 保留歷史欄位與 migration；觀察通過後另案先移除 UI／worker route，再清 service/config |
| 重複 Copilot floating widget | `rg` 證明只有元件本身與文件引用，沒有任何 import／layout／bundle entry | 已刪除元件；保留 `/dashboard/copilot` 專屬頁 | 靜態 dead-code 證據，不需等待客戶使用觀察 | 可由刪除前 source revision 還原；沒有資料表或客戶資料 |
| ML scoring online runtime／UI | API、服務、visitor 歷史欄位與 UI route 仍存在 | 從 phase2 preset 移除，預設 off；允許明確 override 以量測既有需求 | 至少 30 天且零 API／score 更新訊號；仍需模型 owner／上線決策 | 即使未來移除 runtime，也保留 `ml_intent_score`、時間欄位與離線契約 |
| Telegram 通知 | 綁定 API、webhook、channel adapter、preferences、delivery log 均存在 | 維持 active，觀察採用 | 至少 60 天；零送達且零 enabled preference，並先完成入口停用 | 不刪通知核心；個別渠道另案移除，先匯出／通知使用者 |
| LINE 通知 | adapter、notification router、preferences、delivery log 存在；目前無專屬綁定 UI | 維持 active，觀察採用與設定依賴 | 至少 60 天；零送達且零 enabled preference，並先完成入口停用 | 不刪通知核心；保留其他渠道及歷史 notification log |
| AI relation 推薦 | 兩個推薦 API、LLM service 存在；人工 RelationsPanel 不依賴推薦 API | 新增獨立 feature，預設 off；只量測明確 override 後的 API 使用 | 至少 60 天且零使用 | 永遠保留已發布 Product／Application 關聯資料與人工管理介面 |
| 舊 IP resolver | 無 caller；HTTP fallback；直接把 ISP `org` 轉成公司名稱 | 已刪除 | 靜態 dead／unsafe 證據；正式 `NetworkObservation` provider 架構已取代 | 無 DB 資料；可由刪除前 source revision 還原，不影響公司辨識核心 |
| 其他 legacy／dead code | 無法只靠檔名證明無使用 | 本批不做大範圍猜測式刪除 | 必須逐項具備 route/import/bundle/job/DB/telemetry 證據 | 以獨立變更集與向前 migration 處理 |

## 3. 已落地的觀察與決策機制

0086 migration 建立：

- `retirement_candidate_observations`：候選、程式狀態、必要天數、觀察起點、人工決策與理由。
- `retirement_usage_events`：只保存 candidate、tenant、事件名稱、來源與時間；不保存 request body、email、IP、收件人、內容或操作人 ID。

平台 API 與 UI：

- `GET /api/v1/admin/retirement-audit`：顯示觀察進度、使用訊號、租戶設定依賴、最後使用、blocker 與資料證據。
- `PUT /api/v1/admin/retirement-audit/{candidate}/decision`：只能由 superuser 決定保留或核准移除。
- `/platform/retirement`：平台退場稽核頁；顯示 30／60 天進度與 blocker。
- 核准移除必須同時滿足：entry disabled、觀察期完成、零使用、零仍啟用設定；決策寫入 `PlatformAuditLog`。
- `removed` 決策不可由 API 回改；真正移除仍需下一個獨立 code review、forward migration 與部署回復窗口。

## 4. 觀察起算與不可宣稱事項

- migration 在本機測試資料庫執行的日期不是 production 觀察起點。
- 只有 0086 正式部署並開始持續記錄後，才可計入 production 30／60 天觀察期。
- 目前不得宣稱 AgentOS、ML runtime、通知渠道或 relation recommender 已符合刪除條件。
- telemetry 的「零」只有在整段觀察期間無缺口、migration 與應用版本一致、監控正常時才有效。

## 5. 未來實際刪除變更集的必要清單

1. 匯出平台稽核報告並由產品／營運／工程簽核。
2. 確認 `removal_ready=true`，且 production telemetry 沒有中斷。
3. 匯出或保留歷史客戶資料；通知受影響租戶與 API 使用者。
4. 先移除 navigation／UI／worker／route，再清 service、env 與依賴。
5. 保留歷史 migrations；以新的 forward migration 刪除確定不再需要的 schema。
6. 跑 API、Admin、Web、migration、啟動、備份與 restore smoke tests。
7. 在部署前建立可回復 source tag／revision 與資料備份；回復不得依賴修改已執行 migration。

## 6. 本批回復方式

- 0086 downgrade 只移除退場觀察表，不碰北極星業務資料；已完成 0086 → 0085 → 0086 往返測試。
- 兩個立即刪除項目沒有 DB 資料，可由刪除前 source revision 還原。
- ML／AgentOS／notification／relation 的歷史 models、migrations 與客戶資料均未刪除。
- production 部署前仍須建立正式 source tag 與資料庫備份；本文件不把尚未建立的 tag 或備份宣稱為已存在。
