"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Users, Flame, TrendingUp, Thermometer, Eye } from "lucide-react";
import { apiClient } from "@/lib/api/client";

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

type ContactListResponse = {
  items?: Contact[];
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return; // Wait until authenticated
    setLoading(true); setError(null);
    try {
      const [visitorsData, contactsData] = await Promise.all([
        apiClient.get<Visitor[]>("/tracking/visitors?limit=10", token),
        apiClient.get<ContactListResponse | Contact[]>("/tracking/contacts?page_size=50", token),
      ]);
      setTopVisitors(Array.isArray(visitorsData) ? visitorsData : []);
      setContacts(Array.isArray(contactsData) ? contactsData : contactsData.items ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  // Per-visitor KPIs derived from top-10 list
  const topScore = topVisitors[0]?.intent_score ?? 0;
  const avgScore = topVisitors.length
    ? Math.round(topVisitors.reduce((s, v) => s + (v.intent_score ?? 0), 0) / topVisitors.length)
    : 0;
  const salesReadyCount = topVisitors.filter((v) => v.intent_stage === "sales_ready").length;
  const identifiedCount = contacts.length;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">意圖分析</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">追蹤高意圖個別訪客，找出最值得跟進的潛在買家</p>
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

      {/* Actionable KPI Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">最高意圖分數</p>
            <p className="mt-2 text-3xl font-bold">{topScore}</p>
            <p className="text-xs text-muted-foreground">Top 1 訪客</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">Top 10 平均分數</p>
            <p className="mt-2 text-3xl font-bold">{avgScore}</p>
            <p className="text-xs text-muted-foreground">高意圖訪客均值</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">Sales-Ready（Top 10）</p>
            <p className="mt-2 text-3xl font-bold">{salesReadyCount}</p>
            <p className="text-xs text-muted-foreground">可立即跟進</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">已識別聯絡人</p>
            <p className="mt-2 text-3xl font-bold">{identifiedCount}</p>
            <p className="text-xs text-muted-foreground">留下資料的訪客</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Top Visitors — Actionable Worktable */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Flame className="h-4 w-4 text-orange-500" />高意圖訪客工作台
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topVisitors.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">尚無訪客資料</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">訪客</th>
                    <th className="px-3 py-2 text-center font-medium text-muted-foreground">Stage</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">分數</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">瀏覽頁數</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">最後活動</th>
                    <th className="px-3 py-2 text-center font-medium text-muted-foreground">動作</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {topVisitors.map(v => (
                    <tr key={v.visitor_id} className="hover:bg-muted/30">
                      <td className="px-3 py-2">
                        <Link href={`/dashboard/visitors/${v.visitor_id}`} className="font-mono text-xs text-primary hover:underline">
                          {v.visitor_id?.slice(0, 8)}…
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <Badge className={`text-xs ${STAGE_COLOR[v.intent_stage] ?? ""}`}>
                          {STAGE_DISPLAY[v.intent_stage] ?? v.intent_stage}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-right font-bold">{v.intent_score ?? 0}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">{v.total_page_views ?? 0}</td>
                      <td className="px-3 py-2 text-right text-xs text-muted-foreground">
                        {v.last_seen ? new Date(v.last_seen).toLocaleDateString("zh-TW", { month: "short", day: "numeric" }) : "—"}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Button asChild variant="ghost" size="icon" className="h-7 w-7" title="查看旅程">
                            <Link href={`/dashboard/visitors/${v.visitor_id}`}>
                              <Eye className="h-3.5 w-3.5" />
                            </Link>
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

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
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
        <span className="flex items-center gap-1"><TrendingUp className="h-4 w-4" />顯示 Top {topVisitors.length} 高意圖訪客</span>
        <span className="flex items-center gap-1"><Thermometer className="h-4 w-4" />已識別聯絡人：{identifiedCount}</span>
      </div>
    </div>
  );
}
