"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Save } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type OpsConfig = {
  auto_reply_enabled?: boolean;
  auto_reply_signature?: string;
  auto_reply_from_name?: string;
  sla_response_hours?: number;
};

export function OpsConfigCard() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [autoReplyEnabled, setAutoReplyEnabled] = useState(false);
  const [signature, setSignature] = useState("");
  const [fromName, setFromName] = useState("");
  const [slaHours, setSlaHours] = useState("4");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/site-profile/ops-config`, {
        headers: buildApiHeaders(token),
      });
      if (!res.ok) throw new Error(`載入失敗 (${res.status})`);
      const data = (await res.json()) as OpsConfig;
      setAutoReplyEnabled(data.auto_reply_enabled === true);
      setSignature(data.auto_reply_signature ?? "");
      setFromName(data.auto_reply_from_name ?? "");
      setSlaHours(data.sla_response_hours != null ? String(data.sla_response_hours) : "4");
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入營運設定失敗");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave() {
    const hours = Number(slaHours);
    if (!Number.isFinite(hours) || hours <= 0 || hours > 168) {
      setError("SLA 目標時數必須介於 0 到 168 之間。");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await fetch(`${API_BASE}/site-profile/ops-config`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({
          auto_reply_enabled: autoReplyEnabled,
          auto_reply_signature: signature || null,
          auto_reply_from_name: fromName || null,
          sla_response_hours: hours,
        }),
      });
      if (!res.ok) throw new Error(`儲存失敗 (${res.status})`);
      setSuccess("營運設定已更新，立即生效於新進 RFQ。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "儲存營運設定失敗");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>詢價回覆與時限</CardTitle>
            <CardDescription>
              設定收到詢價後是否寄出固定格式的收件確認信，以及希望業務在多久內第一次回覆。
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || saving}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
            </Button>
            <Button size="sm" onClick={() => void handleSave()} disabled={loading || saving || !token}>
              <Save className={`mr-2 h-4 w-4 ${saving ? "animate-pulse" : ""}`} />儲存營運設定
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {success ? (
          <Alert>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="sla_response_hours">首次回應 SLA（營業小時）</Label>
            <Input
              id="sla_response_hours"
              type="number"
              min={1}
              max={168}
              step={1}
              value={slaHours}
              onChange={(e) => setSlaHours(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              新詢價會依買家時區的營業時間計算回覆期限，逾期自動標示並進入「今日待辦」。
            </p>
          </div>
          <div className="space-y-2">
            <Label>自動寄送收件確認信</Label>
            <label className="flex items-center gap-2.5 rounded-md border bg-muted/30 px-3 py-2.5 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={autoReplyEnabled}
                onChange={(e) => setAutoReplyEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
              />
              <span>收到詢價後，立即通知買家「我們已收到」</span>
            </label>
            <p className="text-xs text-muted-foreground">
              這只是確認收件，不會代替業務報價或答應交期；可隨時關閉。
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="auto_reply_signature">確認信署名</Label>
            <Input
              id="auto_reply_signature"
              value={signature}
              onChange={(e) => setSignature(e.target.value)}
              placeholder="Sales Team"
              disabled={!autoReplyEnabled}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="auto_reply_from_name">寄件者顯示名稱</Label>
            <Input
              id="auto_reply_from_name"
              value={fromName}
              onChange={(e) => setFromName(e.target.value)}
              placeholder="沿用系統預設"
              disabled={!autoReplyEnabled}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
