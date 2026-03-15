"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Users } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

type Segment = {
  id: string;
  name: string;
  description: string;
  conditions: string;
  combinator: string;
  created_at: string;
  updated_at: string;
};

type EvalResult = {
  matched_count?: number;
  count?: number;
  sample_visitors?: { visitor_id: string; intent_stage: string; intent_score: number }[];
};

function fmt(d?: string) {
  return d ? new Date(d).toLocaleDateString("zh-TW") : "—";
}

const FIELD_LABELS: Record<string, string> = {
  intent_stage: "意圖階段",
  intent_score: "意圖分數",
  country: "國家",
  event_count: "事件次數",
};

export default function SegmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [seg, setSeg] = useState<Segment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  // Edit fields
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  // Evaluate
  const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tracking/segments/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Segment 不存在");
      const data: Segment = await res.json();
      setSeg(data);
      setName(data.name);
      setDescription(data.description);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [id, token]);

  useEffect(() => { if (token) load(); }, [load, token]);

  const save = async () => {
    setSaving(true); setMessage("");
    try {
      const res = await fetch(`${API_BASE}/tracking/segments/${id}`, {
        method: "PATCH", headers,
        body: JSON.stringify({ name, description }),
      });
      if (!res.ok) throw new Error("儲存失敗");
      setMessage("已更新 ✓");
      await load();
    } catch (e: unknown) {
      setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally { setSaving(false); }
  };

  const evaluate = async () => {
    setEvaluating(true);
    try {
      const res = await fetch(`${API_BASE}/tracking/segments/${id}/evaluate`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setEvalResult(await res.json());
    } catch { /* ignore */ }
    finally { setEvaluating(false); }
  };

  if (loading) return <p className="py-10 text-center text-muted-foreground">載入中…</p>;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!seg) return null;

  let conditions: Record<string, unknown>[] = [];
  try { conditions = JSON.parse(seg.conditions); } catch { /* ignore */ }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{seg.name}</h1>
        <Button variant="outline" size="sm" onClick={() => router.push("/dashboard/segments")}>← 返回列表</Button>
      </div>

      {message && <Alert><AlertDescription>{message}</AlertDescription></Alert>}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Edit basic info */}
        <Card>
          <CardHeader><CardTitle className="text-base">基本資料</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label className="text-xs">名稱</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">說明</Label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <p className="text-xs text-muted-foreground">建立於 {fmt(seg.created_at)}</p>
            <Button size="sm" className="w-full" disabled={saving} onClick={save}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}儲存
            </Button>
          </CardContent>
        </Card>

        {/* Conditions display */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">條件規則</CardTitle>
              <Badge variant="secondary">{seg.combinator}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {conditions.length === 0 ? (
              <p className="text-sm text-muted-foreground">無條件</p>
            ) : (
              conditions.map((c, i) => (
                <div key={i} className="flex items-center gap-2 rounded border p-2 text-sm">
                  {i > 0 && <Badge variant="outline" className="text-xs">{seg.combinator}</Badge>}
                  <Badge>{FIELD_LABELS[String(c.field)] || String(c.field)}</Badge>
                  <span className="text-muted-foreground">{String(c.operator)}</span>
                  <span className="font-medium">{String(c.value)}</span>
                  {c.event_name && <span className="text-xs text-muted-foreground">(事件: {String(c.event_name)}, {String(c.within_days || 30)} 天內)</span>}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Evaluate */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">受眾評估</CardTitle>
            <Button size="sm" variant="outline" onClick={evaluate} disabled={evaluating}>
              {evaluating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Users className="mr-2 h-4 w-4" />}
              重新評估
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {evalResult ? (
            <div className="space-y-3">
              <p className="text-lg font-bold">
                符合 <span className="text-primary">{evalResult.matched_count ?? evalResult.count ?? 0}</span> 位訪客
              </p>
              {evalResult.sample_visitors && evalResult.sample_visitors.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">樣本訪客：</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {evalResult.sample_visitors.map((v) => (
                      <div key={v.visitor_id} className="rounded border p-2 text-xs">
                        <p className="font-mono truncate">{v.visitor_id.slice(0, 12)}…</p>
                        <p className="text-muted-foreground">{v.intent_stage} / {v.intent_score}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">點擊「重新評估」以查看符合此分群的訪客數量</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
