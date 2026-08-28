"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

export default function NewSequencePage() {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    name: "",
    description: "",
    trigger_type: "intent_stage",
    trigger_value: "warm",
    is_active: false,
    allow_re_enrollment: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/nurture/sequences`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      router.push(`/dashboard/nurture/${data.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "建立失敗");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <h1 className="text-2xl font-bold">新增跟進郵件流程</h1>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader><CardTitle className="text-base">流程設定</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>序列名稱 *</Label>
              <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required maxLength={200} placeholder="例如：有興趣買家跟進" />
            </div>
            <div className="space-y-1.5">
              <Label>說明</Label>
              <Input value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} maxLength={500} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>觸發類型</Label>
                <select className={SELECT_CLS} value={form.trigger_type} onChange={(e) => setForm((f) => ({ ...f, trigger_type: e.target.value }))}>
                  <option value="intent_stage">買家關注程度</option>
                  <option value="segment">買家分群</option>
                  <option value="manual">手動</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label>觸發值</Label>
                <Input value={form.trigger_value} onChange={(e) => setForm((f) => ({ ...f, trigger_value: e.target.value }))} placeholder="例如：warm / hot" />
              </div>
            </div>
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
                啟用
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.allow_re_enrollment} onChange={(e) => setForm((f) => ({ ...f, allow_re_enrollment: e.target.checked }))} />
                允許重複加入
              </label>
            </div>
          </CardContent>
        </Card>
        <div className="flex gap-3 pt-4">
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {saving ? "建立中…" : "建立序列"}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.push("/dashboard/nurture")}>取消</Button>
        </div>
      </form>
    </div>
  );
}
