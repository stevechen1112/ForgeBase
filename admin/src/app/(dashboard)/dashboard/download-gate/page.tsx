"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Lock, FileDown, Users } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type GatedAsset = {
  id: string;
  original_filename: string;
  title?: string;
  public_url?: string;
  asset_type?: string;
  file_size_bytes?: number;
  requires_gate?: boolean;
  created_at?: string;
};

type GateSubmission = {
  id: string;
  email?: string;
  full_name?: string;
  company_name?: string;
  asset_id?: string;
  created_at?: string;
};

function formatSize(bytes?: number) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function DownloadGatePage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [assets, setAssets] = useState<GatedAsset[]>([]);
  const [submissions, setSubmissions] = useState<GateSubmission[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [aRes, sRes] = await Promise.all([
        fetch(`${API_BASE}/content/assets?requires_gate=true&page_size=50`, { headers }),
        fetch(`${API_BASE}/tracking/contacts?page_size=50`, { headers }),
      ]);
      const aData = await aRes.json();
      const sData = await sRes.json();
      const gatedAssets = (Array.isArray(aData) ? aData : aData.data ?? []).filter((a: GatedAsset) => a.requires_gate);
      setAssets(gatedAssets);
      setSubmissions(Array.isArray(sData) ? sData : sData.items ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Download Gate</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">需填表才能下載的受保護資產管理與下載請求紀錄</p>
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

      <div className="mb-4 grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4 flex items-center gap-3">
            <Lock className="h-8 w-8 text-primary/60" />
            <div><p className="text-sm text-muted-foreground">閘控資產</p><p className="text-3xl font-bold">{assets.length}</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 flex items-center gap-3">
            <Users className="h-8 w-8 text-green-500/60" />
            <div><p className="text-sm text-muted-foreground">表單提交紀錄</p><p className="text-3xl font-bold">{submissions.length}</p></div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Gated Assets */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileDown className="h-4 w-4 text-primary" />受保護下載資產（{assets.length}）
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
            ) : assets.length === 0 ? (
              <div className="py-12 text-center">
                <Lock className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">尚無閘控資產</p>
                <p className="mt-1 text-xs text-muted-foreground">在媒體庫上傳資產時，開啟「需要表單」選項</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">檔案</th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">類型</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground">大小</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {assets.map(a => (
                    <tr key={a.id} className="hover:bg-muted/30">
                      <td className="px-3 py-2">
                        <p className="font-medium truncate max-w-[160px]">{a.title ?? a.original_filename}</p>
                        <Badge className="mt-0.5 text-xs bg-red-100 text-red-700">
                          <Lock className="mr-1 h-2.5 w-2.5" />需要填表
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground uppercase text-xs">{a.asset_type ?? "—"}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">{formatSize(a.file_size_bytes)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        {/* Gate Submissions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4 text-green-500" />下載聯絡人（{submissions.length}）
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {submissions.length === 0 ? (
              <div className="py-12 text-center">
                <Users className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">尚無填表下載紀錄</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">聯絡人</th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">公司</th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">時間</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {submissions.slice(0, 15).map(s => (
                    <tr key={s.id} className="hover:bg-muted/30">
                      <td className="px-3 py-2">
                        <p className="font-medium">{s.full_name ?? "—"}</p>
                        <p className="text-xs text-muted-foreground">{s.email}</p>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground">{s.company_name ?? "—"}</td>
                      <td className="px-3 py-2 text-muted-foreground text-xs">
                        {s.created_at ? new Date(s.created_at).toLocaleDateString("zh-TW") : "—"}
                      </td>
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
