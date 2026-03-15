"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Loader2, PlusCircle, Trash2, Users } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

type Condition = {
  field: string;
  operator: string;
  value: string;
  // For event_count
  event_name?: string;
  within_days?: number;
};

const FIELD_OPTIONS = [
  { value: "intent_stage", label: "意圖階段" },
  { value: "intent_score", label: "意圖分數" },
  { value: "country", label: "國家" },
  { value: "event_count", label: "事件次數" },
];

const OPERATOR_MAP: Record<string, { value: string; label: string }[]> = {
  intent_stage: [{ value: "eq", label: "等於" }],
  intent_score: [
    { value: "gte", label: "≥" },
    { value: "lte", label: "≤" },
    { value: "eq", label: "=" },
  ],
  country: [{ value: "eq", label: "等於" }],
  event_count: [{ value: "gte", label: "≥" }],
};

function emptyCondition(): Condition {
  return { field: "intent_stage", operator: "eq", value: "" };
}

export default function NewSegmentPage() {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [combinator, setCombinator] = useState("AND");
  const [conditions, setConditions] = useState<Condition[]>([emptyCondition()]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preview
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [previewing, setPreviewing] = useState(false);

  const updateCondition = (idx: number, patch: Partial<Condition>) => {
    setConditions((prev) =>
      prev.map((c, i) => {
        if (i !== idx) return c;
        const updated = { ...c, ...patch };
        // Reset operator when field changes
        if (patch.field && patch.field !== c.field) {
          updated.operator = OPERATOR_MAP[patch.field]?.[0]?.value ?? "eq";
          updated.value = "";
        }
        return updated;
      })
    );
  };

  const removeCondition = (idx: number) => {
    setConditions((prev) => prev.filter((_, i) => i !== idx));
  };

  const buildConditionsPayload = () =>
    conditions.map((c) => {
      const base: Record<string, unknown> = { field: c.field, operator: c.operator, value: c.value };
      if (c.field === "intent_score") base.value = Number(c.value);
      if (c.field === "event_count") {
        base.event_name = c.event_name || "page_view";
        base.within_days = c.within_days || 30;
        base.value = Number(c.value);
      }
      return base;
    });

  const handlePreview = async () => {
    setPreviewing(true);
    setPreviewCount(null);
    try {
      // Create temp segment, evaluate, then delete — or just call evaluate with inline rules
      // The evaluate endpoint requires a saved segment. So we'll create, evaluate, then show count.
      // Alternative: just submit and show count on the detail page.
      // For now, create the segment first
      const res = await fetch(`${API_BASE}/tracking/segments`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: name || "Preview (temp)",
          description,
          conditions: JSON.stringify(buildConditionsPayload()),
          combinator,
        }),
      });
      if (!res.ok) throw new Error("建立預覽失敗");
      const seg = await res.json();

      // Evaluate
      const evalRes = await fetch(`${API_BASE}/tracking/segments/${seg.id}/evaluate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (evalRes.ok) {
        const evalData = await evalRes.json();
        setPreviewCount(evalData.matched_count ?? evalData.count ?? 0);
      }

      // Delete temp segment
      await fetch(`${API_BASE}/tracking/segments/${seg.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setPreviewCount(-1);
    } finally { setPreviewing(false); }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/tracking/segments`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name,
          description,
          conditions: JSON.stringify(buildConditionsPayload()),
          combinator,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      router.push("/dashboard/segments");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "建立失敗");
    } finally { setSaving(false); }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <h1 className="text-2xl font-bold">新增受眾分群</h1>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <form onSubmit={handleSubmit} className="space-y-5">
        <Card>
          <CardHeader><CardTitle className="text-base">基本資料</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label>分群名稱 *</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} placeholder="例：高意圖台灣訪客" />
            </div>
            <div className="space-y-1.5">
              <Label>說明</Label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} maxLength={300} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">條件規則</CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">條件組合：</span>
                <select className="rounded border px-2 py-1 text-xs" value={combinator} onChange={(e) => setCombinator(e.target.value)}>
                  <option value="AND">AND (全部符合)</option>
                  <option value="OR">OR (任一符合)</option>
                </select>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {conditions.map((cond, idx) => (
              <div key={idx} className="flex items-end gap-2 rounded-lg border p-3">
                {idx > 0 && (
                  <Badge variant="secondary" className="mb-1 text-xs shrink-0">{combinator}</Badge>
                )}
                <div className="flex-1 grid grid-cols-3 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">欄位</Label>
                    <select className={SELECT_CLS} value={cond.field} onChange={(e) => updateCondition(idx, { field: e.target.value })}>
                      {FIELD_OPTIONS.map((f) => (
                        <option key={f.value} value={f.value}>{f.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">運算</Label>
                    <select className={SELECT_CLS} value={cond.operator} onChange={(e) => updateCondition(idx, { operator: e.target.value })}>
                      {(OPERATOR_MAP[cond.field] || []).map((op) => (
                        <option key={op.value} value={op.value}>{op.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">值</Label>
                    {cond.field === "intent_stage" ? (
                      <select className={SELECT_CLS} value={cond.value} onChange={(e) => updateCondition(idx, { value: e.target.value })}>
                        <option value="">請選擇</option>
                        <option value="cold">Cold</option>
                        <option value="warm">Warm</option>
                        <option value="hot">Hot</option>
                        <option value="sales_ready">Sales Ready</option>
                      </select>
                    ) : (
                      <Input value={cond.value} onChange={(e) => updateCondition(idx, { value: e.target.value })} placeholder={cond.field === "intent_score" ? "例：50" : "值"} />
                    )}
                  </div>
                </div>
                {cond.field === "event_count" && (
                  <div className="grid grid-cols-2 gap-2 flex-1">
                    <div className="space-y-1">
                      <Label className="text-xs">事件名稱</Label>
                      <Input value={cond.event_name || ""} onChange={(e) => updateCondition(idx, { event_name: e.target.value })} placeholder="page_view" />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">天數內</Label>
                      <Input type="number" value={cond.within_days || 30} onChange={(e) => updateCondition(idx, { within_days: Number(e.target.value) })} min={1} />
                    </div>
                  </div>
                )}
                <Button type="button" variant="ghost" size="sm" className="text-destructive shrink-0" onClick={() => removeCondition(idx)} disabled={conditions.length <= 1}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={() => setConditions((p) => [...p, emptyCondition()])}>
              <PlusCircle className="mr-2 h-4 w-4" />新增條件
            </Button>
          </CardContent>
        </Card>

        {/* Preview */}
        <div className="flex items-center gap-4">
          <Button type="button" variant="outline" size="sm" onClick={handlePreview} disabled={previewing}>
            {previewing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Users className="mr-2 h-4 w-4" />}
            預覽符合人數
          </Button>
          {previewCount !== null && previewCount >= 0 && (
            <span className="text-sm font-medium">符合 <strong>{previewCount}</strong> 位訪客</span>
          )}
          {previewCount === -1 && (
            <span className="text-sm text-destructive">預覽失敗</span>
          )}
        </div>

        <div className="flex gap-3">
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {saving ? "儲存中…" : "建立分群"}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>取消</Button>
        </div>
      </form>
    </div>
  );
}
