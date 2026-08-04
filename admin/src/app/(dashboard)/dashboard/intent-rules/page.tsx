"use client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Flame, TrendingUp, Zap, Eye, Target, RefreshCcw,
  MousePointerClick, FileText, ClipboardList, Globe,
  Download, HelpCircle, Scale, Save, RotateCcw, MessageSquare, Award, ShieldCheck,
} from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

const EVENT_META: Record<string, { label: string; icon: React.ElementType; color: string; note: string }> = {
  page_view:             { label: "頁面瀏覽",         icon: Eye,               color: "text-gray-400",    note: "任意頁面瀏覽" },
  category_view:         { label: "分類頁瀏覽",       icon: Globe,             color: "text-indigo-400",  note: "瀏覽商品分類頁" },
  product_view:          { label: "商品頁瀏覽",       icon: Eye,               color: "text-blue-500",    note: "瀏覽單一商品頁" },
  application_view:      { label: "應用場景瀏覽",     icon: Globe,             color: "text-indigo-500",  note: "瀏覽應用場景頁" },
  faq_expand:            { label: "FAQ 展開",          icon: HelpCircle,        color: "text-gray-500",    note: "展開任一 FAQ 問答" },
  comparison_view:       { label: "比較表查看",        icon: Scale,             color: "text-purple-500",  note: "查看競品比較頁" },
  spec_download:         { label: "規格書下載",        icon: Download,          color: "text-green-600",   note: "下載 PDF 規格書" },
  certification_view:    { label: "認證頁瀏覽",        icon: ShieldCheck,       color: "text-teal-500",    note: "瀏覽認證說明頁" },
  cta_click:             { label: "行動按鈕點擊（次要）",  icon: MousePointerClick, color: "text-orange-400",  note: "點擊次要行動按鈕" },
  form_start:            { label: "表單開始填寫",      icon: FileText,          color: "text-yellow-600",  note: "開始填寫非 RFQ 表單" },
  form_submit:           { label: "表單提交",          icon: FileText,          color: "text-yellow-700",  note: "提交非 RFQ 表單" },
  rfq_start:             { label: "RFQ 開始填寫",      icon: ClipboardList,     color: "text-red-400",     note: "開始填寫詢價表單" },
  rfq_submit:            { label: "RFQ 提交",          icon: Flame,             color: "text-red-600",     note: "成功提交詢價" },
  return_visit:          { label: "回訪（24h+）",      icon: RefreshCcw,        color: "text-teal-500",    note: "24 小時後再次到訪" },
  session_depth_reached: { label: "深度瀏覽（≥5頁）", icon: TrendingUp,        color: "text-blue-600",    note: "單次 session 瀏覽 5 頁以上" },
  chat_start:            { label: "AI 對話開始",       icon: MessageSquare,     color: "text-violet-500",  note: "訪客啟動 AI 聊天" },
  chat_rfq_handoff:      { label: "AI 對話轉 RFQ",    icon: Award,             color: "text-violet-700",  note: "AI 聊天中觸發詢價轉接" },
};

const STAGE_NAME: Record<string, string> = {
  cold: "初次瀏覽",
  warm: "多次互動",
  hot: "高度關注",
  sales_ready: "可成交",
};

const STAGE_META: Record<string, { color: string; desc: string; action: string }> = {
  cold:        { color: "bg-gray-100 text-gray-700",     desc: "尚未顯示明確購買意向",   action: "持續曝光，不主動跟進" },
  warm:        { color: "bg-yellow-100 text-yellow-800", desc: "有瀏覽行為，輕度關注", action: "可加入跟進名單或發送跟進郵件" },
  hot:         { color: "bg-orange-100 text-orange-800", desc: "高頻瀏覽，高度關注", action: "發出業務提醒，建議主動聯繫" },
  sales_ready: { color: "bg-red-100 text-red-800",       desc: "已提交詢價或分數極高", action: "高優先提醒，立即業務跟進" },
};

type StageThreshold = { min_score: number; stage: string };
type Config = { base_scores: Record<string, number>; stage_thresholds: StageThreshold[] };

