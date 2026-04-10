"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  ArrowLeft,
  Globe,
  Monitor,
  Eye,
  MessageSquare,
  ClipboardList,
  TrendingUp,
  Clock,
  MousePointerClick,
  Download,
  FileText,
  Bot,
  Star,
} from "lucide-react";
import { API_BASE } from "@/lib/api/client";

type VisitorProfile = {
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

type TimelineEntry = {
  type: "event" | "chat" | "rfq";
  timestamp: string;
  // event
  event_name?: string;
  page_url?: string;
  page_type?: string;
  score_delta?: number;
  properties?: Record<string, unknown> | null;
  // chat
  chat_session_id?: string;
  status?: string;
  message_count?: number;
  context_page?: string;
  context_entity_type?: string;
  quality_rating?: number | null;
  first_user_msg?: string | null;
  last_assistant_msg?: string | null;
  // rfq
  rfq_id?: string;
  rfq_number?: string;
  priority?: string;
  intent_score_at_submit?: number;
  company_name?: string | null;
  email?: string | null;
};

type JourneyData = {
  visitor: VisitorProfile;
  summary: {
    total_events: number;
    total_chats: number;
    total_rfqs: number;
    event_breakdown: Record<string, number>;
  };
  timeline: TimelineEntry[];
};

const STAGE_COLOR: Record<string, string> = {
  sales_ready: "bg-red-100 text-red-700",
  hot: "bg-orange-100 text-orange-700",
  warm: "bg-yellow-100 text-yellow-800",
  cold: "bg-gray-100 text-gray-600",
};

const EVENT_ICON: Record<string, React.ElementType> = {
  page_view: Eye,
  chat_start: MessageSquare,
  chat_rfq_handoff: ClipboardList,
  rfq_submit: ClipboardList,
  rfq_start: ClipboardList,
  spec_download: Download,
  faq_view: FileText,
  product_view: Eye,
  cta_click: MousePointerClick,
};

const EVENT_LABEL: Record<string, string> = {
  page_view: "瀏覽頁面",
  chat_start: "開始 AI 對話",
  chat_rfq_handoff: "AI 轉介詢價",
  rfq_submit: "提交詢價單",
  rfq_start: "開始填寫詢價表",
  spec_download: "下載規格書",
  faq_view: "查看 FAQ",
  product_view: "查看產品頁",
  cta_click: "點擊 CTA",
  application_view: "查看應用場景",
  category_view: "查看分類頁",
};

const RFQ_STATUS_COLOR: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  assigned: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-orange-100 text-orange-800",
  quoted: "bg-purple-100 text-purple-800",
  won: "bg-green-100 text-green-800",
  lost: "bg-muted text-muted-foreground",
};

