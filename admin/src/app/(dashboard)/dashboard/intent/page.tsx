"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Users, Flame, TrendingUp, Thermometer } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type Visitor = {
  id: string;
  visitor_uuid: string;
  intent_score: number;
  intent_stage: string;
  first_seen: string;
  last_seen: string;
  page_views: number;
  events_count: number;
};

type Contact = {
  id: string;
  email: string;
  full_name?: string;
  company_name?: string;
  intent_score_at_creation: number;
  created_at: string;
};

const STAGE_COLOR: Record<string, string> = {
  "Sales-Ready": "bg-red-100 text-red-700",
  Hot: "bg-orange-100 text-orange-700",
  Warm: "bg-yellow-100 text-yellow-800",
  Cold: "bg-gray-100 text-gray-600",
};

export default function IntentPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [visitors, setVisitors] = useState<Visitor[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [vRes, cRes] = await Promise.all([
        fetch(`${API_BASE}/tracking/visitors?page_size=50`, { headers }),
        fetch(`${API_BASE}/tracking/contacts?page_size=50`, { headers }),
      ]);
      const vData = await vRes.json();
      const cData = await cRes.json();
      setVisitors(Array.isArray(vData) ? vData : vData.items ?? []);
      setContacts(Array.isArray(cData) ? cData : cData.items ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const stageCounts = visitors.reduce<Record<string, number>>((acc, v) => {
    const s = v.intent_stage ?? "Cold";
    acc[s] = (acc[s] ?? 0) + 1;
    return acc;
  }, {});

  const topVisitors = [...visitors].sort((a, b) => (b.intent_score ?? 0) - (a.intent_score ?? 0)).slice(0, 10);

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
        {["Cold", "Warm", "Hot", "Sales-Ready"].map(s => (
          <Card key={s}>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{s}</span>
                <Badge className={STAGE_COLOR[s] ?? ""}>{stageCounts[s] ?? 0}</Badge>
              </div>
              <p className="mt-2 text-3xl font-bold">{stageCounts[s] ?? 0}</p>
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
            {visitors.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">尚無訪客資料</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">UUID</th>
                    <th className="px-3 py-2 text-center font-medium text-muted-foreground">Stage</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">分數</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">事件</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {topVisitors.map(v => (
                    <tr key={v.id} className="hover:bg-muted/30">
                      <td className="px-3 py-2 font-mono text-xs">{v.visitor_uuid?.slice(0, 8)}…</td>
                      <td className="px-3 py-2 text-center">
                        <Badge className={`text-xs ${STAGE_COLOR[v.intent_stage] ?? ""}`}>{v.intent_stage ?? "Cold"}</Badge>
                      </td>
                      <td className="px-3 py-2 text-right font-bold">{v.intent_score ?? 0}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">{v.events_count ?? 0}</td>
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
        <span className="flex items-center gap-1"><TrendingUp className="h-4 w-4" />總訪客：{visitors.length}</span>
        <span className="flex items-center gap-1"><Thermometer className="h-4 w-4" />已識別：{contacts.length}</span>
      </div>
    </div>
  );
}
