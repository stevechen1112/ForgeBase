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
            <CardTitle>營運設定（RFQ 自動回覆 / SLA）</CardTitle>
            <CardDescription>
              控制新 RFQ 進來時的自動確認信與首次回應 SLA；高品質 RFQ（≥70 分）即時推播為系統固定門檻。
              LINE 推播金鑰為環境變數（LINE_CHANNEL_ACCESS_TOKEN），不在此設定。
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
              新 RFQ 會依買家時區的營業時間計算回應期限，逾期自動標記 breached 並進入「今日必處理」。
            </p>
          </div>
          <div className="space-y-2">
            <Label>RFQ 自動專業回覆</Label>
            <label className="flex items-center gap-2.5 rounded-md border bg-muted/30 px-3 py-2.5 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={autoReplyEnabled}
                onChange={(e) => setAutoReplyEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
              />
              <span>收到 RFQ 後自動寄出專業確認信給買家</span>
            </label>
            <p className="text-xs text-muted-foreground">
              內容依 RFQ 欄位（產品、數量、時程）組成，以買家時區的用語回覆；可隨時關閉。
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
