"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Bell, BellOff, CheckCircle2, Loader2, Send, Trash2 } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

type NotificationPref = {
  id: string;
  channel: string;
  channel_config: Record<string, string>;
  enabled: boolean;
  notify_new_rfq: boolean;
  notify_hot_visitor: boolean;
  notify_daily_summary: boolean;
  notify_churn_risk: boolean;
  notify_chat_handoff: boolean;
  notify_content_suggestion: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  created_at: string;
};

const TOGGLE_LABELS: { key: keyof NotificationPref; label: string; desc: string }[] = [
  { key: "notify_new_rfq", label: "新 RFQ 通知", desc: "有新詢價時立即推送，含 AI 摘要" },
  { key: "notify_hot_visitor", label: "高意圖訪客警報", desc: "訪客進入 hot 或 sales_ready 時通知" },
  { key: "notify_daily_summary", label: "每日營運摘要", desc: "每日 08:00 推送前一天數據摘要" },
  { key: "notify_churn_risk", label: "客戶流失預警", desc: "已識別客戶 intent score 下降時通知" },
  { key: "notify_chat_handoff", label: "Chat 人工接手", desc: "AI 聊天機器人轉交人工時通知" },
  { key: "notify_content_suggestion", label: "內容優化建議", desc: "AI 偵測到頁面需優化時推薦（低頻）" },
];

