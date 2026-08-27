"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type PlatformDashboard } from "@/lib/api/platform-admin";
import {
  Building2, Users, Package, ClipboardList, Eye,
  TrendingUp, AlertCircle, Globe2, TriangleAlert, Workflow,
} from "lucide-react";

const ATTENTION_LABELS: Record<string, string> = {
  tenant_inactive: "租戶停用",
  site_build_missing: "缺交付單",
  site_not_published: "網站未發布",
  site_blocked: "上線條件未通過",
  cms_not_connected: "CMS 未確認",
  active_owner_missing: "缺有效 Owner",
  failed_jobs: "背景工作失敗",
};

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-3xl font-bold tabular-nums">{value.toLocaleString()}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

export default function PlatformOverviewPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;
  const [data, setData] = useState<PlatformDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    platformAdminApi
      .dashboard(token)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">平台總覽</h1>
        <p className="mt-1 text-sm text-muted-foreground">先看需要處理的租戶，再看跨租戶整體數字。</p>
      </div>

      {loading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 animate-pulse">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-muted" />
          ))}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={Building2} label="租戶總數" value={data.total_tenants} sub={`${data.active_tenants} 個活躍`} />
            <StatCard icon={Users} label="用戶總數" value={data.total_users} sub={`${data.active_users} 個活躍`} />
            <StatCard icon={Package} label="商品總數" value={data.total_products} />
            <StatCard icon={ClipboardList} label="RFQ 總數" value={data.total_rfqs} sub={data.legacy_unassigned_rfqs ? `${data.legacy_unassigned_rfqs} 筆舊資料待歸戶` : undefined} />
            <StatCard icon={Eye} label="訪客記錄" value={data.total_visitors} sub={data.legacy_unassigned_visitors ? `${data.legacy_unassigned_visitors} 筆舊資料待歸戶` : undefined} />
            <StatCard icon={Globe2} label="已發布網站" value={data.published_sites} sub={`${data.blocked_sites} 個待補上線條件`} />
            <StatCard icon={TriangleAlert} label="待處理租戶" value={data.tenants_needing_attention} sub={`${data.failed_jobs} 個失敗背景工作`} />
            <StatCard icon={Workflow} label="近 30 天 RFQ" value={data.rfqs_30d} />
          </div>

          <div className="rounded-xl border border-amber-200 bg-amber-50/50 shadow-sm">
            <div className="flex items-center justify-between border-b border-amber-200 px-5 py-3">
              <div className="flex items-center gap-2"><TriangleAlert className="h-4 w-4 text-amber-700" /><h3 className="text-sm font-semibold">租戶待處理清單</h3></div>
              <Link href="/platform/tenants" className="text-xs font-medium text-amber-800 hover:underline">查看全部租戶</Link>
            </div>
            {data.attention_tenants.length === 0 ? (
              <p className="p-5 text-sm text-emerald-700">目前沒有需要處理的租戶。</p>
            ) : (
              <div className="divide-y divide-amber-100">
                {data.attention_tenants.map((tenant) => (
                  <Link key={tenant.id} href={`/platform/tenants/${tenant.id}`} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 hover:bg-amber-100/50">
                    <div><p className="text-sm font-medium text-foreground">{tenant.name}</p><p className="text-xs text-muted-foreground">{tenant.slug}</p></div>
                    <div className="flex flex-wrap justify-end gap-1.5">{tenant.reasons.map((reason) => <span key={reason} className="rounded-full border border-amber-200 bg-white px-2 py-0.5 text-[11px] text-amber-800">{ATTENTION_LABELS[reason] || reason}</span>)}</div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Daily RFQ trend */}
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold">近 7 天 RFQ 趨勢</h3>
              </div>
              {data.daily_rfqs.length === 0 ? (
                <p className="text-sm text-muted-foreground">尚無資料</p>
              ) : (
                <div className="flex items-end gap-1.5 h-28">
                  {data.daily_rfqs.map((d) => {
                    const max = Math.max(...data.daily_rfqs.map((x) => x.count), 1);
                    const pct = (d.count / max) * 100;
                    return (
                      <div key={d.date} className="group relative flex flex-1 flex-col items-center gap-1">
                        <div
                          className="w-full rounded-t bg-red-500/70 transition-all group-hover:bg-red-500"
                          style={{ height: `${pct}%`, minHeight: 2 }}
                        />
                        <span className="text-[10px] text-muted-foreground">{d.date.slice(5)}</span>
                        <span className="absolute -top-5 hidden text-[10px] font-medium group-hover:block">{d.count}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Top tenants */}
            <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
              <div className="border-b border-border px-5 py-3">
                <h3 className="text-sm font-semibold">RFQ 前 5 租戶</h3>
              </div>
              {data.top_tenants.length === 0 ? (
                <p className="p-5 text-sm text-muted-foreground">尚無資料</p>
              ) : (
                <div className="max-w-full overflow-x-auto">
                <table className="w-full min-w-[420px]">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase text-muted-foreground">
                      <th className="px-5 py-2">租戶</th>
                      <th className="px-5 py-2 text-right">RFQ 數</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.top_tenants.map((t) => (
                      <tr key={t.name} className="hover:bg-muted/30">
                        <td className="px-5 py-2 text-sm font-medium">{t.name}</td>
                        <td className="px-5 py-2 text-right text-sm tabular-nums">{t.rfq_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
