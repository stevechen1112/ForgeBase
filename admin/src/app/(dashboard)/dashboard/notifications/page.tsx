"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Loader2, RefreshCw, Bell, CheckCircle2, XCircle } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import Link from "next/link";
import { useCapabilities } from "@/lib/hooks/useCapabilities";

type NotifLog = {
  id: string;
  channel: string;
  event_type: string;
  message_preview: string;
  status: "sent" | "failed" | "skipped";
  error_detail: string | null;
  sent_at: string;
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  new_rfq: "新 RFQ",
  hot_visitor: "熱訪客",
  daily_summary: "每日摘要",
  churn_risk: "流失預警",
  chat_handoff: "對話轉業務",
  content_suggestion: "內容建議",
};

const EVENT_TYPE_FEATURES: Partial<Record<string, string>> = {
  hot_visitor: "intent_scoring",
  churn_risk: "intent_scoring",
  chat_handoff: "chat_handoff",
  content_suggestion: "full_tracking",
};

const STATUS_CLS: Record<string, string> = {
  sent: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  skipped: "bg-muted text-muted-foreground",
};

const CHANNEL_LABELS: Record<string, string> = {
  telegram: "Telegram",
  line: "LINE",
  email: "Email",
  in_app: "站內",
};

function formatDt(iso: string): string {
  return new Date(iso).toLocaleString("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function NotificationCenterPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const { hasFeature, isLoading: featuresLoading } = useCapabilities();

  const [logs, setLogs] = useState<NotifLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [channelFilter, setChannelFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [eventFilter, setEventFilter] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/notifications/history?limit=100`, {
      headers: buildApiHeaders(token),
    })
      .then((r) => r.json())
      .then((d) => setLogs(d.data || []))
      .catch(() => setError("載入失敗"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const visibleEventTypes = Object.entries(EVENT_TYPE_LABELS).filter(([eventType]) => {
    const feature = EVENT_TYPE_FEATURES[eventType];
    return !feature || (!featuresLoading && hasFeature(feature));
  });
  const visibleLogs = logs.filter((log) => {
    const feature = EVENT_TYPE_FEATURES[log.event_type];
    return !feature || (!featuresLoading && hasFeature(feature));
  });
  const filtered = visibleLogs.filter((l) => {
    if (channelFilter && l.channel !== channelFilter) return false;
    if (statusFilter && l.status !== statusFilter) return false;
    if (eventFilter && l.event_type !== eventFilter) return false;
    return true;
  });

  const SELECT_CLS =
    "rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">通知中心</h1>
          <p className="text-muted-foreground mt-1">
            近期系統與 AI 助理推給您的通知紀錄。
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/settings/notifications">
            <Button variant="outline" size="sm">
              通知設定
            </Button>
          </Link>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          className={SELECT_CLS}
          value={channelFilter}
          onChange={(e) => setChannelFilter(e.target.value)}
        >
          <option value="">全部管道</option>
          {Object.entries(CHANNEL_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        <select
          className={SELECT_CLS}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">全部狀態</option>
          <option value="sent">已送出</option>
          <option value="failed">失敗</option>
          <option value="skipped">略過</option>
        </select>
        <select
          className={SELECT_CLS}
          value={eventFilter}
          onChange={(e) => setEventFilter(e.target.value)}
        >
          <option value="">全部事件</option>
          {visibleEventTypes.map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        {(channelFilter || statusFilter || eventFilter) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setChannelFilter(""); setStatusFilter(""); setEventFilter(""); }}
          >
            清除篩選
          </Button>
        )}
      </div>

      {/* Stats row */}
      {visibleLogs.length > 0 && (
        <div className="flex gap-4 text-sm text-muted-foreground">
          <span>共 {visibleLogs.length} 筆</span>
          <span className="text-green-600">
            <CheckCircle2 className="inline h-3.5 w-3.5 mr-0.5" />
            {visibleLogs.filter((l) => l.status === "sent").length} 已送出
          </span>
          <span className="text-red-600">
            <XCircle className="inline h-3.5 w-3.5 mr-0.5" />
            {visibleLogs.filter((l) => l.status === "failed").length} 失敗
          </span>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground py-8">
          <Loader2 className="h-5 w-5 animate-spin" /> 載入中…
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          <Bell className="h-8 w-8 mx-auto mb-3 opacity-30" />
          <p className="text-sm">尚無通知記錄</p>
          {!visibleLogs.length && <p className="mt-1 text-xs">新 RFQ、客戶回覆與真人接手等系統事件發生後，記錄會顯示於此。</p>}
        </div>
      ) : (
        <div className="max-w-full overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">時間</th>
                <th className="text-left px-4 py-2.5 font-medium">管道</th>
                <th className="text-left px-4 py-2.5 font-medium">事件</th>
                <th className="text-left px-4 py-2.5 font-medium">訊息預覽</th>
                <th className="text-left px-4 py-2.5 font-medium">狀態</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((log) => (
                <tr key={log.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                    {formatDt(log.sent_at)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {CHANNEL_LABELS[log.channel] || log.channel}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium">
                      {EVENT_TYPE_LABELS[log.event_type] || log.event_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate text-muted-foreground">
                    {log.message_preview || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLS[log.status] || ""}`}
                    >
                      {log.status === "sent"
                        ? "已送出"
                        : log.status === "failed"
                        ? "失敗"
                        : "略過"}
                    </span>
                    {log.error_detail && (
                      <span className="ml-1 text-xs text-destructive" title={log.error_detail}>
                        ⚠
                      </span>
                    )}
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