export default function NotificationSettingsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [prefs, setPrefs] = useState<NotificationPref[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Telegram bind form
  const [tgChatId, setTgChatId] = useState("");
  const [tgCode, setTgCode] = useState("");
  const [bindStep, setBindStep] = useState<"idle" | "sent" | "done">("idle");
  const [bindLoading, setBindLoading] = useState(false);

  const loadPrefs = useCallback(() => {
    setLoading(true);
    fetch(`${API_BASE}/copilot/preferences`, {
      headers: buildApiHeaders(token),
    })
      .then((r) => r.json())
      .then((d) => { setPrefs(d.data || []); })
      .catch(() => setError("無法載入通知設定"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { loadPrefs(); }, [loadPrefs]);

  const togglePref = async (id: string, field: string, value: boolean) => {
    await fetch(`${API_BASE}/copilot/preferences/${id}`, {
      method: "PUT",
      headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify({ [field]: value }),
    });
    setPrefs((prev) =>
      prev.map((p) => (p.id === id ? { ...p, [field]: value } : p))
    );
  };

  const deletePref = async (id: string) => {
    if (!confirm("確定要移除此通知設定？")) return;
    await fetch(`${API_BASE}/copilot/preferences/${id}`, {
      method: "DELETE",
      headers: buildApiHeaders(token),
    });
    setPrefs((prev) => prev.filter((p) => p.id !== id));
    setSuccess("已移除");
    setTimeout(() => setSuccess(null), 2000);
  };

  const startTelegramBind = async () => {
    if (!tgChatId.trim()) return;
    setBindLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/copilot/telegram/bind-start`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ telegram_chat_id: tgChatId.trim() }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "發送失敗");
      setBindStep("sent");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "未知錯誤";
      setError(msg);
    } finally {
      setBindLoading(false);
    }
  };

  const verifyTelegramBind = async () => {
    if (!tgCode.trim()) return;
    setBindLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/copilot/telegram/bind-verify`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ code: tgCode.trim().toUpperCase() }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "驗證失敗");
      setBindStep("done");
      setSuccess("Telegram 綁定成功！");
      loadPrefs();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "未知錯誤";
      setError(msg);
    } finally {
      setBindLoading(false);
    }
  };

  const telegramPref = prefs.find((p) => p.channel === "telegram" && p.enabled);
  const linePref = prefs.find((p) => p.channel === "line" && p.enabled);

  // LINE bind form
  const [lineUserId, setLineUserId] = useState("");
  const [lineLoading, setLineLoading] = useState(false);

  const bindLine = async () => {
    if (!lineUserId.trim()) return;
    setLineLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/copilot/preferences`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({
          channel: "line",
          channel_config: { line_user_id: lineUserId.trim() },
          enabled: true,
        }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(typeof d.detail === "string" ? d.detail : "綁定失敗");
      setSuccess("LINE 綁定成功！");
      setLineUserId("");
      loadPrefs();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "未知錯誤");
    } finally {
      setLineLoading(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI 行銷專員通知設定</h1>
        <p className="text-muted-foreground mt-1">
          設定 AI 行銷專員的通知管道和事件偏好，讓重要事件主動送到你的口袋。
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {/* Telegram Binding */}
      <section className="rounded-lg border p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Send className="h-5 w-5 text-blue-500" />
          <h2 className="text-base font-semibold">Telegram 通知綁定</h2>
          {telegramPref && (
            <span className="ml-2 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 font-medium">
              已綁定
            </span>
          )}
        </div>

        {telegramPref ? (
          <p className="text-sm text-muted-foreground">
            已成功綁定 Telegram（chat_id: {telegramPref.channel_config?.chat_id}）。
            AI 行銷專員通知將推送到此帳號。
          </p>
        ) : bindStep === "done" ? (
          <p className="text-sm text-green-600">✅ 綁定完成！請重新整理頁面查看狀態。</p>
        ) : bindStep === "sent" ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              驗證碼已發送到你的 Telegram。請輸入收到的 6 位驗證碼：
            </p>
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring tracking-widest uppercase"
                placeholder="例如：AB1C2D"
                value={tgCode}
                onChange={(e) => setTgCode(e.target.value.toUpperCase())}
                maxLength={6}
              />
              <Button onClick={verifyTelegramBind} disabled={bindLoading || tgCode.length < 6}>
                {bindLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "驗證"}
              </Button>
              <Button variant="ghost" onClick={() => setBindStep("idle")}>
                重新輸入
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              輸入你的 Telegram Chat ID。可在 Telegram 搜尋{" "}
              <code className="bg-muted rounded px-1">@userinfobot</code> 取得 ID。
            </p>
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="例如：123456789"
                value={tgChatId}
                onChange={(e) => setTgChatId(e.target.value)}
              />
              <Button onClick={startTelegramBind} disabled={bindLoading || !tgChatId.trim()}>
                {bindLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "發送驗證碼"}
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* LINE Binding */}
      <section className="rounded-lg border p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5 text-green-600" />
          <h2 className="text-base font-semibold">LINE 通知綁定</h2>
          {linePref && (
            <span className="ml-2 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 font-medium">
              已綁定
            </span>
          )}
        </div>
        {linePref ? (
          <p className="text-sm text-muted-foreground">
            已成功綁定 LINE（User ID：{linePref.channel_config?.line_user_id}）。
            高品質 RFQ 與緊急事件通知將推播到此帳號。如需更換，請先移除下方管道設定再重新綁定。
          </p>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              輸入你的 LINE User ID（U 開頭 33 碼）。取得方式：加入官方帳號好友後，於 LINE Developers Console
              的 Messaging API 頁面透過 webhook 或「Your user ID」欄位查詢。
            </p>
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="例如：U1234567890abcdef..."
                value={lineUserId}
                onChange={(e) => setLineUserId(e.target.value)}
              />
              <Button onClick={bindLine} disabled={lineLoading || !lineUserId.trim()}>
                {lineLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "綁定"}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              注意：LINE 推播需由系統管理員在伺服器設定環境變數 LINE_CHANNEL_ACCESS_TOKEN（官方帳號 Channel Access Token），未設定時通知會被略過。
            </p>
          </div>
        )}
      </section>

      {/* Existing preferences & toggles */}
      {prefs.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-base font-semibold">已設定的通知管道</h2>
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          ) : (
            prefs.map((pref) => (
              <div key={pref.id} className="rounded-lg border p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium capitalize">{pref.channel}</span>
                    {pref.enabled ? (
                      <span className="flex items-center gap-1 text-xs text-green-600">
                        <Bell className="h-3 w-3" /> 啟用
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <BellOff className="h-3 w-3" /> 停用
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => togglePref(pref.id, "enabled", !pref.enabled)}
                    >
                      {pref.enabled ? "停用" : "啟用"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deletePref(pref.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {TOGGLE_LABELS.map(({ key, label, desc }) => (
                    <label
                      key={key}
                      className="flex items-start gap-3 cursor-pointer rounded-md p-2 hover:bg-muted/50"
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={!!pref[key]}
                        onChange={(e) =>
                          togglePref(pref.id, key, e.target.checked)
                        }
                      />
                      <div>
                        <div className="text-sm font-medium">{label}</div>
                        <div className="text-xs text-muted-foreground">{desc}</div>
                      </div>
                    </label>
                  ))}
                </div>

                {/* Quiet hours */}
                <div className="flex items-center gap-3 pt-2 border-t">
                  <span className="text-xs text-muted-foreground">靜音時段：</span>
                  <input
                    type="time"
                    className="rounded border border-input bg-background px-2 py-1 text-xs"
                    value={pref.quiet_hours_start || ""}
                    onChange={(e) =>
                      togglePref(
                        pref.id,
                        "quiet_hours_start",
                        e.target.value as unknown as boolean
                      )
                    }
                  />
                  <span className="text-xs text-muted-foreground">至</span>
                  <input
                    type="time"
                    className="rounded border border-input bg-background px-2 py-1 text-xs"
                    value={pref.quiet_hours_end || ""}
                    onChange={(e) =>
                      togglePref(
                        pref.id,
                        "quiet_hours_end",
                        e.target.value as unknown as boolean
                      )
                    }
                  />
                </div>
              </div>
            ))
          )}
        </section>
      )}
    </div>
  );
}
