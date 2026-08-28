import type { PlatformAuditItem } from "@/lib/api/platform-admin";

const ACTION_LABELS: Record<string, string> = {
  "tenant.provisioned": "建立租戶",
  "tenant.updated": "更新租戶設定",
  "platform_operator.created": "建立平台人員",
  "platform_operator.updated": "更新平台人員",
  "observability.sampled": "擷取服務水準快照",
  "incident.acknowledge": "確認營運事件",
  "incident.resolve": "解決營運事件",
  "privacy.retention_run": "執行資料保留清理",
  "privacy.visitor_exported": "匯出訪客資料",
  "privacy.visitor_erased": "刪除訪客資料",
  "site_build.created": "建立網站交付單",
  "site_build.updated": "更新網站交付設定",
  "site_build.validated": "檢查上線條件",
  "site_build.publish_blocked": "發布被上線條件阻擋",
  "site_build.published": "標記網站發布",
  "site_profile.updated": "更新網站資料",
  "rfq.classified": "分類詢價資料",
};

const TARGET_LABELS: Record<string, string> = {
  tenant: "租戶",
  platform_user: "平台人員",
  service_level_snapshot: "服務水準快照",
  operational_incident: "營運事件",
  privacy_operation: "隱私作業",
  site_build: "網站交付單",
  site_profile: "網站資料",
  rfq: "詢價",
};

const FIELD_LABELS: Record<string, string> = {
  name: "租戶名稱",
  is_active: "啟用狀態",
  feature_overrides: "功能覆寫",
  status: "狀態",
  note: "備註",
  template_key: "網站範本",
  primary_domain: "主要網域",
  locales: "語系",
  cms_connected: "CMS 串接",
  delivery_stage: "交付階段",
  delivery_owner_id: "交付負責人",
  target_launch_at: "預計上線日",
  handoff_at: "交接日",
  acceptance_status: "驗收狀態",
  internal_note: "內部備註",
  readiness: "上線條件",
  before: "執行前",
  after: "執行後",
  is_test_data: "測試資料",
  is_spam: "垃圾詢價",
  reason: "原因",
};

const VALUE_LABELS: Record<string, string> = {
  true: "是",
  false: "否",
  active: "啟用",
  inactive: "停用",
  draft: "草稿",
  blocked: "受阻",
  published: "已發布",
  acknowledged: "已確認",
  resolved: "已解決",
};

export function platformAuditActionLabel(action: string): string {
  return ACTION_LABELS[action] || action;
}

export function platformAuditTargetLabel(target: string): string {
  return TARGET_LABELS[target] || target;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "未設定";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "string" || typeof value === "number") {
    const text = String(value);
    return VALUE_LABELS[text] || text;
  }
  if (Array.isArray(value)) return value.length ? value.map(formatValue).join("、") : "無";
  try {
    return JSON.stringify(value);
  } catch {
    return "無法顯示";
  }
}

function changeText(value: unknown): string {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const pair = value as Record<string, unknown>;
    if (Object.hasOwn(pair, "from") && Object.hasOwn(pair, "to")) {
      return `${formatValue(pair.from)} → ${formatValue(pair.to)}`;
    }
  }
  return formatValue(value);
}

export function PlatformAuditSummary({ changes }: Pick<PlatformAuditItem, "changes">) {
  const entries = Object.entries(changes);
  if (!entries.length) return <span className="text-muted-foreground">無欄位異動</span>;

  return (
    <div className="space-y-1.5">
      {entries.map(([field, value]) => {
        const text = changeText(value);
        return (
          <div key={field} className="text-xs leading-5">
            <span className="font-medium text-foreground">{FIELD_LABELS[field] || field}：</span>
            <span className="break-words text-muted-foreground" title={text}>{text}</span>
          </div>
        );
      })}
    </div>
  );
}
