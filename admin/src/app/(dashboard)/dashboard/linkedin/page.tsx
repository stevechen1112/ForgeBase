"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Linkedin, PlusCircle, Users } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type Audience = {
  id: string;
  name: string;
  description?: string;
  match_type?: string;
  member_count?: number;
  status?: string;
  segment_id?: string;
  synced_at?: string;
  created_at?: string;
};

function fmt(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("zh-TW");
}

export default function LinkedInPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [audiences, setAudiences] = useState<Audience[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/linkedin-audiences`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setAudiences(Array.isArray(d) ? d : d.items ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">LinkedIn Audience</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">將高意圖受眾分群同步至 LinkedIn，用於投放精準広告</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" disabled>
            <PlusCircle className="mr-2 h-4 w-4" />建立受眾
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
            <Linkedin className="h-4 w-4 text-[#0077B5]" />LinkedIn 受眾列表（{audiences.length}）
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : audiences.length === 0 ? (
            <div className="py-16 text-center">
              <Linkedin className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground">尚未建立 LinkedIn 受眾</p>
              <p className="mt-1 text-xs text-muted-foreground">需要先建立受眾分群，再將其同步至 LinkedIn Campaign Manager</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">名稱</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">比對類型</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">成員數</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">最後同步</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {audiences.map(a => (
                  <tr key={a.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">{a.name}</td>
                    <td className="px-4 py-2 text-muted-foreground">{a.match_type ?? "—"}</td>
                    <td className="px-4 py-2 text-center">
                      <Badge className={a.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
                        {a.status ?? "pending"}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-right font-bold">
                      <span className="flex items-center justify-end gap-1">
                        <Users className="h-3 w-3" />{a.member_count ?? 0}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{fmt(a.synced_at)}</td>
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
