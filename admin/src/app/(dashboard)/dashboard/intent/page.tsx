"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Users, Flame, TrendingUp, Thermometer } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

type Visitor = {
  visitor_id: string;
  intent_score: number;
  intent_stage: string; // API returns lowercase: "cold"|"warm"|"hot"|"sales_ready"
  first_seen: string;
  last_seen: string;
  total_page_views: number;
  total_visits: number;
};

type Contact = {
  id: string;
  email: string;
  full_name?: string;
  company_name?: string;
  intent_score_at_creation: number;
  created_at: string;
};

type FunnelStage = { stage: string; visitors: number };
type FunnelData = {
  funnel_stages: FunnelStage[];
  totals: { visitors: number; rfqs: number };
};

// API returns lowercase stage names; map to display labels
const STAGE_DISPLAY: Record<string, string> = {
  sales_ready: "Sales-Ready",
  hot: "Hot",
  warm: "Warm",
  cold: "Cold",
};

const STAGE_COLOR: Record<string, string> = {
  sales_ready: "bg-red-100 text-red-700",
  hot: "bg-orange-100 text-orange-700",
  warm: "bg-yellow-100 text-yellow-800",
  cold: "bg-gray-100 text-gray-600",
};

export default function IntentPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  // topVisitors: top 10 by score (API already sorts DESC)
  const [topVisitors, setTopVisitors] = useState<Visitor[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [funnel, setFunnel] = useState<FunnelData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return; // Wait until authenticated
    setLoading(true); setError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [vRes, cRes, fRes] = await Promise.all([
        // Only need top 10 — API already sorts by score DESC
        fetch(`${API_BASE}/tracking/visitors?limit=10`, { headers }),
        fetch(`${API_BASE}/tracking/contacts?page_size=50`, { headers }),
        // Use funnel API with large window to get accurate all-time stage distribution
        fetch(`${API_BASE}/tracking/analytics/funnel?days=365`, { headers }),
      ]);
      if (!vRes.ok || !cRes.ok || !fRes.ok) {
        const errRes = !vRes.ok ? vRes : !cRes.ok ? cRes : fRes;
        const errJson = await errRes.json().catch(() => ({}));
        throw new Error(errJson.error ?? `API error ${errRes.status}`);
      }
      const vData = await vRes.json();
      const cData = await cRes.json();
      const fData = await fRes.json();
      setTopVisitors(Array.isArray(vData) ? vData : vData.items ?? []);
      setContacts(Array.isArray(cData) ? cData : cData.items ?? []);
      setFunnel(fData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  // Stage counts from funnel API (accurate, all visitors)
  const stageCounts = Object.fromEntries(
    (funnel?.funnel_stages ?? []).map((s) => [s.stage, s.visitors])
  );
  const totalVisitors = funnel?.totals?.visitors ?? 0;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Intent 意圖分析</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">即時訪客意圖分數與買家 Stage 分佈</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Stage Summary Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {(["cold", "warm", "hot", "sales_ready"] as const).map(key => (
          <Card key={key}>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{STAGE_DISPLAY[key]}</span>
                <Badge className={STAGE_COLOR[key] ?? ""}>{stageCounts[key] ?? 0}</Badge>
              </div>
              <p className="mt-2 text-3xl font-bold">{stageCounts[key] ?? 0}</p>
              <p className="text-xs text-muted-foreground">訪客</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Top Visitors */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Flame className="h-4 w-4 text-orange-500" />高意圖訪客 Top 10
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topVisitors.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">尚無訪客資料</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">訪客 ID</th>
                    <th className="px-3 py-2 text-center font-medium text-muted-foreground">Stage</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">分數</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">瀏覽頁數</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {topVisitors.map(v => (
                    <tr key={v.visitor_id} className="hover:bg-muted/30">
                      <td className="px-3 py-2 font-mono text-xs">{v.visitor_id?.slice(0, 8)}…</td>
                      <td className="px-3 py-2 text-center">
                        <Badge className={`text-xs ${STAGE_COLOR[v.intent_stage] ?? ""}`}>
                          {STAGE_DISPLAY[v.intent_stage] ?? v.intent_stage}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-right font-bold">{v.intent_score ?? 0}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">{v.total_page_views ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        {/* Contacts with Intent */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4 text-primary" />已識別聯絡人意圖
            </CardTitle>
          </CardHeader>
          <CardContent>
            {contacts.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">尚無已識別聯絡人</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">聯絡人</th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">公司</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">分數</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {contacts.slice(0, 10).map(c => (
                    <tr key={c.id} className="hover:bg-muted/30">
                      <td className="px-3 py-2">
                        <p className="font-medium">{c.full_name ?? "—"}</p>
                        <p className="text-xs text-muted-foreground">{c.email}</p>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground">{c.company_name ?? "—"}</td>
                      <td className="px-3 py-2 text-right font-bold">{c.intent_score_at_creation ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
        <span className="flex items-center gap-1"><TrendingUp className="h-4 w-4" />總訪客：{totalVisitors}</span>
        <span className="flex items-center gap-1"><Thermometer className="h-4 w-4" />已識別：{contacts.length}</span>
      </div>
    </div>
  );
}
