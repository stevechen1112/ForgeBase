# ForgeBase 文件權威與版本狀態索引

> 建立日期：2026-08-28
>
> 用途：避免歷史稽核、舊 TODO、舊百分比或舊兩階段方案被誤認為目前產品狀態。

## 一、文件優先順序

遇到不同文件結論不一致時，依下列順序判定：

1. 最新 production 只讀 audit／workflow artifact 與目前部署 commit。
2. `FORGEBASE_FUNCTION_MODULE_COMPLETENESS_AUDIT_2026-08-15.md` 的 2026-08-28 正式環境更新版。
3. `FORGEBASE_NORTH_STAR_CORE_GAP_IMPLEMENTATION_PLAN_2026-08-26.md` 的最新執行記錄與決策記錄。
4. `FORGEBASE_NORTH_STAR_IMPLEMENTATION_PROGRESS_2026-08-26.md` 與 `FORGEBASE_INTERNAL_PRODUCTIZATION_14_BATCH_PROGRESS_2026-08-27.md`。
5. 專項現行決策文件，例如供應商 POC、退場治理與部署 runbook。
6. 舊稽核、舊 roadmap、舊 TODO 與 sprint ticket；只用於理解歷史，不作目前完成度或產品承諾依據。

計分規則：目前唯一有效的 17 模組百分比與四分類，以功能模組完整度盤點的 2026-08-28 版本為準。

## 二、目前權威文件

| 文件 | 狀態 | 權威範圍 |
|---|---|---|
| `FORGEBASE_FUNCTION_MODULE_COMPLETENESS_AUDIT_2026-08-15.md` | **目前總盤點** | 17 模組分數、北極星逐段狀態、四分類、對外承諾與剩餘 Gate |
| `FORGEBASE_NORTH_STAR_CORE_GAP_IMPLEMENTATION_PLAN_2026-08-26.md` | **產品決策基準／持續更新** | 北極星契約、Build vs. Buy、供應商中立、Phase Gate；現況優先讀第 23、24 節 |
| `FORGEBASE_NORTH_STAR_IMPLEMENTATION_PROGRESS_2026-08-26.md` | **工程實作紀錄** | 北極星各批實作、測試與 code review；較早批次的「尚缺」是歷史快照 |
| `FORGEBASE_INTERNAL_PRODUCTIZATION_14_BATCH_PROGRESS_2026-08-27.md` | **內部產品化完成紀錄** | 14 批 Release、瀏覽器、五語、AI、fault、capacity、security、delivery、privacy、SLO、release、retirement |
| `FORGEBASE_CATEGORY4_RETIREMENT_AUDIT_2026-08-27.md` | **退場決策基準** | 已移除項、觀察中項、30／60 天與治理 Gate |
| `FORGEBASE_EXTERNAL_PROVIDER_POC_DECISION_2026-08-27.md` | **供應商 POC 決策** | PDL／Hunter／Resend、Apollo 條件式候選及資料權利邊界 |
| `ARCHITECTURE.md` | **現行架構入口** | 服務、資料與部署架構；若與 production topology 不同，以 deployment workflow 為準 |
| `FORGEBASE_DEPLOY_SETUP.md`、`deploy/README.md` | **營運 runbook** | 部署與復原操作；實際控制以 repository script／workflow 為準 |

## 三、權威 production 證據

| 證據 | 狀態／用途 |
|---|---|
| Complete Release Gate `33141795688` | SHA `0539149` 完整 Gate 與正式部署成功 |
| Production Company Identification `33142199489` | 兩個 active tenant 均為 `shadow/pdl_ip/ready=true`，無政策變更 |
| Provider Sync `33132485016` | production registry 已具 `pdl_ip`、`hunter_domain`、`hunter` |
| Production Retirement `33140492663` | 兩項 removed verified、五項 disabled observing、無新增刪除授權 |
| Production Data Quality `33138620002` | active tenant identity 與 synthetic RFQ 分類證據 |
| Recovery／Browser `33136513984` | recovery point、隔離 restore 與 Platform Admin browser evidence |
| `.github/workflows/production-commercial-readiness-audit.yml` | Hunter／Resend／inbound／kill switch／tenant policy 的最新只讀稽核入口 |

