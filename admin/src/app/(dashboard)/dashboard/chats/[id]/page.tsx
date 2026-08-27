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
  Bot,
  User,
  Star,
  ExternalLink,
  MessageSquare,
  Clock,
  Globe,
  Monitor,
} from "lucide-react";
import { apiClient } from "@/lib/api/client";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Array<{ type: string; id: string; name: string; url?: string; filename?: string; page_number?: string }>;
  grounding_status: "grounded" | "limited" | "blocked" | null;
  claim_warnings: string[];
  created_at: string;
};

const GROUNDING_LABEL: Record<string, string> = {
  grounded: "已根據網站資料回覆",
  limited: "資料不足，回覆已限縮",
  blocked: "已依安全規則阻擋",
};

const WARNING_LABEL: Record<string, string> = {
  commercial_terms_require_sales_confirmation: "價格、交期等商務條件仍需業務確認",
  compliance_claim_requires_documented_source: "合規聲明仍需正式文件佐證",
  insufficient_compliance_evidence: "網站資料不足以證明該認證或合規聲明",
  no_published_source: "沒有可支撐這則回覆的已發布資料",
  prompt_injection_blocked: "偵測到嘗試改變系統規則的請求",
  unsupported_numeric_claim: "回覆中的數字規格未出現在已索引原文",
};