export default function IntentRulesPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [config, setConfig] = useState<Config | null>(null);
  const [draft, setDraft] = useState<Config | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const r = await fetch(`${API_BASE}/tracking/intent-rules`, { headers: buildApiHeaders(token) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d: Config = await r.json();
      setConfig(d);
      setDraft(structuredClone(d));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const handleScoreChange = (event: string, value: string) => {
    const n = parseInt(value, 10);
    if (isNaN(n) || n < 0) return;
    setDraft(prev => prev ? { ...prev, base_scores: { ...prev.base_scores, [event]: n } } : prev);
  };

  const handleStageChange = (index: number, field: "min_score" | "stage", value: string) => {
    setDraft(prev => {
      if (!prev) return prev;
      const thresholds = [...prev.stage_thresholds];
      thresholds[index] = { ...thresholds[index], [field]: field === "min_score" ? parseInt(value, 10) || 0 : value };
      return { ...prev, stage_thresholds: thresholds };
    });
  };

  const save = async () => {
    if (!draft) return;
    setSaving(true); setError(null);
    try {
      const r = await fetch(`${API_BASE}/tracking/intent-rules`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify(draft),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail ?? "儲存失敗");
      setConfig(d); setDraft(structuredClone(d));
      setSaved(true); setTimeout(() => setSaved(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setSaving(false); }
  };

  const reset = () => { if (config) setDraft(structuredClone(config)); };
  const isDirty = JSON.stringify(draft) !== JSON.stringify(config);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">關注度規則</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            設定行為權重與買家熱度門檻；儲存後約 2 分鐘生效
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={reset} disabled={saving || !isDirty}>
            <RotateCcw className="mr-1.5 h-4 w-4" />還原
          </Button>
          <Button size="sm" onClick={save} disabled={saving || !isDirty}>
            <Save className="mr-1.5 h-4 w-4" />
            {saving ? "儲存中…" : saved ? "✓ 已儲存" : "儲存設定"}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && <p className="text-sm text-muted-foreground">載入設定中…</p>}

      {draft && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* 行為評分規則 */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Zap className="h-4 w-4 text-yellow-500" />行為評分規則
              </CardTitle>
              <CardDescription>
                每個訪客行為觸發時的加分值。數字越高，該行為對意圖分數的貢獻越大。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">事件</th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">說明</th>
                    <th className="px-3 py-2 text-right font-medium text-muted-foreground w-28">分數</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {Object.entries(draft.base_scores).map(([event, score]) => {
                    const meta = EVENT_META[event];
                    const Icon = meta?.icon ?? Zap;
                    return (
                      <tr key={event} className="hover:bg-muted/30">
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <Icon className={`h-4 w-4 ${meta?.color ?? "text-muted-foreground"}`} />
                            <span className="font-medium">{meta?.label ?? event}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-muted-foreground text-xs">{meta?.note ?? "—"}</td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {config && config.base_scores[event] !== score && (
                              <span className="text-xs text-muted-foreground line-through">{config.base_scores[event]}</span>
                            )}
                            <input
                              type="number"
                              min={0}
                              max={999}
                              value={score}
                              onChange={e => handleScoreChange(event, e.target.value)}
                              className={`w-20 rounded border px-2 py-1 text-right text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary ${
                                config && config.base_scores[event] !== score
                                  ? "border-orange-400 bg-orange-50 text-orange-700"
                                  : ""
                              }`}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Intent Stage 門檻 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Target className="h-4 w-4 text-primary" />買家熱度門檻
              </CardTitle>
              <CardDescription>
                累積分數超過門檻時，訪客會升級為對應熱度。數字請由高到低排列。
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {draft.stage_thresholds.map((st, i) => {
                const meta = STAGE_META[st.stage];
                return (
                  <div key={st.stage} className={`rounded-lg p-3 ${meta?.color ?? "bg-muted text-foreground"}`}>
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-semibold">{STAGE_NAME[st.stage] ?? st.stage}</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-medium opacity-70">門檻</span>
                        {config && config.stage_thresholds[i]?.min_score !== st.min_score && (
                          <span className="text-xs opacity-60 line-through">{config.stage_thresholds[i]?.min_score}</span>
                        )}
                        <input
                          type="number"
                          min={0}
                          max={9999}
                          value={st.min_score}
                          onChange={e => handleStageChange(i, "min_score", e.target.value)}
                          className={`w-20 rounded border bg-white/70 px-2 py-1 text-right text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary ${
                            config && config.stage_thresholds[i]?.min_score !== st.min_score
                              ? "border-orange-400"
                              : ""
                          }`}
                        />
                        <span className="text-xs opacity-70">分</span>
                      </div>
                    </div>
                    {meta && (
                      <>
                        <p className="mt-1 text-xs opacity-80">{meta.desc}</p>
                        <p className="mt-0.5 text-xs font-medium">→ {meta.action}</p>
                      </>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* 衰減規則（唯讀） */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <RefreshCcw className="h-4 w-4 text-muted-foreground" />分數衰減規則
              </CardTitle>
              <CardDescription>閒置時間越長，意圖分數自動衰減（每日批次，固定規則）</CardDescription>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">閒置時間</th>
                    <th className="px-3 py-2 text-center font-medium text-muted-foreground">係數</th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">說明</th>
                  </tr>
                </thead>
                <tbody className="divide-y text-xs">
                  {[
                    { days: "7 天內",    mult: "×1.0", desc: "分數完整保留" },
                    { days: "8–14 天",   mult: "×0.8", desc: "衰減 20%" },
                    { days: "15–30 天",  mult: "×0.5", desc: "衰減 50%" },
                    { days: "31–60 天",  mult: "×0.2", desc: "衰減 80%" },
                    { days: "60 天以上", mult: "×0.0", desc: "分數歸零" },
                  ].map(r => (
                    <tr key={r.days} className="hover:bg-muted/30">
                      <td className="px-3 py-2 font-medium">{r.days}</td>
                      <td className="px-3 py-2 text-center font-mono">
                        <Badge variant="outline">{r.mult}</Badge>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground">{r.desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-xs text-muted-foreground">
                ⓘ 衰減規則為系統固定常數，如需調整請聯繫 ForgeBase 技術支援。
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
