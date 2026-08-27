"use client";

import { useMessageNamespace } from "@/lib/messages";

export function DemoEnvironmentNotice() {
  const copy = useMessageNamespace<{ demoNoticeLabel: string; demoNotice: string }>("common");

  return (
    <aside
      role="note"
      aria-label={copy.demoNoticeLabel}
      className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-center text-xs font-medium leading-5 text-amber-950"
    >
      {copy.demoNotice}
    </aside>
  );
}
