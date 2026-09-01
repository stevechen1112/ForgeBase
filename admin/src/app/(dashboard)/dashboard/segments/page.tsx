"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Users, PlusCircle } from "lucide-react";
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
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">等待跟進的買家</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">依市場與網站互動整理待跟進名單；這不是自動評分，也不會自動投放廣告。</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" onClick={() => router.push("/dashboard/segments/new")}>
            <PlusCircle className="mr-2 h-4 w-4" />建立跟進名單條件
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
            <Users className="h-4 w-4 text-primary" />跟進名單條件（{segments.length}）
          </CardTitle>
        </CardHeader>
        <CardContent className="max-w-full overflow-x-auto p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : segments.length === 0 ? (
            <div className="py-16 text-center">
              <Users className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground">尚未建立任何跟進名單條件</p>
              <p className="mt-1 text-xs text-muted-foreground">先設定市場或網站互動條件，符合的訪客會出現在待跟進名單中。</p>
            </div>
          ) : (
            <table className="w-full min-w-[720px] text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">名稱</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">說明</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">符合人數</th>
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
