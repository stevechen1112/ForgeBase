import { FlaskConical } from "lucide-react";

export function DemoNotice({ compact = false, message = "本頁使用示意企業與假資料；不蒐集資料、不送出詢價。" }: { compact?: boolean; message?: string }) {
  return (
    <div className={compact ? "demo-notice compact" : "demo-notice"} role="note">
      <FlaskConical aria-hidden="true" size={16} />
      <span>
        <strong>Template Preview</strong>
        {!compact && ` — ${message}`}
      </span>
    </div>
  );
}
