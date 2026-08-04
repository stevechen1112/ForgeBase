"use client";
/**
 * StatusBadge — visually differentiates draft / published / archived.
 */
type Props = { status: string; labelMap?: Record<string, string> };

const COLOR_MAP: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-700",
  scheduled: "bg-amber-100 text-amber-700",
  published: "bg-green-100 text-green-700",
  archived: "bg-gray-100 text-gray-500",
  active: "bg-green-100 text-green-700",
  pending: "bg-blue-100 text-blue-700",
  processing: "bg-purple-100 text-purple-700",
  generating: "bg-purple-100 text-purple-700",
  done: "bg-green-100 text-green-700",
  ready: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
  rejected: "bg-red-100 text-red-700",
};

const DEFAULT_LABELS: Record<string, string> = {
  draft: "草稿",
  scheduled: "排程中",
  published: "已上架",
  archived: "已封存",
  active: "啟用",
  pending: "待處理",
  processing: "處理中",
  generating: "產生中",
  done: "完成",
  ready: "就緒",
  error: "錯誤",
  rejected: "已拒絕",
};

export function StatusBadge({ status, labelMap }: Props) {
  const cls = COLOR_MAP[status] ?? "bg-gray-100 text-gray-600";
  const label = labelMap?.[status] ?? DEFAULT_LABELS[status] ?? status;
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}
