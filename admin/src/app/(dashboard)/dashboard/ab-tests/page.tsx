"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { RefreshCw, FlaskConical, PlusCircle, Power, Trash2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Matches the actual ABTest SQLModel returned by GET /ab-tests/
type ABTest = {
  id: string;
  name: string;
  description?: string;
  page_id?: string;
  test_element: string;   // "cta" | "headline" | "block" | "custom"
  variant_a: string;
  variant_b: string;
  split_ratio: number;
  is_active: boolean;     // true = 進行中, false = 已停用
  views_a: number;
  views_b: number;
  conversions_a: number;
  conversions_b: number;
  created_at: string;
  updated_at: string;
};

const ELEMENT_LABEL: Record<string, string> = {
  cta: "CTA 按鈕",
  headline: "標題文字",
  block: "區塊內容",
  custom: "自訂",
};

function ctr(conversions: number, views: number): string {
  if (!views) return "—";
  return `${(conversions / views * 100).toFixed(1)}%`;
}

function fmt(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("zh-TW");
}

/* ── Create Dialog ─────────────────────────────────────── */
function CreateDialog({ token, onCreated }: { token: string; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    test_element: "cta",
    variant_a: "",
    variant_b: "",
    split_ratio: "0.5",
  });

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  async function handleSave() {
    if (!form.name.trim() || !form.variant_a.trim() || !form.variant_b.trim()) {
      setError("測試名稱、變形 A 與變形 B 為必填");
      return;
    }
    setSaving(true); setError(null);
    try {
      const r = await fetch(`${API_BASE}/ab-tests/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          test_element: form.test_element,
          variant_a: form.variant_a.trim(),
          variant_b: form.variant_b.trim(),
          split_ratio: parseFloat(form.split_ratio),
        }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText);
      setOpen(false);
      setForm({ name: "", description: "", test_element: "cta", variant_a: "", variant_b: "", split_ratio: "0.5" });
      onCreated();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "建立失敗");
    } finally { setSaving(false); }
  }

  const splitPct = Math.round(parseFloat(form.split_ratio) * 100);

  return (
    <Dialog open={open} onOpenChange={v => { setOpen(v); if (!v) setError(null); }}>
      <DialogTrigger asChild>
        <Button size="sm"><PlusCircle className="mr-2 h-4 w-4" />新增測試</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>新增 A/B 測試</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

          <div className="space-y-1">
            <Label>測試名稱 *</Label>
            <Input
              placeholder="e.g. Homepage CTA 測試 #1"
              value={form.name}
              onChange={e => set("name", e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <Label>描述</Label>
            <Input
              placeholder="可選"
              value={form.description}
              onChange={e => set("description", e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <Label>測試元素</Label>
            <Select value={form.test_element} onValueChange={v => set("test_element", v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="cta">CTA 按鈕</SelectItem>
                <SelectItem value="headline">標題文字</SelectItem>
                <SelectItem value="block">區塊內容</SelectItem>
                <SelectItem value="custom">自訂</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>變形 A（控制組）*</Label>
              <Textarea
                rows={3}
                placeholder="現有版本文字"
                value={form.variant_a}
                onChange={e => set("variant_a", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>變形 B（挑戰組）*</Label>
              <Textarea
                rows={3}
                placeholder="新版本文字"
                value={form.variant_b}
                onChange={e => set("variant_b", e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>分流比例（A 組 {100 - splitPct}%，B 組 {splitPct}%）</Label>
            <input
              type="range" min="0.1" max="0.9" step="0.05"
              value={form.split_ratio}
              onChange={e => set("split_ratio", e.target.value)}
              className="w-full accent-primary"
            />
            <p className="text-xs text-muted-foreground">預設 50/50，往右增加 B 組流量</p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? "建立中…" : "建立測試"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ── Main Page ─────────────────────────────────────────── */
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

  async function toggleActive(t: ABTest) {
    await fetch(`${API_BASE}/ab-tests/${t.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ is_active: !t.is_active }),
    });
    load();
  }

  async function deleteTest(t: ABTest) {
    if (!confirm(`確定要刪除「${t.name}」？此操作無法復原。`)) return;
    await fetch(`${API_BASE}/ab-tests/${t.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    load();
  }

  const activeCount = tests.filter(t => t.is_active).length;
  const inactiveCount = tests.length - activeCount;
  const totalViews = tests.reduce((s, t) => s + (t.views_a ?? 0) + (t.views_b ?? 0), 0);
  const totalConversions = tests.reduce((s, t) => s + (t.conversions_a ?? 0) + (t.conversions_b ?? 0), 0);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">A/B 測試</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            測試頁面標題、CTA 文字、區塊內容對轉換率的影響
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <CreateDialog token={token} onCreated={load} />
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Summary Cards — always visible */}
      <div className="mb-6 grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pb-4 pt-4">
            <p className="text-sm text-muted-foreground">進行中</p>
            <p className="mt-1 text-3xl font-bold">{activeCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pb-4 pt-4">
            <p className="text-sm text-muted-foreground">已停用</p>
            <p className="mt-1 text-3xl font-bold">{inactiveCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pb-4 pt-4">
            <p className="text-sm text-muted-foreground">總曝光次數</p>
            <p className="mt-1 text-3xl font-bold">{totalViews.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pb-4 pt-4">
            <p className="text-sm text-muted-foreground">總轉換次數</p>
            <p className="mt-1 text-3xl font-bold">{totalConversions.toLocaleString()}</p>
          </CardContent>
        </Card>
      </div>

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
              <p className="mt-1 text-xs text-muted-foreground">
                建立測試實驗，比較兩種變形對轉換率的影響
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">測試名稱</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">測試元素</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">曝光 A / B</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">CTR A</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">CTR B</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">建立時間</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tests.map(t => (
                  <tr key={t.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2">
                      <p className="font-medium">{t.name}</p>
                      {t.description && (
                        <p className="text-xs text-muted-foreground">{t.description}</p>
                      )}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {ELEMENT_LABEL[t.test_element] ?? t.test_element}
                    </td>
                    <td className="px-4 py-2 text-center">
                      <Badge className={
                        t.is_active
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-600"
                      }>
                        {t.is_active ? "進行中" : "已停用"}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-center font-mono text-xs">
                      {(t.views_a ?? 0).toLocaleString()} / {(t.views_b ?? 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {ctr(t.conversions_a ?? 0, t.views_a ?? 0)}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {ctr(t.conversions_b ?? 0, t.views_b ?? 0)}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{fmt(t.created_at)}</td>
                    <td className="px-4 py-2 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          className="rounded p-1 hover:bg-muted"
                          title={t.is_active ? "停用測試" : "啟用測試"}
                          onClick={() => toggleActive(t)}
                        >
                          <Power className={`h-4 w-4 ${t.is_active ? "text-green-600" : "text-muted-foreground"}`} />
                        </button>
                        <button
                          className="rounded p-1 hover:bg-muted"
                          title="刪除測試"
                          onClick={() => deleteTest(t)}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </button>
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
  );
}
