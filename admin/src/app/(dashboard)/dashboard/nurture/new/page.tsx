"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

const INTENT_STAGES = [
  { value: "cold",        label: "冷 (Cold) — 首次接觸" },
  { value: "warm",        label: "暖 (Warm) — 有興趣" },
  { value: "hot",         label: "熱 (Hot) — 高意圖" },
  { value: "sales_ready", label: "Sale Ready — 可接觸" },
];

type SegmentOption = { id: string; name: string };

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
  const [segments, setSegments] = useState<SegmentOption[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 當觸發類型為 segment 時，載入受眾清單
  useEffect(() => {
    if (form.trigger_type !== "segment" || !token) return;
    fetch(`${API_BASE}/tracking/segments`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => {
        const list: SegmentOption[] = (Array.isArray(d) ? d : d.items ?? []).map((s: { id: string; name: string }) => ({ id: s.id, name: s.name }));
        setSegments(list);
        if (list.length > 0) setForm(f => ({ ...f, trigger_value: list[0].id }));
      })
      .catch(() => {});
  }, [form.trigger_type, token]);

  // 切換觸發類型時重設觸發值
  const handleTriggerTypeChange = (type: string) => {
    const defaultValue = type === "intent_stage" ? "warm" : type === "manual" ? "" : "";
    setForm(f => ({ ...f, trigger_type: type, trigger_value: defaultValue }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/nurture/sequences`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
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

  // 根據觸發類型渲染對應的觸發值欄位
  function TriggerValueField() {
    if (form.trigger_type === "manual") return null;

    if (form.trigger_type === "intent_stage") {
      return (
        <div className="space-y-1.5">
          <Label>觸發條件</Label>
          <select
            className={SELECT_CLS}
            value={form.trigger_value}
            onChange={(e) => setForm(f => ({ ...f, trigger_value: e.target.value }))}
          >
            {INTENT_STAGES.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      );
    }

    if (form.trigger_type === "segment") {
      return (
        <div className="space-y-1.5">
          <Label>觸發受眾</Label>
          {segments.length === 0 ? (
            <p className="text-sm text-muted-foreground pt-2">尚無自訂受眾，請先至「自訂受眾」建立。</p>
          ) : (
            <select
              className={SELECT_CLS}
              value={form.trigger_value}
              onChange={(e) => setForm(f => ({ ...f, trigger_value: e.target.value }))}
            >
              {segments.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          )}
        </div>
      );
    }

    // download_gate
    return (
      <div className="space-y-1.5">
        <Label>Gate 識別碼</Label>
        <Input
          value={form.trigger_value}
          onChange={(e) => setForm(f => ({ ...f, trigger_value: e.target.value }))}
          placeholder="例：spec-download-gate"
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <h1 className="text-2xl font-bold tracking-tight">新增 Nurture 序列</h1>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader><CardTitle className="text-base">序列設定</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>序列名稱 *</Label>
              <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required maxLength={200} placeholder="例：Warm 階段培育信" />
            </div>
            <div className="space-y-1.5">
              <Label>描述</Label>
              <Input value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} maxLength={500} placeholder="這個序列的用途說明" />
            </div>
            <div className="space-y-1.5">
              <Label>觸發類型</Label>
              <select className={SELECT_CLS} value={form.trigger_type} onChange={(e) => handleTriggerTypeChange(e.target.value)}>
                <option value="intent_stage">意圖階段 — 訪客達到某個熱度時觸發</option>
                <option value="segment">自訂受眾 — 符合指定受眾條件時觸發</option>
                <option value="download_gate">下載 Gate — 下載規格書後觸發</option>
                <option value="manual">手動 — 由業務人員手動加入</option>
              </select>
            </div>
            <TriggerValueField />
            <div className="flex items-center gap-6 pt-1">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
                建立後立即啟用
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.allow_re_enrollment} onChange={(e) => setForm((f) => ({ ...f, allow_re_enrollment: e.target.checked }))} />
                允許重複入列
              </label>
            </div>
          </CardContent>
        </Card>
        <div className="flex gap-3 pt-4">
          <Button type="submit" disabled={saving || (form.trigger_type === "segment" && segments.length === 0)}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {saving ? "儲存中…" : "建立序列"}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>取消</Button>
        </div>
      </form>
    </div>
  );
}
