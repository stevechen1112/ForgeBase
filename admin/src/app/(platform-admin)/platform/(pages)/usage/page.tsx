"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type PlatformUsageSummary,
} from "@/lib/api/platform-admin";

const TOTAL_LABELS: Record<string, string> = {
  products: "產品",
  assets: "素材",
  asset_bytes: "素材空間",
  rfqs: "RFQ",
  visitors: "訪客",
  active_users: "啟用用戶",
};
const formatBytes = (value = 0) =>
  value < 1024 * 1024
    ? `${value.toLocaleString()} B`
    : `${(value / 1024 / 1024).toFixed(1)} MB`;

export default function PlatformUsagePage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [data, setData] = useState<PlatformUsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setData(await platformAdminApi.usage(token));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取平台用量。");
    } finally {
      setLoading(false);
    }
  }, [token]);
  useEffect(() => {
    void load();
  }, [load]);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">平台用量</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            以實際事件、素材與資料量做內部營運監控；此頁不承擔產品分級或計費邏輯。
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => void load()}
          disabled={loading}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          重新整理
        </Button>
      </div>
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Object.entries(TOTAL_LABELS).map(([key, label]) => (
          <div key={key} className="rounded-xl border bg-card p-5 shadow-sm">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-2 text-3xl font-bold tabular-nums">
              {key === "asset_bytes"
                ? formatBytes(data?.totals[key])
                : (data?.totals[key] ?? "—").toLocaleString()}
            </p>
          </div>
        ))}
      </div>
      <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="border-b px-5 py-4">
          <h2 className="font-semibold">各租戶用量</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-left text-xs text-muted-foreground">
                <th className="px-4 py-3">租戶</th>
                <th className="px-4 py-3 text-right">產品</th>
                <th className="px-4 py-3 text-right">素材</th>
                <th className="px-4 py-3 text-right">素材空間</th>
                <th className="px-4 py-3 text-right">RFQ</th>
                <th className="px-4 py-3 text-right">訪客</th>
              </tr>
            </thead>
            <tbody>
              {data?.tenants.map((tenant) => (
                <tr key={tenant.tenant_id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-medium">{tenant.tenant_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {tenant.slug}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {tenant.product_count}
                  </td>
                  <td className="px-4 py-3 text-right">{tenant.asset_count}</td>
                  <td className="px-4 py-3 text-right">
                    {formatBytes(tenant.asset_bytes)}
                  </td>
                  <td className="px-4 py-3 text-right">{tenant.rfq_count}</td>
                  <td className="px-4 py-3 text-right">
                    {tenant.visitor_count}
                  </td>
                </tr>
              ))}
              {!loading && !data?.tenants.length && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-12 text-center text-muted-foreground"
                  >
                    尚無租戶用量資料。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
