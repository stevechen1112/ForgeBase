"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, FlaskConical, PlusCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type ABTest = {
  id: string;
  name: string;
  description?: string;
  status?: string;
  page_slug?: string;
  variant_count?: number;
  winner_variant?: string;
  started_at?: string;
  ended_at?: string;
  created_at?: string;
};

const STATUS_COLOR: Record<string, string> = {
  running: "bg-green-100 text-green-700",
  paused: "bg-yellow-100 text-yellow-700",
  ended: "bg-gray-100 text-gray-600",
  draft: "bg-blue-100 text-blue-700",
};

function fmt(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("zh-TW");
}

export default function ABTestsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [tests, setTests] = useState<ABTest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/ab-tests/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setTests(Array.isArray(d) ? d : d.items ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const statusCounts = tests.reduce<Record<string, number>>((acc, t) => {
    const s = t.status ?? "draft";
    acc[s] = (acc[s] ?? 0) + 1;
    return acc;
  }, {});

  const STATUS_LABEL: Record<string, string> = {
    running: "進行中",
    paused: "已暫停",
    ended: "已結束",
    draft: "草稿",
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">A/B 測試</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">測試頁面標題、CTA 文字、版面配置對轉換率的影響</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" disabled>
            <PlusCircle className="mr-2 h-4 w-4" />新增測試
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {tests.length > 0 && (
        <div className="mb-6 grid grid-cols-4 gap-4">
          {["running", "paused", "ended", "draft"].map(s => (
            <Card key={s}>
              <CardContent className="pt-4 pb-4">
                <p className="text-sm text-muted-foreground">{STATUS_LABEL[s] ?? s}</p>
                <p className="mt-1 text-3xl font-bold">{statusCounts[s] ?? 0}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FlaskConical className="h-4 w-4 text-primary" />測試列表（{tests.length}）
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : tests.length === 0 ? (
            <div className="py-16 text-center">
              <FlaskConical className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground">尚未建立 A/B 測試</p>
              <p className="mt-1 text-xs text-muted-foreground">建立測試實驗，比較不同牌面變形的轉換效率</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">測試名稱</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">頁面</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">變形數</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">勝出變形</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">開始時間</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tests.map(t => (
                  <tr key={t.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">{t.name}</td>
                    <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{t.page_slug ?? "—"}</td>
                    <td className="px-4 py-2 text-center">
                      <Badge className={`text-xs ${STATUS_COLOR[t.status ?? "draft"] ?? ""}`}>{t.status ?? "draft"}</Badge>
                    </td>
                    <td className="px-4 py-2 text-center">{t.variant_count ?? 2}</td>
                    <td className="px-4 py-2 text-muted-foreground">{t.winner_variant ?? "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground">{fmt(t.started_at ?? t.created_at)}</td>
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
