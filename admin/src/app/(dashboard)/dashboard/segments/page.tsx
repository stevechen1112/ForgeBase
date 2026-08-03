"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { RefreshCw, Users, PlusCircle, Send } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

type Segment = {
  id: string;
  name: string;
  description?: string;
  rules?: Record<string, unknown>[];
  member_count?: number;
  is_active?: boolean;
  created_at?: string;
};

function fmt(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("zh-TW");
}

/* ── Sync to ESP Dialog ───────────────────────────────────────── */
function SyncToEspDialog({ token, segmentId, segmentName }: { token: string; segmentId: string; segmentName: string }) {
  const [open, setOpen] = useState(false);
  const [provider, setProvider] = useState<"sendgrid" | "mailchimp">("sendgrid");
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function doSync() {
    setSyncing(true); setResult(null);
    try {
      const r = await fetch(`${API_BASE}/tracking/segments/${segmentId}/sync-to-esp?provider=${provider}`, {
        method: "POST",
        headers: buildApiHeaders(token),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail ?? r.statusText);
      setResult(`完成：匹配訪客 ${d.visitors_matched}、聯絡人 ${d.contacts_matched}，成功 ${d.success}、失敗 ${d.failed}`);
    } catch (e: unknown) {
      setResult(e instanceof Error ? e.message : "同步失敗");
    } finally { setSyncing(false); }
  }

  return (
    <Dialog open={open} onOpenChange={v => { setOpen(v); if (!v) { setResult(null); } }}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" onClick={e => e.stopPropagation()}>
          <Send className="mr-2 h-4 w-4" />同步到 ESP
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm" onClick={e => e.stopPropagation()}>
        <DialogHeader><DialogTitle>同步「{segmentName}」到 ESP</DialogTitle></DialogHeader>
        <div className="space-y-4 py-2">
          {result && (
            <Alert variant={result.includes("失敗") && !result.includes("成功") ? "destructive" : "default"}>
              <AlertDescription>{result}</AlertDescription>
            </Alert>
          )}
          <div className="space-y-1">
            <label className="text-sm font-medium">ESP 供應商</label>
            <select
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={provider}
              onChange={e => setProvider(e.target.value as "sendgrid" | "mailchimp")}
            >
              <option value="sendgrid">SendGrid</option>
              <option value="mailchimp">Mailchimp</option>
            </select>
            <p className="text-xs text-muted-foreground">
              將此受眾匹配的聯絡人同步到所選 ESP 行銷清單
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
            <Button onClick={doSync} disabled={syncing}>
              {syncing ? "同步中…" : "開始同步"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function SegmentsPage() {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/segments`, { headers: buildApiHeaders(token) })
      .then(r => r.json())
      .then(d => setSegments(Array.isArray(d) ? d : d.items ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">自訂受眾</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">依行為條件定義目標族群，用於再行銷受眾與廣告投放</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" onClick={() => router.push("/dashboard/segments/new")}>
            <PlusCircle className="mr-2 h-4 w-4" />新增 Segment
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-4 w-4 text-primary" />分群列表（{segments.length}）
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : segments.length === 0 ? (
            <div className="py-16 text-center">
              <Users className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground">尚未建立任何受眾分群</p>
              <p className="mt-1 text-xs text-muted-foreground">透過 API 或後台設定建立分群規則，訪客將自動歸分</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">名稱</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">說明</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">成員數</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">建立時間</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {segments.map(s => (
                  <tr key={s.id} className="hover:bg-muted/30 cursor-pointer" onClick={() => router.push(`/dashboard/segments/${s.id}`)}>
                    <td className="px-4 py-2 font-medium text-primary hover:underline">{s.name}</td>
                    <td className="px-4 py-2 text-muted-foreground">{s.description ?? "—"}</td>
                    <td className="px-4 py-2 text-center">
                      <Badge className={s.is_active !== false ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
                        {s.is_active !== false ? "啟用" : "停用"}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-right font-bold">{s.member_count ?? 0}</td>
                    <td className="px-4 py-2 text-muted-foreground">{fmt(s.created_at)}</td>
                    <td className="px-4 py-2 text-right" onClick={e => e.stopPropagation()}>
                      <SyncToEspDialog token={token} segmentId={s.id} segmentName={s.name} />
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
