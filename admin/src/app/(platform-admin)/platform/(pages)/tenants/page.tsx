"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type TenantSummary } from "@/lib/api/platform-admin";
import { Search, ChevronRight, AlertCircle, CheckCircle2, XCircle, Plus, TriangleAlert } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const SITE_STATUS_LABELS: Record<string, string> = {
  missing: "尚未建單",
  draft: "設定中",
  ready: "可發布",
  blocked: "待補條件",
  published: "已發布",
};

const ATTENTION_LABELS: Record<string, string> = {
  tenant_inactive: "租戶停用",
  site_build_missing: "缺交付單",
  site_not_published: "網站未發布",
  site_blocked: "上線條件未通過",
  cms_not_connected: "CMS 未確認",
  active_owner_missing: "缺有效 Owner",
  failed_jobs: "背景工作失敗",
  custom_domain_pending: "自有網域待處理",
  custom_domain_failed: "自有網域驗證失敗",
};

export default function PlatformTenantsPage() {
  const { state } = usePlatformAuth();
  const router = useRouter();
  const token = state.status === "authenticated" ? state.accessToken : undefined;

  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");
  const [siteStatus, setSiteStatus] = useState("all");
  const [attentionOnly, setAttentionOnly] = useState(false);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    const params = {
      ...(search ? { search } : {}),
      ...(activeFilter === "all" ? {} : { is_active: activeFilter === "active" }),
      ...(siteStatus === "all" ? {} : { site_status: siteStatus }),
      ...(attentionOnly ? { needs_attention: true } : {}),
    };
    platformAdminApi
      .tenants(token, params)
      .then(setTenants)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, search, activeFilter, siteStatus, attentionOnly]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">租戶管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理公司帳號、能力治理與網站交付狀態。</p>
        </div>
        <Button onClick={() => router.push("/platform/tenants/new")}><Plus className="mr-2 h-4 w-4" />開通新租戶</Button>
      </div>

      <div className="grid gap-3 rounded-xl border border-border bg-card p-4 md:grid-cols-[minmax(220px,1fr)_145px_160px_auto_auto]">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜尋租戶名稱 / Slug..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select className="h-10 rounded-md border border-input bg-background px-3 text-sm" value={activeFilter} onChange={(e) => setActiveFilter(e.target.value)} aria-label="租戶狀態">
          <option value="all">全部租戶狀態</option>
          <option value="active">只看活躍</option>
          <option value="inactive">只看停用</option>
        </select>
        <select className="h-10 rounded-md border border-input bg-background px-3 text-sm" value={siteStatus} onChange={(e) => setSiteStatus(e.target.value)} aria-label="網站交付狀態">
          <option value="all">全部交付狀態</option>
          {Object.entries(SITE_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <Button variant={attentionOnly ? "default" : "outline"} size="sm" onClick={() => setAttentionOnly((value) => !value)}>
          <TriangleAlert className="mr-2 h-4 w-4" />待處理
        </Button>
        <Button variant="outline" size="sm" onClick={load}>刷新</Button>
      </div>

      {!loading && (
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          <span>目前顯示 {tenants.length} 個租戶</span>
          <span>·</span>
          <span>{tenants.filter((tenant) => tenant.attention_reasons.length > 0).length} 個需要處理</span>
          <span>·</span>
          <span>{tenants.filter((tenant) => tenant.site_build_status === "published").length} 個網站已發布</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-muted" />
          ))}
        </div>
      ) : tenants.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">無符合條件的租戶</p>
      ) : (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          <div className="max-w-full overflow-x-auto">
          <table className="w-full min-w-[900px] text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-5 py-3">名稱</th>
                <th className="px-5 py-3">租戶／網站狀態</th>
                <th className="px-5 py-3">正式網域</th>
                <th className="px-5 py-3 text-right">30 天 RFQ</th>
                <th className="px-5 py-3">最近活動</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tenants.map((t) => (
                <tr
                  key={t.id}
                  className="cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() => router.push(`/platform/tenants/${t.id}`)}
                >
                  <td className="px-5 py-3">
                    <Link
                      href={`/platform/tenants/${t.id}`}
                      className="inline-block rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <span className="block font-medium">{t.name}</span>
                      <span className="block text-xs text-muted-foreground">{t.slug}</span>
                    </Link>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex flex-wrap items-center gap-1.5 text-xs font-medium">
                      {t.is_active ? (
                        <span className="inline-flex items-center gap-1 text-green-600"><CheckCircle2 className="h-3.5 w-3.5" />活躍</span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-500"><XCircle className="h-3.5 w-3.5" />停用</span>
                      )}
                      <span className="rounded bg-muted px-1.5 py-0.5 text-muted-foreground">{SITE_STATUS_LABELS[t.site_build_status || "missing"] || t.site_build_status}</span>
                    </div>
                    {t.attention_reasons.length > 0 && <p className="mt-1 max-w-xs text-[11px] text-amber-700">{t.attention_reasons.slice(0, 2).map((reason) => ATTENTION_LABELS[reason] || reason).join("、")}{t.attention_reasons.length > 2 ? ` 等 ${t.attention_reasons.length} 項` : ""}</p>}
                  </td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">{t.primary_domain || "尚未設定"}</td>
                  <td className="px-5 py-3 text-right tabular-nums"><span className="font-semibold text-foreground">{t.rfq_count_30d}</span><span className="ml-1 text-xs text-muted-foreground">/ 總計 {t.rfq_count}</span></td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">{t.last_activity_at ? new Date(t.last_activity_at).toLocaleDateString("zh-TW") : "尚無活動"}</td>
                  <td className="px-5 py-3">
                    <Link
                      href={`/platform/tenants/${t.id}`}
                      aria-label={`開啟 ${t.name} 租戶詳情`}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  );
}
