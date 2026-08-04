"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, MessageSquare, Star, AlertTriangle } from "lucide-react";
import { apiClient } from "@/lib/api/client";

type ChatSessionItem = {
  id: string;
  visitor_id: string;
  visitor_intent_stage: string | null;
  visitor_intent_score: number | null;
  visitor_country: string | null;
  context_page: string | null;
  context_entity_type: string | null;
  status: string;
  message_count: number;
  quality_rating: number | null;
  admin_notes: string | null;
  started_at: string;
  ended_at: string | null;
};

type ChatSessionsResponse = {
  items: ChatSessionItem[];
  total: number;
  limit: number;
  offset: number;
};

const STATUS_COLOR: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  handoff_ready: "bg-yellow-100 text-yellow-800",
  handoff_completed: "bg-blue-100 text-blue-800",
};

const STATUS_LABEL: Record<string, string> = {
  active: "進行中",
  handoff_ready: "待業務接手",
  handoff_completed: "已轉業務接手",
};

const STAGE_COLOR: Record<string, string> = {
  sales_ready: "bg-red-100 text-red-700",
  hot: "bg-orange-100 text-orange-700",
  warm: "bg-yellow-100 text-yellow-800",
  cold: "bg-gray-100 text-gray-600",
};

const STAGE_LABEL: Record<string, string> = {
  sales_ready: "可成交",
  hot: "高度關注",
  warm: "觀望中",
  cold: "初次瀏覽",
};

const SELECT_CLS =
  "rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

function StarRating({ rating }: { rating: number | null }) {
  if (!rating) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <span className="inline-flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <Star
          key={i}
          className={`h-3 w-3 ${i < rating ? "fill-yellow-400 text-yellow-400" : "text-gray-300"}`}
        />
      ))}
    </span>
  );
}

export default function ChatSessionsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [items, setItems] = useState<ChatSessionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [ratingFilter, setRatingFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String((page - 1) * PAGE_SIZE),
      });
      if (statusFilter) params.set("status", statusFilter);
      if (ratingFilter) params.set("quality_rating", ratingFilter);

      const data = await apiClient.get<ChatSessionsResponse>(
        `/chat/admin/sessions?${params.toString()}`,
        token,
      );
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [token, page, statusFilter, ratingFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const unratedCount = items.filter((s) => !s.quality_rating).length;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">官網對話</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            查看官網 AI 對話紀錄、回答品質，以及何時轉給業務接手
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* KPI Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">總對話數</p>
            <p className="mt-2 text-3xl font-bold">{total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">已轉業務接手</p>
            <p className="mt-2 text-3xl font-bold">
              {items.filter((s) => s.status === "handoff_completed").length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">平均訊息數</p>
            <p className="mt-2 text-3xl font-bold">
              {items.length
                ? Math.round(items.reduce((s, i) => s + i.message_count, 0) / items.length)
                : 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              未評分 {unratedCount > 0 && <AlertTriangle className="h-3.5 w-3.5 text-yellow-500" />}
            </p>
            <p className="mt-2 text-3xl font-bold">{unratedCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          className={SELECT_CLS}
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">所有狀態</option>
          <option value="active">Active</option>
          <option value="handoff_ready">待業務接手</option>
          <option value="handoff_completed">已轉業務接手</option>
        </select>
        <select
          className={SELECT_CLS}
          value={ratingFilter}
          onChange={(e) => {
            setRatingFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">所有評分</option>
          {[1, 2, 3, 4, 5].map((r) => (
            <option key={r} value={String(r)}>
              {"★".repeat(r)} ({r})
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-card overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-sm text-muted-foreground">載入中…</div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground">
            <MessageSquare className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
            尚無對話紀錄
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                {[
                  "訪客",
                  "來源頁面",
                  "狀態",
                  "訊息數",
                  "品質評分",
                  "開始時間",
                  "",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left font-medium text-muted-foreground"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((s) => (
                <tr
                  key={s.id}
                  className="hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      <Link
                        href={`/dashboard/visitors/${s.visitor_id}`}
                        className="font-mono text-xs text-primary hover:underline"
                      >
                        {s.visitor_id.slice(0, 8)}…
                      </Link>
                      <div className="flex items-center gap-1.5">
                        {s.visitor_intent_stage && (
                          <Badge
                            className={`text-[10px] px-1.5 py-0 ${STAGE_COLOR[s.visitor_intent_stage] ?? ""}`}
                          >
                            {STAGE_LABEL[s.visitor_intent_stage] ?? s.visitor_intent_stage}
                          </Badge>
                        )}
                        {s.visitor_country && (
                          <span className="text-[10px] text-muted-foreground">
                            {s.visitor_country}
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="max-w-[200px] truncate text-xs text-muted-foreground">
                      {s.context_page ?? "—"}
                    </div>
                    {s.context_entity_type && s.context_entity_type !== "unknown" && (
                      <Badge variant="outline" className="mt-0.5 text-[10px]">
                        {s.context_entity_type}
                      </Badge>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge className={`text-xs ${STATUS_COLOR[s.status] ?? "bg-muted text-muted-foreground"}`}>
                      {STATUS_LABEL[s.status] ?? s.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-center font-medium">{s.message_count}</td>
                  <td className="px-4 py-3">
                    <StarRating rating={s.quality_rating} />
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {new Date(s.started_at).toLocaleString("zh-TW", {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  <td className="px-4 py-3">
                    <Button asChild variant="ghost" size="sm">
                      <Link href={`/dashboard/chats/${s.id}`}>查看 →</Link>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>共 {total} 筆</span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            上一頁
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={items.length < PAGE_SIZE}
            onClick={() => setPage((p) => p + 1)}
          >
            下一頁
          </Button>
        </div>
      </div>
    </div>
  );
}
