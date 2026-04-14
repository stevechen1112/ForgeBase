"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { platformAdminApi, type TenantSummary, type TenantUpdate } from "@/lib/api/platform-admin";
import { Search, ChevronRight, AlertCircle, CheckCircle2, XCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const PLAN_COLORS: Record<string, string> = {
  starter: "bg-gray-100 text-gray-700",
  professional: "bg-blue-100 text-blue-700",
  enterprise: "bg-purple-100 text-purple-700",
};

export default function PlatformTenantsPage() {
  const { state } = useAuth();
  const router = useRouter();
  const token = state.status === "authenticated" ? state.accessToken : undefined;

  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    platformAdminApi
      .tenants(token, search ? { search } : undefined)
      .then(setTenants)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, search]);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleActive(t: TenantSummary) {
    if (!token) return;
    try {
      const update: TenantUpdate = { is_active: !t.is_active };
      await platformAdminApi.updateTenant(token, t.id, update);
      setTenants((prev) => prev.map((x) => (x.id === t.id ? { ...x, is_active: !x.is_active } : x)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "更新失敗");
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">租戶管理</h1>
        <p className="mt-1 text-sm text-muted-foreground">所有租戶的方案、狀態與用量</p>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜尋租戶名稱 / Slug..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button variant="outline" size="sm" onClick={load}>刷新</Button>
      </div>

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
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-5 py-3">名稱</th>
                <th className="px-5 py-3">方案</th>
                <th className="px-5 py-3">狀態</th>
                <th className="px-5 py-3 text-right">用戶</th>
                <th className="px-5 py-3 text-right">商品</th>
                <th className="px-5 py-3 text-right">RFQ</th>
                <th className="px-5 py-3 text-right">訪客</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tenants.map((t) => (
                <tr
                  key={t.id}
                  className="cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() => router.push(`/dashboard/platform/tenants/${t.id}`)}
                >
                  <td className="px-5 py-3">
                    <p className="font-medium">{t.name}</p>
                    <p className="text-xs text-muted-foreground">{t.slug}</p>
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        PLAN_COLORS[t.plan] ?? "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {t.plan}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <button
                      className="flex items-center gap-1 text-xs font-medium hover:opacity-70 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleActive(t);
                      }}
                    >
                      {t.is_active ? (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                          <span className="text-green-600">活躍</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3.5 w-3.5 text-red-400" />
                          <span className="text-red-500">停用</span>
                        </>
                      )}
                    </button>
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums">{t.user_count}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{t.product_count}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{t.rfq_count}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{t.visitor_count}</td>
                  <td className="px-5 py-3">
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
