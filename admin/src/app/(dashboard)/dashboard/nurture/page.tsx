"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Mail, PlusCircle, ListChecks } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type Sequence = {
  id: string;
  name: string;
  description?: string;
  trigger?: string;
  step_count?: number;
  is_active?: boolean;
  enrollment_count?: number;
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
      const headers = { Authorization: `Bearer ${token}` };
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
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Nurture 引擎</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">自動化郵件引擎序列，將已識別訪客培育為高意圖潛在客戶</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" onClick={() => router.push("/dashboard/nurture/new")}>
            <PlusCircle className="mr-2 h-4 w-4" />新增序列
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
          <p className="text-sm text-muted-foreground">序列數量</p>
          <p className="mt-1 text-3xl font-bold">{sequences.length}</p>
        </CardContent></Card>
        <Card><CardContent className="pt-4 pb-4">
          <p className="text-sm text-muted-foreground">總入列數</p>
          <p className="mt-1 text-3xl font-bold">{enrollments.length}</p>
        </CardContent></Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Mail className="h-4 w-4 text-primary" />序列列表
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
            ) : sequences.length === 0 ? (
              <div className="py-12 text-center">
                <Mail className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">尚未建立 Nurture 序列</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">名稱</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">步驟</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">建立時間</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {sequences.map(s => (
                    <tr key={s.id} className="hover:bg-muted/30 cursor-pointer" onClick={() => router.push(`/dashboard/nurture/${s.id}`)}>
                      <td className="px-4 py-2 font-medium text-primary hover:underline">{s.name}</td>
                      <td className="px-4 py-2 text-center">{s.step_count ?? 0}</td>
                      <td className="px-4 py-2 text-center">
                        <Badge className={s.is_active !== false ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
                          {s.is_active !== false ? "啟用" : "停用"}
                        </Badge>
                      </td>
                      <td className="px-4 py-2 text-muted-foreground">{fmt(s.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ListChecks className="h-4 w-4 text-muted-foreground" />最新筆名記錄
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {enrollments.length === 0 ? (
              <div className="py-12 text-center">
                <ListChecks className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">尚無筆名記錄</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">聯絡人 ID</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                    <th className="px-4 py-2 text-center font-medium text-muted-foreground">當前步驟</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">筆名時間</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {enrollments.slice(0, 15).map(e => (
                    <tr key={e.id} className="hover:bg-muted/30">
                      <td className="px-4 py-2 font-mono text-xs">{e.contact_id?.slice(0, 8) ?? "—"}…</td>
                      <td className="px-4 py-2 text-center">
                        <Badge variant="outline" className="text-xs">{e.status ?? "active"}</Badge>
                      </td>
                      <td className="px-4 py-2 text-center">{e.current_step ?? 1}</td>
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
