"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Trash2, PlusCircle, GripVertical } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

type Step = {
  id: string;
  sequence_id: string;
  step_order: number;
  delay_days: number;
  subject: string;
  html_body: string;
  text_body?: string;
  from_name?: string;
  from_email?: string;
};

type Sequence = {
  id: string;
  name: string;
  description?: string;
  trigger_type: string;
  trigger_value: string;
  is_active: boolean;
  is_approved?: boolean;
  allow_re_enrollment: boolean;
  steps?: Step[];
  created_at?: string;
  updated_at?: string;
};

type Enrollment = {
  id: string;
  contact_id: string;
  status: string;
  current_step: number;
  enrolled_at: string;
  last_sent_at?: string;
  completed_at?: string;
};

function fmt(d?: string) {
  return d ? new Date(d).toLocaleDateString("zh-TW") : "—";
}

export default function SequenceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [seq, setSeq] = useState<Sequence | null>(null);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState("intent_stage");
  const [triggerValue, setTriggerValue] = useState("");
  const [isActive, setIsActive] = useState(false);
  const [isApproved, setIsApproved] = useState(false);
  const [approving, setApproving] = useState(false);

  const [newStepSubject, setNewStepSubject] = useState("");
  const [newStepDelay, setNewStepDelay] = useState(1);
  const [newStepBody, setNewStepBody] = useState("");
  const [addingStep, setAddingStep] = useState(false);

  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sRes, eRes] = await Promise.all([
        fetch(`${API_BASE}/nurture/sequences/${id}`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/nurture/enrollments?sequence_id=${id}&limit=20`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (!sRes.ok) throw new Error("序列不存在");
      const sData: Sequence = await sRes.json();
      const eData = await eRes.json();
      setSeq(sData);
      setName(sData.name);
      setDescription(sData.description || "");
      setTriggerType(sData.trigger_type);
      setTriggerValue(sData.trigger_value || "");
      setIsActive(sData.is_active);
      setIsApproved(Boolean(sData.is_approved));
      setEnrollments(Array.isArray(eData) ? eData : eData.items ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id, token]);

  useEffect(() => { if (token) load(); }, [load, token]);

  const saveSequence = async () => {
    setSaving(true); setMessage("");
    try {
      const res = await fetch(`${API_BASE}/nurture/sequences/${id}`, {
        method: "PATCH", headers,
        body: JSON.stringify({ name, description, trigger_type: triggerType, trigger_value: triggerValue, is_active: isActive }),
      });
      if (!res.ok) throw new Error("儲存失敗");
      setMessage("流程設定已儲存");
      await load();
    } catch (e: unknown) {
      setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally { setSaving(false); }
  };

  const addStep = async () => {
    if (!newStepSubject.trim()) return;
    setAddingStep(true);
    try {
      const steps = seq?.steps ?? [];
      const nextOrder = steps.length ? Math.max(...steps.map((s) => s.step_order)) + 1 : 0;
      const res = await fetch(`${API_BASE}/nurture/sequences/${id}/steps`, {
        method: "POST", headers,
        body: JSON.stringify({
          step_order: nextOrder,
          subject: newStepSubject,
          delay_days: newStepDelay,
          html_body: newStepBody || `<p>${newStepSubject}</p>`,
        }),
      });
      if (!res.ok) throw new Error("新增步驟失敗");
      setNewStepSubject(""); setNewStepDelay(1); setNewStepBody("");
      await load();
    } catch (e: unknown) {
      setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally { setAddingStep(false); }
  };

  const deleteStep = async (stepId: string) => {
    try {
      const res = await fetch(`${API_BASE}/nurture/steps/${stepId}`, {
        method: "DELETE", headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("刪除失敗");
      await load();
    } catch (e: unknown) {
      setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const toggleApprove = async () => {
    setApproving(true); setMessage("");
    try {
      const action = isApproved ? "unapprove" : "approve";
      const res = await fetch(`${API_BASE}/nurture/sequences/${id}/${action}`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(isApproved ? "取消核准失敗" : "核准失敗");
      setMessage(isApproved ? "已取消核准，後續不會再寄信" : "已核准，排程將開始寄送");
      await load();
    } catch (e: unknown) {
      setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally { setApproving(false); }
  };

  if (loading) return <p className="py-10 text-center text-muted-foreground">載入中…</p>;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!seq) return null;

  const steps = seq.steps || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{seq.name}</h1>
          <p className="text-sm text-muted-foreground">建立於 {fmt(seq.created_at)}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => router.push("/dashboard/nurture")}>← 返回列表</Button>
      </div>

      {message && <Alert><AlertDescription>{message}</AlertDescription></Alert>}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader><CardTitle className="text-base">流程設定</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label className="text-xs">名稱</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">說明</Label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">觸發類型</Label>
              <select className={SELECT_CLS} value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
                <option value="intent_stage">買家關注程度</option>
                <option value="segment">買家分群</option>
                <option value="manual">手動</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">觸發值</Label>
              <Input value={triggerValue} onChange={(e) => setTriggerValue(e.target.value)} placeholder="warm / hot / sales_ready" />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              啟用
            </label>
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              {isApproved ? "已核准：排程到點會寄出此序列的郵件。" : "尚未核准：即使啟用，核准前不會寄出任何郵件。"}
            </div>
            <div className="flex gap-2">
              <Button size="sm" className="flex-1" disabled={saving} onClick={saveSequence}>
                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}儲存設定
              </Button>
              <Button
                size="sm"
                variant={isApproved ? "outline" : "default"}
                className="flex-1"
                disabled={approving}
                onClick={toggleApprove}
              >
                {approving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isApproved ? "取消核准" : "核准寄信"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">郵件步驟（{steps.length}）</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {steps.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">尚未建立步驟</p>
            ) : (
              <div className="space-y-3">
                {[...steps].sort((a, b) => a.step_order - b.step_order).map((step, idx) => (
                  <div key={step.id} className="flex items-start gap-3 rounded-lg border p-3">
                    <GripVertical className="mt-1 h-4 w-4 text-muted-foreground/50 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">Step {idx + 1}</Badge>
                        <Badge variant="outline" className="text-xs">+{step.delay_days} 天</Badge>
                      </div>
                      <p className="mt-1 text-sm font-medium truncate">{step.subject}</p>
                    </div>
                    <Button variant="ghost" size="sm" className="text-destructive shrink-0" onClick={() => deleteStep(step.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            <div className="rounded-lg border border-dashed p-4 space-y-3">
              <p className="text-sm font-medium">新增步驟</p>
              <div className="grid grid-cols-4 gap-3">
                <div className="col-span-3 space-y-1">
                  <Label className="text-xs">主旨</Label>
                  <Input value={newStepSubject} onChange={(e) => setNewStepSubject(e.target.value)} placeholder="郵件主旨" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">延遲天數</Label>
                  <Input type="number" value={newStepDelay} onChange={(e) => setNewStepDelay(Number(e.target.value))} min={0} />
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">內容（HTML）</Label>
                <textarea
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none font-mono"
                  rows={3}
                  value={newStepBody}
                  onChange={(e) => setNewStepBody(e.target.value)}
                  placeholder="<p>您好，這是一封跟進郵件</p>"
                />
              </div>
              <Button size="sm" disabled={addingStep || !newStepSubject.trim()} onClick={addStep}>
                {addingStep && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                <PlusCircle className="mr-2 h-4 w-4" />新增步驟
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">加入紀錄（{enrollments.length}）</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {enrollments.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">此流程尚無買家加入</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">聯絡人 ID</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">目前步驟</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">加入時間</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">最後寄送</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {enrollments.map((e) => (
                  <tr key={e.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-mono text-xs">{e.contact_id.slice(0, 8)}</td>
                    <td className="px-4 py-2 text-center">
                      <Badge variant="outline" className="text-xs">{e.status}</Badge>
                    </td>
                    <td className="px-4 py-2 text-center">{e.current_step + 1}</td>
                    <td className="px-4 py-2 text-muted-foreground">{fmt(e.enrolled_at)}</td>
                    <td className="px-4 py-2 text-muted-foreground">{fmt(e.last_sent_at)}</td>
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