export default function VisitorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [data, setData] = useState<JourneyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "event" | "chat" | "rfq">("all");

  const load = useCallback(async () => {
    if (!token || !id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/tracking/visitors/${id}/journey`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      setData(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [token, id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <div className="py-20 text-center text-muted-foreground">載入中…</div>;
  }

  if (error || !data) {
    return (
      <div>
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error ?? "找不到訪客"}</AlertDescription>
        </Alert>
        <Button asChild variant="outline">
          <Link href="/dashboard/intent">
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回意圖分析
          </Link>
        </Button>
      </div>
    );
  }

  const { visitor, summary, timeline } = data;
  const filtered =
    filter === "all" ? timeline : timeline.filter((t) => t.type === filter);

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Button asChild variant="ghost" size="icon">
          <Link href="/dashboard/intent">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight">訪客旅程</h1>
          <p className="mt-0.5 font-mono text-sm text-muted-foreground">
            {visitor.visitor_id.slice(0, 12)}…
          </p>
        </div>
        <Badge className={`text-sm px-3 py-1 ${STAGE_COLOR[visitor.intent_stage] ?? ""}`}>
          {visitor.intent_stage} · {visitor.intent_score} pts
        </Badge>
      </div>

      {/* Profile cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-5">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">意圖分數</p>
            <p className="mt-1 text-2xl font-bold">{visitor.intent_score}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">總瀏覽頁數</p>
            <p className="mt-1 text-2xl font-bold">{visitor.total_page_views}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">AI 對話</p>
            <p className="mt-1 text-2xl font-bold">{summary.total_chats}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">詢價單</p>
            <p className="mt-1 text-2xl font-bold">{summary.total_rfqs}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              {visitor.country && <Globe className="h-3 w-3" />}
              {visitor.device_type && <Monitor className="h-3 w-3" />}
              來源
            </p>
            <p className="mt-1 text-lg font-medium">
              {visitor.country ?? "—"} / {visitor.device_type ?? "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Event breakdown */}
      {Object.keys(summary.event_breakdown).length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          {Object.entries(summary.event_breakdown)
            .sort(([, a], [, b]) => b - a)
            .map(([name, count]) => (
              <Badge key={name} variant="outline" className="text-xs">
                {EVENT_LABEL[name] ?? name}: {count}
              </Badge>
            ))}
        </div>
      )}

      {/* Timeline filter */}
      <div className="mb-4 flex items-center gap-2">
        {(
          [
            { key: "all", label: "全部", count: timeline.length },
            { key: "event", label: "事件", count: timeline.filter((t) => t.type === "event").length },
            { key: "chat", label: "對話", count: summary.total_chats },
            { key: "rfq", label: "詢價", count: summary.total_rfqs },
          ] as const
        ).map((f) => (
          <Button
            key={f.key}
            variant={filter === f.key ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(f.key)}
          >
            {f.label} ({f.count})
          </Button>
        ))}
      </div>

      {/* Timeline */}
      <Card>
        <CardContent className="pt-6">
          {filtered.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              無相關紀錄
            </p>
          ) : (
            <div className="relative">
              {/* vertical line */}
              <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />

              <div className="space-y-0">
                {filtered.map((entry, i) => (
                  <div key={i} className="relative flex gap-4 pb-6 pl-10">
                    {/* dot */}
                    <div
                      className={`absolute left-2.5 top-1 h-3 w-3 rounded-full border-2 border-background ${
                        entry.type === "rfq"
                          ? "bg-green-500"
                          : entry.type === "chat"
                            ? "bg-blue-500"
                            : entry.score_delta && entry.score_delta > 0
                              ? "bg-orange-400"
                              : "bg-muted-foreground/30"
                      }`}
                    />

                    <div className="flex-1 min-w-0">
                      {/* Event */}
                      {entry.type === "event" && (() => {
                        const Icon = EVENT_ICON[entry.event_name ?? ""] ?? Eye;
                        return (
                          <div className="flex items-start gap-2">
                            <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">
                                  {EVENT_LABEL[entry.event_name ?? ""] ?? entry.event_name}
                                </span>
                                {entry.score_delta !== undefined && entry.score_delta > 0 && (
                                  <Badge className="bg-orange-100 text-orange-700 text-[10px] px-1.5 py-0">
                                    +{entry.score_delta}
                                  </Badge>
                                )}
                              </div>
                              {entry.page_url && (
                                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                                  {entry.page_url}
                                </p>
                              )}
                            </div>
                            <time className="shrink-0 text-[10px] text-muted-foreground">
                              {new Date(entry.timestamp).toLocaleString("zh-TW", {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </time>
                          </div>
                        );
                      })()}

                      {/* Chat */}
                      {entry.type === "chat" && (
                        <div className="rounded-lg border bg-blue-50/50 p-3">
                          <div className="flex items-center gap-2">
                            <Bot className="h-4 w-4 text-blue-600" />
                            <span className="text-sm font-medium">AI 對話</span>
                            <Badge
                              className={`text-[10px] ${
                                entry.status === "handoff_completed"
                                  ? "bg-blue-100 text-blue-800"
                                  : entry.status === "handoff_ready"
                                    ? "bg-yellow-100 text-yellow-800"
                                    : "bg-green-100 text-green-700"
                              }`}
                            >
                              {entry.status?.replace("_", " ")}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {entry.message_count} 則訊息
                            </span>
                            {entry.quality_rating && (
                              <span className="flex items-center gap-0.5">
                                {Array.from({ length: entry.quality_rating }, (_, j) => (
                                  <Star key={j} className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                                ))}
                              </span>
                            )}
                            <time className="ml-auto text-[10px] text-muted-foreground">
                              {new Date(entry.timestamp).toLocaleString("zh-TW", {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </time>
                          </div>
                          {entry.first_user_msg && (
                            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
                              <span className="font-medium text-foreground">訪客：</span>{" "}
                              {entry.first_user_msg}
                            </p>
                          )}
                          {entry.last_assistant_msg && (
                            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                              <span className="font-medium text-foreground">AI：</span>{" "}
                              {entry.last_assistant_msg}
                            </p>
                          )}
                          <div className="mt-2">
                            <Button asChild variant="outline" size="sm" className="h-6 text-xs">
                              <Link href={`/dashboard/chats/${entry.chat_session_id}`}>
                                查看完整對話 →
                              </Link>
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* RFQ */}
                      {entry.type === "rfq" && (
                        <div className="rounded-lg border bg-green-50/50 p-3">
                          <div className="flex items-center gap-2">
                            <ClipboardList className="h-4 w-4 text-green-600" />
                            <span className="text-sm font-medium">詢價單</span>
                            <Link
                              href={`/dashboard/rfqs/${entry.rfq_id}`}
                              className="font-mono text-xs text-primary hover:underline"
                            >
                              {entry.rfq_number}
                            </Link>
                            <Badge
                              className={`text-[10px] ${
                                RFQ_STATUS_COLOR[entry.status ?? ""] ?? "bg-muted"
                              }`}
                            >
                              {entry.status?.replace("_", " ")}
                            </Badge>
                            {entry.priority === "urgent" && (
                              <Badge className="bg-red-100 text-red-700 text-[10px]">
                                urgent
                              </Badge>
                            )}
                            <time className="ml-auto text-[10px] text-muted-foreground">
                              {new Date(entry.timestamp).toLocaleString("zh-TW", {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </time>
                          </div>
                          {(entry.company_name || entry.email) && (
                            <p className="mt-1 text-xs text-muted-foreground">
                              {entry.company_name}
                              {entry.company_name && entry.email && " · "}
                              {entry.email}
                            </p>
                          )}
                          <div className="mt-2">
                            <Button asChild variant="outline" size="sm" className="h-6 text-xs">
                              <Link href={`/dashboard/rfqs/${entry.rfq_id}`}>
                                查看 RFQ →
                              </Link>
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Footer info */}
      <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
        <span className="flex items-center gap-1">
          <Clock className="h-4 w-4" />
          首次出現：{new Date(visitor.first_seen).toLocaleDateString("zh-TW")}
        </span>
        <span className="flex items-center gap-1">
          <TrendingUp className="h-4 w-4" />
          最後活動：{new Date(visitor.last_seen).toLocaleDateString("zh-TW")}
        </span>
        {visitor.contact_id && (
          <span className="text-primary">已識別聯絡人</span>
        )}
      </div>
    </div>
  );
}
