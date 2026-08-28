"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ScrollText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type PlatformAuditItem,
} from "@/lib/api/platform-admin";
import {
  PlatformAuditSummary,
  platformAuditActionLabel,
  platformAuditTargetLabel,
} from "@/components/platform/PlatformAuditSummary";

export default function PlatformAuditPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [items, setItems] = useState<PlatformAuditItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setItems(await platformAdminApi.auditLog(token));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取操作紀錄。");
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
          <h1 className="text-2xl font-bold">操作紀錄</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            記錄平台人員對租戶、交付單與發布流程的高影響操作，供問題追查與交付驗收使用。
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
      <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="flex items-center gap-2 border-b px-5 py-4">
          <ScrollText className="h-4 w-4" />
          <h2 className="font-semibold">最近 100 筆</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-left text-xs text-muted-foreground">
                <th className="px-4 py-3">時間</th>
                <th className="px-4 py-3">操作者</th>
                <th className="px-4 py-3">動作</th>
                <th className="px-4 py-3">目標</th>
                <th className="px-4 py-3">異動摘要</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b last:border-0">
                  <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">
                    {new Date(item.created_at).toLocaleString("zh-TW")}
                  </td>
                  <td className="px-4 py-3">{item.actor_email}</td>
                  <td className="px-4 py-3">
                    <p>{platformAuditActionLabel(item.action)}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">{item.action}</p>
                  </td>
                  <td className="px-4 py-3">{platformAuditTargetLabel(item.target_type)}</td>
                  <td className="max-w-[360px] px-4 py-3">
                    <PlatformAuditSummary changes={item.changes} />
                  </td>
                </tr>
              ))}
              {!loading && !items.length && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-12 text-center text-muted-foreground"
                  >
                    尚無操作紀錄。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
