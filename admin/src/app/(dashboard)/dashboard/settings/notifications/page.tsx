"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArchiveX, Bell, BellOff, CheckCircle2, Loader2, Trash2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";
import { useCapabilities } from "@/lib/hooks/useCapabilities";

type NotificationPref = {
  id: string;
  channel: string;
  channel_config: Record<string, string>;
  enabled: boolean;
  notify_new_rfq: boolean;
  notify_daily_summary: boolean;
  notify_chat_handoff: boolean;
  notify_content_suggestion: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  retirement_disabled_at: string | null;
  created_at: string;
};

const ACTIVE_CHANNELS = new Set(["email", "in_app"]);
const RETIRED_CHANNELS = new Set(["telegram", "line"]);
const TOGGLE_LABELS: {
  key: keyof NotificationPref;
  label: string;
  desc: string;
  requiredFeature?: string;
}[] = [
  { key: "notify_new_rfq", label: "新 RFQ 通知", desc: "有新詢價時立即留下營運通知" },
  { key: "notify_daily_summary", label: "每日營運摘要", desc: "每日彙整前一天的重要事件" },
  { key: "notify_chat_handoff", label: "對話轉業務接手", desc: "官網 AI 對話轉交真人時通知", requiredFeature: "chat_handoff" },
  { key: "notify_content_suggestion", label: "內容優化建議", desc: "保留低頻內容品質提醒", requiredFeature: "full_tracking" },
];

export default function NotificationSettingsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const { hasFeature, isLoading: featuresLoading } = useCapabilities();
  const [prefs, setPrefs] = useState<NotificationPref[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const activePrefs = useMemo(
    () => prefs.filter((pref) => ACTIVE_CHANNELS.has(pref.channel)),
    [prefs],
  );
  const retiredPrefCount = useMemo(
    () => prefs.filter((pref) => RETIRED_CHANNELS.has(pref.channel)).length,
    [prefs],
  );
  const visibleToggleLabels = TOGGLE_LABELS.filter(
    (item) => !item.requiredFeature || (!featuresLoading && hasFeature(item.requiredFeature)),
  );

  const loadPrefs = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/notifications/preferences`, {
        headers: buildApiHeaders(token),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "無法載入通知設定");
      setPrefs(payload.data || []);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "無法載入通知設定");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadPrefs(); }, [loadPrefs]);

  const updatePref = async (id: string, field: string, value: boolean | string) => {
    setError(null);
    const response = await fetch(`${API_BASE}/notifications/preferences/${id}`, {
      method: "PUT",
      headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify({ [field]: value }),
    });
    if (!response.ok) {
      const payload = await response.json();
      setError(payload.detail || "通知設定更新失敗");
      return;
    }
    setPrefs((current) => current.map((pref) => (
      pref.id === id ? { ...pref, [field]: value } : pref
    )));
  };

  const deletePref = async (id: string) => {
    if (!confirm("確定要移除此通知設定？")) return;
    const response = await fetch(`${API_BASE}/notifications/preferences/${id}`, {
      method: "DELETE",
      headers: buildApiHeaders(token),
    });
    if (!response.ok) {
      setError("通知設定移除失敗");
      return;
    }
    setPrefs((current) => current.filter((pref) => pref.id !== id));
    setSuccess("已移除通知設定");
  };

  return (
    <div className="max-w-3xl space-y-8">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">營運通知設定</h1>
        <p className="mt-1 text-muted-foreground">
          通知事件、歷史與站內營運流程持續保留；外部渠道依正式退場政策管理。
        </p>
      </header>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {success && <Alert><CheckCircle2 className="h-4 w-4" /><AlertDescription>{success}</AlertDescription></Alert>}

      <section className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/50 p-6 dark:border-amber-900 dark:bg-amber-950/20">
        <div className="flex items-center gap-2">
          <ArchiveX className="h-5 w-5 text-amber-700 dark:text-amber-300" />
          <h2 className="font-semibold">LINE／Telegram 已停止新綁定</h2>
        </div>
        <p className="text-sm leading-6 text-muted-foreground">
          這兩個未使用的外部渠道已進入 60 天退場觀察。期間不再發送或接受新設定；既有停用設定與歷史記錄保留，供稽核與必要時回復。通知核心沒有移除。
        </p>
        {retiredPrefCount > 0 && <p className="text-xs text-muted-foreground">目前保留 {retiredPrefCount} 筆已停用渠道設定作為稽核證據。</p>}
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold">受管理的通知管道</h2>
          <p className="mt-1 text-sm text-muted-foreground">站內與 Email 管道依系統部署設定顯示；事件開關不影響退場中的外部渠道。</p>
        </div>
        {loading ? (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />載入中…</div>
        ) : activePrefs.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
            目前沒有需由租戶手動維護的管道；系統事件與通知歷史仍正常運作。
          </div>
        ) : activePrefs.map((pref) => (
          <div key={pref.id} className="space-y-4 rounded-lg border p-5">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium">{pref.channel === "in_app" ? "站內通知" : "Email"}</span>
                <span className={pref.enabled ? "flex items-center gap-1 text-xs text-green-600" : "flex items-center gap-1 text-xs text-muted-foreground"}>
                  {pref.enabled ? <Bell className="h-3 w-3" /> : <BellOff className="h-3 w-3" />}
                  {pref.enabled ? "啟用" : "停用"}
                </span>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => void updatePref(pref.id, "enabled", !pref.enabled)}>{pref.enabled ? "停用" : "啟用"}</Button>
                <Button variant="ghost" size="sm" aria-label="移除通知設定" onClick={() => void deletePref(pref.id)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {visibleToggleLabels.map(({ key, label, desc }) => (
                <label key={key} className="flex cursor-pointer items-start gap-3 rounded-md p-2 hover:bg-muted/50">
                  <input type="checkbox" className="mt-0.5" checked={Boolean(pref[key])} onChange={(event) => void updatePref(pref.id, key, event.target.checked)} />
                  <span><span className="block text-sm font-medium">{label}</span><span className="block text-xs text-muted-foreground">{desc}</span></span>
                </label>
              ))}
            </div>

            <div className="flex items-center gap-3 border-t pt-3">
              <span className="text-xs text-muted-foreground">靜音時段：</span>
              <input type="time" className="rounded border border-input bg-background px-2 py-1 text-xs" value={pref.quiet_hours_start || ""} onChange={(event) => void updatePref(pref.id, "quiet_hours_start", event.target.value)} />
              <span className="text-xs text-muted-foreground">至</span>
              <input type="time" className="rounded border border-input bg-background px-2 py-1 text-xs" value={pref.quiet_hours_end || ""} onChange={(event) => void updatePref(pref.id, "quiet_hours_end", event.target.value)} />
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