type ChatDetail = {
  id: string;
  visitor_id: string;
  visitor_intent_stage: string | null;
  visitor_intent_score: number | null;
  visitor_country: string | null;
  visitor_device_type: string | null;
  context_page: string | null;
  context_entity_type: string | null;
  context_entity_id: string | null;
  status: string;
  message_count: number;
  quality_rating: number | null;
  admin_notes: string | null;
  started_at: string;
  ended_at: string | null;
  messages: ChatMessage[];
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

export default function ChatDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [detail, setDetail] = useState<ChatDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [localRating, setLocalRating] = useState<number | null>(null);
  const [localNotes, setLocalNotes] = useState("");

  const load = useCallback(async () => {
    if (!token || !id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<ChatDetail>(`/chat/admin/sessions/${id}`, token);
      setDetail(data);
      setLocalRating(data.quality_rating);
      setLocalNotes(data.admin_notes ?? "");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [token, id]);

  useEffect(() => {
    load();
  }, [load]);

  const saveReview = async () => {
    if (!token || !id) return;
    setSaving(true);
    try {
      const updated = await apiClient.patch<{
        id: string;
        quality_rating: number | null;
        admin_notes: string | null;
      }>(
        `/chat/admin/sessions/${id}`,
        {
          quality_rating: localRating,
          admin_notes: localNotes || null,
        },
        token,
      );
      setDetail((d) =>
        d
          ? { ...d, quality_rating: updated.quality_rating, admin_notes: updated.admin_notes }
          : d,
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="py-20 text-center text-muted-foreground">載入中…</div>;
  }

  if (error || !detail) {
    return (
      <div>
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error ?? "找不到對話"}</AlertDescription>
        </Alert>
        <Button asChild variant="outline">
          <Link href="/dashboard/chats">
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回列表
          </Link>
        </Button>
      </div>
    );
  }

  const hasChanges =
    localRating !== detail.quality_rating ||
    (localNotes || null) !== (detail.admin_notes || null);

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Button asChild variant="ghost" size="icon">
          <Link href="/dashboard/chats">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight">對話詳情</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {new Date(detail.started_at).toLocaleString("zh-TW")} ·{" "}
            {detail.message_count} 則訊息
          </p>
        </div>
        <Badge className={`text-xs ${STATUS_COLOR[detail.status] ?? "bg-muted"}`}>
          {STATUS_LABEL[detail.status] ?? detail.status}
        </Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Left: Conversation */}
        <div className="space-y-1">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <MessageSquare className="h-4 w-4" />
                對話紀錄
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {detail.messages.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  此對話無訊息紀錄
                </p>
              ) : (
                detail.messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 ${msg.role === "assistant" ? "" : "flex-row-reverse"}`}
                  >
                    <div
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                        msg.role === "assistant"
                          ? "bg-primary/10 text-primary"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {msg.role === "assistant" ? (
                        <Bot className="h-4 w-4" />
                      ) : (
                        <User className="h-4 w-4" />
                      )}
                    </div>
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm ${
                        msg.role === "assistant"
                          ? "bg-muted"
                          : "bg-primary text-primary-foreground"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.role === "assistant" && msg.grounding_status && (
                        <div className="mt-2 border-t border-border/50 pt-2">
                          <Badge variant={msg.grounding_status === "grounded" ? "secondary" : "outline"} className="text-[10px]">
                            {GROUNDING_LABEL[msg.grounding_status] ?? msg.grounding_status}
                          </Badge>
                          {msg.claim_warnings.length > 0 && (
                            <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-[10px] text-amber-700">
                              {msg.claim_warnings.map((warning) => (
                                <li key={warning}>{WARNING_LABEL[warning] ?? "需人工確認"}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                      {msg.sources.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5 border-t border-border/50 pt-2">
                          {msg.sources.map((src, i) => (
                            <Badge key={i} variant="outline" className="text-[10px]">
                              {src.type}: {src.name}
                              {src.filename ? ` · ${src.filename}` : ""}
                              {src.page_number ? ` p.${src.page_number}` : ""}
                            </Badge>
                          ))}
                        </div>
                      )}
                      <p className="mt-1 text-[10px] opacity-50">
                        {new Date(msg.created_at).toLocaleTimeString("zh-TW", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Sidebar info */}
        <div className="space-y-4">
          {/* Visitor info card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">訪客資訊</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">訪客 ID</span>
                <Link
                  href={`/dashboard/visitors/${detail.visitor_id}`}
                  className="font-mono text-xs text-primary hover:underline flex items-center gap-1"
                >
                  {detail.visitor_id.slice(0, 8)}…
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
              {detail.visitor_intent_stage && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">意圖階段</span>
                  <Badge
                    className={`text-xs ${STAGE_COLOR[detail.visitor_intent_stage] ?? ""}`}
                  >
                    {STAGE_LABEL[detail.visitor_intent_stage] ?? detail.visitor_intent_stage}
                  </Badge>
                </div>
              )}
              {detail.visitor_intent_score != null && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">意圖分數</span>
                  <span className="font-bold">{detail.visitor_intent_score}</span>
                </div>
              )}
              {detail.visitor_country && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">
                    <Globe className="mr-1 inline h-3 w-3" />
                    國家
                  </span>
                  <span>{detail.visitor_country}</span>
                </div>
              )}
              {detail.visitor_device_type && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">
                    <Monitor className="mr-1 inline h-3 w-3" />
                    裝置
                  </span>
                  <span>{detail.visitor_device_type}</span>
                </div>
              )}
              {detail.context_page && (
                <div>
                  <span className="text-muted-foreground text-xs">對話起始頁面</span>
                  <p className="mt-0.5 break-all text-xs">{detail.context_page}</p>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">
                  <Clock className="mr-1 inline h-3 w-3" />
                  時長
                </span>
                <span className="text-xs">
                  {detail.ended_at
                    ? `${Math.round(
                        (new Date(detail.ended_at).getTime() -
                          new Date(detail.started_at).getTime()) /
                          60000,
                      )} 分鐘`
                    : "進行中"}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Quality Review */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">品質評分</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-1">
                {Array.from({ length: 5 }, (_, i) => (
                  <button
                    key={i}
                    type="button"
                    className="p-0.5"
                    onClick={() => setLocalRating(i + 1 === localRating ? null : i + 1)}
                  >
                    <Star
                      className={`h-5 w-5 transition-colors ${
                        localRating && i < localRating
                          ? "fill-yellow-400 text-yellow-400"
                          : "text-gray-300 hover:text-yellow-300"
                      }`}
                    />
                  </button>
                ))}
                {localRating && (
                  <span className="ml-2 text-sm text-muted-foreground">{localRating}/5</span>
                )}
              </div>
              <textarea
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                rows={3}
                placeholder="管理員備註（例：AI 回答不夠精準、缺少價格資訊…）"
                value={localNotes}
                onChange={(e) => setLocalNotes(e.target.value)}
              />
              <Button
                size="sm"
                className="w-full"
                disabled={!hasChanges || saving}
                onClick={saveReview}
              >
                {saving ? "儲存中…" : "儲存評分"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
