"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Building2, ChevronLeft, ChevronRight } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type Account = {
  id: string;
  company_name?: string;
  domain?: string;
  country?: string;
  industry?: string;
  employee_count?: number;
  total_intent_score?: number;
  intent_stage?: string;
  visitor_count?: number;
  last_seen?: string;
};

const STAGE_COLOR: Record<string, string> = {
  "Sales-Ready": "bg-red-100 text-red-700",
  Hot: "bg-orange-100 text-orange-700",
  Warm: "bg-yellow-100 text-yellow-800",
  Cold: "bg-gray-100 text-gray-600",
};

function fmt(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("zh-TW");
}

export default function AccountsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const PAGE_SIZE = 20;

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/accounts?page=${page}&page_size=${PAGE_SIZE}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => {
        setAccounts(Array.isArray(d) ? d : d.items ?? []);
        setTotal(d.total ?? (Array.isArray(d) ? d.length : 0));
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, page]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">企業訪客識別</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">通過 IP 反查識別潛在公司帳戶，共 {total} 筆</p>
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

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Building2 className="h-4 w-4 text-primary" />帳戶列表
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : accounts.length === 0 ? (
            <div className="py-16 text-center">
              <Building2 className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground">尚未識別任何公司帳戶</p>
              <p className="mt-1 text-xs text-muted-foreground">IP 反查功能需要配置 Clearbit 或相似服務</p>
            </div>
          ) : (
            <>
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">公司</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">域名</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">國家</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">Stage</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">意圖分</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">最近活動</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {accounts.map(a => (
                    <tr key={a.id} className="hover:bg-muted/30">
                      <td className="px-4 py-2 font-medium">{a.company_name ?? "—"}</td>
                      <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{a.domain ?? "—"}</td>
                      <td className="px-4 py-2 text-muted-foreground">{a.country ?? "—"}</td>
                      <td className="px-4 py-2 text-center">
                        {a.intent_stage && (
                          <Badge className={`text-xs ${STAGE_COLOR[a.intent_stage] ?? ""}`}>{a.intent_stage}</Badge>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right font-bold">{a.total_intent_score ?? 0}</td>
                      <td className="px-4 py-2 text-muted-foreground">{fmt(a.last_seen)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t px-4 py-3">
                  <span className="text-xs text-muted-foreground">{page} / {totalPages} 頁</span>
                  <div className="flex gap-1">
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