workflow 或 artifact 只證明其明列範圍；不會自動證明資料商授權、公司辨識精準率、聯絡人品質、寄達率、回覆率或成交率。

## 四、歷史／已被取代的判定文件

| 文件 | 狀態 | 正確使用方式 |
|---|---|---|
| `FORGEBASE_PRODUCT_CLAIMS_IMPLEMENTATION_AUDIT_2026-08-26.md` | **歷史基線，已被取代** | 保留原始宣稱差距；不可用其「未實作」判定描述現在 |
| `FORGEBASE_COMPANY_IDENTIFICATION_AND_CONTACT_ENRICHMENT_PLAN_2026-08-16.md` | **舊方案，已被北極星計畫取代** | 僅保留早期 provider／架構思考，不使用 15% 或第二優先結論 |
| `FORGEBASE_COMPREHENSIVE_AUDIT_2026-08-11.md` | **歷史稽核** | 當時 132 tests 與上市 blockers 的證據快照 |
| `FORGEBASE_AI_CUSTOMER_SERVICE_AUDIT_2026-08-11.md` | **歷史稽核** | 當時 AI Chat 差距；目前狀態讀總盤點及 AI 實作紀錄 |
| `FORGEBASE_MASTER_ROADMAP.md` | **舊 roadmap，不再是唯一總表** | 舊五階段／ContentFlow 工作線背景，不作目前產品優先級 |
| `FORGEBASE_PHASE1_P0_EXTERNAL_PILOT_TODO_2026-08-16.md` | **歷史兩階段 TODO** | 保留當時開放條件；目前產品不再拆兩階段 |
| `FORGEBASE_CLOSED_TEST_PROTOCOL_2026-08-15.md` | **歷史測試協議** | 可重用測試方法，不用其 readiness 判定 |
| `FORGEBASE_CLOSED_TEST_READINESS_COMPLETION_REPORT_2026-08-15.md` | **歷史完成報告** | 當時環境快照，不覆蓋最新 production evidence |
| `FORGEBASE_EXTERNAL_TEST_HARDENING_REPORT_2026-08-16.md` | **歷史 hardening 快照** | 安全原則可參考；外部服務現況改讀最新 audit |
| `FORGEBASE_PLAN_B_REFERENCE_SITE_TODO_2026-08-11.md` | **歷史 TODO** | 參考站早期工作，不作目前 backlog |
| `FORGEBASE_SPRINT_TICKETS_P0_SPEED.md`、`FORGEBASE_SPRINT_TICKETS_PHASE3_INTENT.md`、`FORGEBASE_SPRINT_TICKETS_PHASE4_OUTCOMES.md`、`FORGEBASE_SPRINT_TICKETS_PHASE5_DEEPENING.md` | **歷史 sprint 記錄** | 不以未勾選項推定目前缺口 |

## 五、仍可使用但需看適用範圍

- `ADMIN_ACCEPTANCE_REPORT_2026-08-13.md`、`ADMIN_UAT_MATRIX_2026-08-13.md`：保留當時驗收證據；目前 RBAC／Browser 以最新 Release Gate 為準。
- AI、多語、網站交付、平台營運等專項計畫：可作設計與測試細節，但完成度以總盤點及最新進度文件為準。
- ContentFlow／SearchOps 相關合約與整合分析：只約束該整合，不改變 ForgeBase 北極星或產品完成度。
- 行銷文案文件：只代表文案候選；發布前仍須符合總盤點的「可說／不可說」邊界。

## 六、維護規則

1. 新的總盤點不得另建一套競爭百分比；直接更新目前總盤點並保留版本差異。
2. 歷史文件保留原內容，不回頭竄改當時證據；只在頂端增加狀態警示。
3. 新 production 結論必須附 run ID、commit、時間與「能證明／不能證明」範圍。
4. provider registry、tenant policy、live transport 必須分開描述。
5. mock／deterministic lab 可證明流程，不得當成 production provider 或商業品質證據。
6. 任何文件若宣稱自動外聯、precision、deliverability、回覆或成交完成，必須附真實非 synthetic 樣本與 Gate 結果。
