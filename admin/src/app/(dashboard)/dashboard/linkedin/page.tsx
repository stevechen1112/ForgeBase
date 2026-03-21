"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RefreshCw, Linkedin, PlusCircle, Users, Play, AlertCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type Audience = {
  id: string;
  name: string;
  description?: string;
  audience_type?: string;    // "EMAIL" | "COMPANY"
  source_type?: string;      // "segment" | "contacts_all"
  source_segment_id?: string;
  linkedin_segment_id?: string;
  status?: string;           // pending | syncing | synced | error
  last_record_count?: number;
  last_sync_at?: string;
  error_message?: string;
  created_at?: string;
};

type Segment = { id: string; name: string };

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  pending:  { label: "等待同步", className: "bg-gray-100 text-gray-600" },
  syncing:  { label: "同步中…",  className: "bg-blue-100 text-blue-700" },
  synced:   { label: "已同步",   className: "bg-green-100 text-green-700" },
  error:    { label: "發生錯誤", className: "bg-red-100 text-red-700" },
};

const AUDIENCE_TYPE_LABEL: Record<string, string> = {
  EMAIL:   "電子郵件",
  COMPANY: "公司名稱",
};

const SOURCE_TYPE_LABEL: Record<string, string> = {
  segment:      "自訂分群",
  contacts_all: "全部聯絡人",
};

function fmt(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("zh-TW");
}

export default function LinkedInPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [audiences, setAudiences] = useState<Audience[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [liConfigured, setLiConfigured] = useState<boolean | null>(null);

  // Create dialog state
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    audience_type: "EMAIL",
    source_type: "segment",
    source_segment_id: "",
  });

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/linkedin-audiences`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setAudiences(Array.isArray(d) ? d : d.items ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  const loadSegments = useCallback(() => {
    fetch(`${API_BASE}/tracking/segments`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setSegments(Array.isArray(d) ? d : d.items ?? []))
      .catch(() => {});
  }, [token]);

  const checkLinkedInConfig = useCallback(() => {
    fetch(`${API_BASE}/esp/status`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setLiConfigured(d.linkedin_configured ?? false))
      .catch(() => setLiConfigured(false));
  }, [token]);

  useEffect(() => { load(); loadSegments(); checkLinkedInConfig(); }, [load, loadSegments, checkLinkedInConfig]);

  const handleSync = async (id: string) => {
    setSyncing(id);
    try {
      await fetch(`${API_BASE}/tracking/linkedin-audiences/${id}/sync`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setTimeout(load, 1000);
    } catch {
      // ignore
    } finally {
      setSyncing(null);
    }
  };

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      const body: Record<string, string> = {
        name: form.name.trim(),
        audience_type: form.audience_type,
        source_type: form.source_type,
      };
      if (form.description.trim()) body.description = form.description.trim();
      if (form.source_type === "segment" && form.source_segment_id) {
        body.source_segment_id = form.source_segment_id;
      }
      await fetch(`${API_BASE}/tracking/linkedin-audiences`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setOpen(false);
      setForm({ name: "", description: "", audience_type: "EMAIL", source_type: "segment", source_segment_id: "" });
      load();
    } catch {
      // ignore
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">LinkedIn Audience</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">將高意圖受眾分群同步至 LinkedIn，用於投放精準廣告</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" onClick={() => setOpen(true)}>
            <PlusCircle className="mr-2 h-4 w-4" />建立受眾
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {liConfigured === false && (
        <Alert className="mb-4 border-yellow-300 bg-yellow-50 text-yellow-900">
          <AlertCircle className="h-4 w-4 text-yellow-600" />
          <AlertDescription className="ml-2">
            <span className="font-semibold">LinkedIn 尚未串接。</span>{" "}
            同步功能需要在伺服器設定兩個環境變數：
            <code className="mx-1 rounded bg-yellow-100 px-1 text-xs">LINKEDIN_ACCESS_TOKEN</code>
            與
            <code className="mx-1 rounded bg-yellow-100 px-1 text-xs">LINKEDIN_AD_ACCOUNT_ID</code>。
            設定完成後此提示會自動消失。
          </AlertDescription>
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
              <p className="mt-1 text-xs text-muted-foreground">點擊「建立受眾」選擇來源分群，建立後再按「立即同步」將名單上傳至 LinkedIn Campaign Manager</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">名稱</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">比對方式</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">來源</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">上傳筆數</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">最後同步</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {audiences.map(a => {
                  const s = STATUS_MAP[a.status ?? "pending"] ?? STATUS_MAP.pending;
                  return (
                    <tr key={a.id} className="hover:bg-muted/30">
                      <td className="px-4 py-2">
                        <p className="font-medium">{a.name}</p>
                        {a.description && <p className="text-xs text-muted-foreground">{a.description}</p>}
                        {a.status === "error" && a.error_message && (
                          <p className="mt-0.5 flex items-center gap-1 text-xs text-red-600">
                            <AlertCircle className="h-3 w-3 shrink-0" />{a.error_message}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-2 text-muted-foreground">{AUDIENCE_TYPE_LABEL[a.audience_type ?? ""] ?? a.audience_type ?? "—"}</td>
                      <td className="px-4 py-2 text-muted-foreground">{SOURCE_TYPE_LABEL[a.source_type ?? ""] ?? a.source_type ?? "—"}</td>
                      <td className="px-4 py-2 text-center">
                        <Badge className={`text-xs ${s.className}`}>{s.label}</Badge>
                      </td>
                      <td className="px-4 py-2 text-right font-bold">
                        <span className="flex items-center justify-end gap-1">
                          <Users className="h-3 w-3" />{a.last_record_count ?? 0}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-muted-foreground">{fmt(a.last_sync_at)}</td>
                      <td className="px-4 py-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                          disabled={a.status === "syncing" || syncing === a.id}
                          onClick={() => handleSync(a.id)}
                        >
                          <Play className="mr-1 h-3 w-3" />立即同步
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Create dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>建立 LinkedIn 受眾</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>受眾名稱 <span className="text-destructive">*</span></Label>
              <Input
                placeholder="例：熱門意圖訪客 - 2026Q2"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>說明（選填）</Label>
              <Input
                placeholder="簡短描述這個受眾的用途"
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>比對方式</Label>
              <Select value={form.audience_type} onValueChange={v => setForm(f => ({ ...f, audience_type: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="EMAIL">電子郵件（雜湊後上傳）</SelectItem>
                  <SelectItem value="COMPANY">公司名稱</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>名單來源</Label>
              <Select value={form.source_type} onValueChange={v => setForm(f => ({ ...f, source_type: v, source_segment_id: "" }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="segment">依自訂受眾分群篩選</SelectItem>
                  <SelectItem value="contacts_all">全部聯絡人</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.source_type === "segment" && (
              <div className="space-y-1.5">
                <Label>選擇分群</Label>
                <Select value={form.source_segment_id} onValueChange={v => setForm(f => ({ ...f, source_segment_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="請選擇受眾分群" /></SelectTrigger>
                  <SelectContent>
                    {segments.map(seg => (
                      <SelectItem key={seg.id} value={seg.id}>{seg.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
            <Button onClick={handleCreate} disabled={creating || !form.name.trim()}>
              {creating ? "建立中…" : "建立受眾"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
