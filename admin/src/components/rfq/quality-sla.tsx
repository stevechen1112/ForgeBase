"use client";

/** Lead Quality Score 徽章 */
export function QualityBadge({ score }: { score: number }) {
  const cls =
    score >= 70
      ? "bg-emerald-100 text-emerald-700"
      : score >= 40
        ? "bg-amber-100 text-amber-800"
        : "bg-red-100 text-red-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {score}
    </span>
  );
}

/** SLA 倒數／逾期狀態（尊重 slaBreached，即使已離開 new/assigned） */
export function SlaCountdown({
  slaDueAt,
  slaBreached,
  status,
}: {
  slaDueAt: string | null;
  slaBreached: boolean;
  status: string;
}) {
  if (!slaDueAt) return <span className="text-muted-foreground">—</span>;

  // sla_due_at 是 UTC-naive 字串，補 Z 讓 Date 正確解析
  const due = new Date(slaDueAt.endsWith("Z") ? slaDueAt : `${slaDueAt}Z`);
  const remainMs = due.getTime() - Date.now();
  const isOpen = ["new", "assigned"].includes(status);
  const isTerminal = ["won", "lost", "expired"].includes(status);

  if (slaBreached || (isOpen && remainMs < 0)) {
    const overH = Math.abs(remainMs) / 3600000;
    const label = isOpen
      ? `已逾期${overH >= 1 ? ` ${Math.floor(overH)}h` : ""}`
      : "回覆時已逾期";
    return <span className="font-semibold text-red-600">{label}</span>;
  }

  if (isTerminal) {
    return <span className="text-muted-foreground">已結案</span>;
  }

  if (!isOpen) {
    return <span className="text-muted-foreground">已回覆</span>;
  }

  if (remainMs < 3600000) {
    return <span className="font-semibold text-orange-600">剩 {Math.max(1, Math.round(remainMs / 60000))}m</span>;
  }
  return <span className="text-muted-foreground">剩 {(remainMs / 3600000).toFixed(1)}h</span>;
}
