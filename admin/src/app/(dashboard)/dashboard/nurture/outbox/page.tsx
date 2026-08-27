"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Send, SkipForward, Inbox } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

type OutboxItem = {
  id: string;
  enrollment_id: string;
  sequence_id: string;
  step_id: string;
  contact_id: string;
  status: string;
  subject: string;
  due_at?: string;
  created_at?: string;
  sent_at?: string;
  error?: string;
};

function fmt(d?: string) {
  return d ? new Date(d).toLocaleString("zh-TW") : "—";
}

export default function NurtureOutboxPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [items, setItems] = useState<OutboxItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [acting, setActing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/nurture/outbox?outbox_status=pending&limit=100`, {
        headers: buildApiHeaders(token),
      });
      const data = await res.json();
      setItems(Array.isArray(data) ? data : data.items ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const act = async (id: string, action: "send" | "skip") => {
    setActing(id); setMessage("");
    try {
      const res = await fetch(`${API_BASE}/nurture/outbox/${id}/${action}`, {
        method: "POST",
        headers: buildApiHeaders(token),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "操作失敗");
      setMessage(action === "send" ? "已寄出" : "已略過並前進到下一步");
      await load();
    } catch (e: unknown) {
      setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally { setActing(null); }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">待寄郵件</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">到期的跟進郵件會先進入此佇列，確認後始可寄出。</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {message && <Alert><AlertDescription>{message}</AlertDescription></Alert>}
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">待確認（{items.length}）</CardTitle>
        </CardHeader>
        <CardContent className="max-w-full overflow-x-auto p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : items.length === 0 ? (
            <div className="py-12 text-center">
              <Inbox className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">目前沒有待寄的跟進郵件</p>
            </div>
          ) : (
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">主旨</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">聯絡人</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">到期</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {items.map((o) => (
                  <tr key={o.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">{o.subject}</td>
                    <td className="px-4 py-2 font-mono text-xs">{o.contact_id.slice(0, 8)}</td>
                    <td className="px-4 py-2 text-muted-foreground">{fmt(o.due_at)}</td>
                    <td className="px-4 py-2 text-center">
                      <Badge variant="outline" className="text-xs">{o.status}</Badge>
                    </td>
                    <td className="px-4 py-2 text-right">
                      <div className="inline-flex gap-2">
                        <Button size="sm" disabled={acting === o.id} onClick={() => act(o.id, "send")}>
                          <Send className="mr-1 h-3.5 w-3.5" />確認寄出
                        </Button>
                        <Button size="sm" variant="outline" disabled={acting === o.id} onClick={() => act(o.id, "skip")}>
                          <SkipForward className="mr-1 h-3.5 w-3.5" />略過
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
