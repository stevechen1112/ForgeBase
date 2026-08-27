"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Eye,
  Flame,
  Globe,
  Monitor,
  RefreshCw,
  Users,
} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";
import { intentStageLabel } from "@/lib/content/displayLabels";

type Visitor = {
  visitor_id: string;
  intent_score: number;
  intent_stage: string;
  total_visits: number;
  total_page_views: number;
  device_type: string | null;
  country: string | null;
  contact_id: string | null;
  first_seen: string;
  last_seen: string;
};

const STAGE_COLOR: Record<string, string> = {
  sales_ready: "bg-red-100 text-red-700",
  hot: "bg-orange-100 text-orange-700",
  warm: "bg-yellow-100 text-yellow-800",
  cold: "bg-gray-100 text-gray-600",
};

const FILTERS = [
  { value: "", label: "全部關注程度" },
  { value: "sales_ready", label: "可成交" },
  { value: "hot", label: "高度關注" },
  { value: "warm", label: "多次互動" },
  { value: "cold", label: "初次瀏覽" },
];

function formatDate(value: string): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("zh-TW", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function VisitorsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [visitors, setVisitors] = useState<Visitor[]>([]);
  const [stageFilter, setStageFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<Visitor[]>(
        "/tracking/visitors?limit=200&sort=intent_score",
        token,
      );
      setVisitors(Array.isArray(data) ? data : []);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredVisitors = useMemo(
    () =>
      stageFilter
        ? visitors.filter((visitor) => visitor.intent_stage === stageFilter)
        : visitors,
    [stageFilter, visitors],
  );
  const pageViews = visitors.reduce(
    (total, visitor) => total + (visitor.total_page_views ?? 0),
    0,
  );
  const highIntentCount = visitors.filter((visitor) =>
    ["hot", "sales_ready"].includes(visitor.intent_stage),
  ).length;
  const averageScore = visitors.length
    ? Math.round(
        visitors.reduce(
          (total, visitor) => total + (visitor.intent_score ?? 0),
          0,
        ) / visitors.length,
      )
    : 0;

  return (
    <div className="min-w-0">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight">訪客旅程</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            查看匿名訪客的瀏覽行為與關注程度，找出值得優先跟進的買家
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw
            className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">已載入訪客</p>
              <Users className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-2 text-3xl font-bold">{visitors.length}</p>
            <p className="text-xs text-muted-foreground">最高關注最多 200 位</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">高關注訪客</p>
              <Flame className="h-4 w-4 text-orange-500" />
            </div>
            <p className="mt-2 text-3xl font-bold">{highIntentCount}</p>
            <p className="text-xs text-muted-foreground">高度關注或可成交</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">平均關注分數</p>
              <Eye className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-2 text-3xl font-bold">{averageScore}</p>
            <p className="text-xs text-muted-foreground">依已載入訪客計算</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">累計瀏覽頁數</p>
              <Globe className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-2 text-3xl font-bold">{pageViews}</p>
            <p className="text-xs text-muted-foreground">已載入訪客的行為總和</p>
          </CardContent>
        </Card>
      </div>

      <Card className="min-w-0 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-4">
          <div>
            <h2 className="font-semibold">匿名訪客清單</h2>
            <p className="text-xs text-muted-foreground">
              顯示 {filteredVisitors.length} 位訪客；資料僅限目前租戶
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <span className="sr-only">篩選關注程度</span>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={stageFilter}
              onChange={(event) => setStageFilter(event.target.value)}
            >
              {FILTERS.map((filter) => (
                <option key={filter.value} value={filter.value}>
                  {filter.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <CardContent className="min-w-0 p-0">
          {loading && visitors.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin" />載入訪客資料中
            </div>
          ) : filteredVisitors.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted-foreground">
              {visitors.length === 0
                ? "尚無訪客資料"
                : "目前沒有符合篩選條件的訪客"}
            </p>
          ) : (
            <div className="max-w-full overflow-x-auto">
              <table className="w-full min-w-[860px] text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                      匿名訪客
                    </th>
                    <th className="px-4 py-3 text-center font-medium text-muted-foreground">
                      關注程度
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                      分數
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                      造訪／頁數
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                      地區／裝置
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                      最後活動
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                      動作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filteredVisitors.map((visitor) => (
                    <tr key={visitor.visitor_id} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs">
                            {visitor.visitor_id.slice(0, 12)}…
                          </span>
                          {visitor.contact_id && (
                            <Badge variant="outline" className="text-[10px]">
                              已識別
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Badge
                          className={`text-xs ${STAGE_COLOR[visitor.intent_stage] ?? ""}`}
                        >
                          {intentStageLabel(visitor.intent_stage)}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold">
                        {visitor.intent_score ?? 0}
                      </td>
                      <td className="px-4 py-3 text-right text-muted-foreground">
                        {visitor.total_visits ?? 0}／{visitor.total_page_views ?? 0}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Globe className="h-3.5 w-3.5" />
                          <span>{visitor.country || "未知地區"}</span>
                          <span>·</span>
                          <Monitor className="h-3.5 w-3.5" />
                          <span>{visitor.device_type || "未知裝置"}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                        {formatDate(visitor.last_seen)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button asChild variant="ghost" size="sm">
                          <Link href={`/dashboard/visitors/${visitor.visitor_id}`}>
                            查看旅程<ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                          </Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
