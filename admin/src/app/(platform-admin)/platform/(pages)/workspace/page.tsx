"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ClipboardCheck, RefreshCw, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type PlatformWorkspace } from "@/lib/api/platform-admin";

const COUNT_LABELS: Record<string, string> = {
  adoption_review: "待評估導入申請",
  delivery_open: "進行中的網站交付",
  rfq_attention: "需要注意的 RFQ",
  failed_jobs: "失敗背景工作",
};

const SEVERITY_STYLE = {
  urgent: "border-red-200 bg-red-50 text-red-800",
  high: "border-amber-200 bg-amber-50 text-amber-900",
  normal: "border-border bg-card text-foreground",
};

export default function PlatformWorkspacePage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [data, setData] = useState<PlatformWorkspace | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setData(await platformAdminApi.workspace(token));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取平台待辦。");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">營運待辦</h1>
          <p className="mt-1 text-sm text-muted-foreground">集中查看導入、交付、詢價、背景工作與外測封板，不會自動對外寄信或改變客戶資料。</p>
        </div>
        <Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button>
      </div>

      {error && <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Object.entries(COUNT_LABELS).map(([key, label]) => (
          <div key={key} className="rounded-xl border bg-card p-5 shadow-sm">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-2 text-3xl font-bold tabular-nums">{data?.counts[key] ?? "—"}</p>
          </div>
        ))}
      </div>

      <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="flex items-center gap-2 border-b px-5 py-4"><Wrench className="h-4 w-4" /><h2 className="font-semibold">依優先順序處理</h2></div>
        {loading ? <p className="p-8 text-sm text-muted-foreground">正在整理待辦…</p> : data?.work_items.length ? (
          <div className="divide-y">
            {data.work_items.map((item, index) => (
              <Link key={`${item.kind}-${item.title}-${index}`} href={item.href} className="block px-5 py-4 transition-colors hover:bg-muted/40">
                <div className="flex gap-3">
                  {item.severity === "urgent" ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" /> : item.severity === "high" ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" /> : <ClipboardCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2"><p className="font-medium">{item.title}</p><span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${SEVERITY_STYLE[item.severity]}`}>{item.severity === "urgent" ? "優先處理" : item.severity === "high" ? "需要注意" : "待處理"}</span></div>
                    <p className="mt-1 text-sm text-muted-foreground">{item.detail}</p>
                    {item.created_at && <p className="mt-1 text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("zh-TW")}</p>}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : <div className="p-10 text-center text-sm text-emerald-700"><CheckCircle2 className="mx-auto mb-2 h-5 w-5" />目前沒有需要平台人員處理的待辦。</div>}
      </section>
    </div>
  );
}
