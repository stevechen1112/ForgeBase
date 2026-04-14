"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { platformAdminApi, type SystemHealth } from "@/lib/api/platform-admin";
import { Database, Clock, Code2, Activity, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

function HealthRow({
  icon: Icon,
  label,
  value,
  isOk,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  isOk: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0">
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium">{label}</span>
      </div>
      <span
        className={`text-sm font-medium ${
          isOk ? "text-green-600" : "text-red-500"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export default function PlatformHealthPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;

  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshed, setRefreshed] = useState<Date | null>(null);

  function load() {
    if (!token) return;
    setLoading(true);
    platformAdminApi
      .systemHealth(token)
      .then((h) => {
        setHealth(h);
        setRefreshed(new Date());
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">系統健康</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {refreshed ? `最後更新: ${refreshed.toLocaleTimeString()}` : "載入中..."}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          刷新
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {loading && !health && (
        <div className="h-40 animate-pulse rounded-xl bg-muted" />
      )}

      {health && (
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          {/* Overall status badge */}
          <div className="mb-5 flex items-center gap-2">
            <Activity className="h-5 w-5 text-muted-foreground" />
            <span className="text-base font-semibold">整體狀態</span>
            <span
              className={`ml-auto inline-flex items-center rounded-full px-3 py-0.5 text-sm font-semibold ${
                health.status === "healthy"
                  ? "bg-green-100 text-green-700"
                  : health.status === "degraded"
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {health.status}
            </span>
          </div>

          <HealthRow
            icon={Database}
            label="資料庫"
            value={health.database}
            isOk={health.database === "ok"}
          />
          <HealthRow
            icon={Clock}
            label="API 運行時間"
            value={formatUptime(health.uptime_seconds)}
            isOk={true}
          />
          <HealthRow
            icon={Code2}
            label="Python 版本"
            value={health.python_version}
            isOk={true}
          />
        </div>
      )}
    </div>
  );
}
