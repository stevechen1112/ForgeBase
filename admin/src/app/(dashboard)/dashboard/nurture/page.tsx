"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Mail, PlusCircle, ListChecks } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

type Sequence = {
  id: string;
  name: string;
  description?: string;
  trigger_type?: string;
  trigger_value?: string;
  step_count?: number;
  is_active?: boolean;
  is_approved?: boolean;
  created_at?: string;
};

type Enrollment = {
  id: string;
  sequence_id?: string;
  contact_id?: string;
  status?: string;
  current_step?: number;
  enrolled_at?: string;
};

function fmt(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("zh-TW");
}

export default function NurturePage() {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const headers = buildApiHeaders(token);
      const [sRes, eRes] = await Promise.all([
        fetch(`${API_BASE}/nurture/sequences`, { headers }),
        fetch(`${API_BASE}/nurture/enrollments`, { headers }),
      ]);
      const sData = await sRes.json();
      const eData = await eRes.json();
      setSequences(Array.isArray(sData) ? sData : sData.items ?? []);
      setEnrollments(Array.isArray(eData) ? eData : eData.items ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">跟進郵件</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">依買家關注程度排程跟進郵件；須經核准後始可寄出（如第 0／3／7 天）。</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" onClick={() => router.push("/dashboard/nurture/new")}>
            <PlusCircle className="mr-2 h-4 w-4" />新增流程
          </Button>
          <Button variant="outline" size="sm" onClick={() => router.push("/dashboard/nurture/outbox")}>
            <ListChecks className="mr-2 h-4 w-4" />待寄郵件
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="mb-4 grid grid-cols-2 gap-4">
        <Card><CardContent className="pt-4 pb-4">
          <p className="text-sm text-muted-foreground">流程總數</p>
          <p className="mt-1 text-3xl font-bold">{sequences.length}</p>
        </CardContent></Card>
        <Card><CardContent className="pt-4 pb-4">
          <p className="text-sm text-muted-foreground">進行中的人數</p>
          <p className="mt-1 text-3xl font-bold">{enrollments.length}</p>
        </CardContent></Card>
      </div>

      <div className="grid gap-6 2xl:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Mail className="h-4 w-4 text-primary" />跟進流程
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto p-0">
            {loading ? (
              <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
            ) : sequences.length === 0 ? (
              <div className="py-12 text-center">
                <Mail className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">尚未建立任何跟進流程</p>
              </div>
            ) : (
              <table className="w-full min-w-[680px] table-fixed text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">名稱</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">觸發</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">步驟</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">建立時間</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {sequences.map(s => (
                    <tr key={s.id} className="hover:bg-muted/30 cursor-pointer" onClick={() => router.push(`/dashboard/nurture/${s.id}`)}>
                      <td className="px-4 py-2 font-medium text-primary hover:underline">
                        <span className="line-clamp-2 break-words">{s.name}</span>
                      </td>
                      <td className="px-4 py-2 text-xs text-muted-foreground">
                        <span className="line-clamp-2 break-all">{s.trigger_type ?? "manual"}{s.trigger_value ? ` · ${s.trigger_value}` : ""}</span>
                      </td>
                      <td className="px-4 py-2 text-center">{s.step_count ?? 0}</td>
                      <td className="px-4 py-2 text-center align-middle">
                        <div className="flex flex-wrap justify-center gap-1">
                        <Badge className={s.is_active !== false ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
                          {s.is_active !== false ? "啟用" : "停用"}
                        </Badge>
                        {s.is_approved ? (
                          <Badge className="bg-blue-100 text-blue-700">已核准</Badge>
                        ) : (
                          <Badge variant="outline" className="border-amber-300 text-amber-600">待核准</Badge>
                        )}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-muted-foreground">{fmt(s.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ListChecks className="h-4 w-4 text-muted-foreground" />最近加入
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto p-0">
            {enrollments.length === 0 ? (
              <div className="py-12 text-center">
                <ListChecks className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">尚無加入紀錄</p>
              </div>
            ) : (
              <table className="w-full min-w-[520px] text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">聯絡人 ID</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">目前步驟</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">加入時間</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {enrollments.slice(0, 15).map(e => (
                    <tr key={e.id} className="hover:bg-muted/30">
                      <td className="px-4 py-2 font-mono text-xs">{e.contact_id?.slice(0, 8) ?? "—"}</td>
                      <td className="px-4 py-2 text-center">
                        <Badge variant="outline" className="text-xs">{e.status ?? "active"}</Badge>
                      </td>
                      <td className="px-4 py-2 text-center">{e.current_step ?? 0}</td>
                      <td className="px-4 py-2 text-muted-foreground">{fmt(e.enrolled_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
