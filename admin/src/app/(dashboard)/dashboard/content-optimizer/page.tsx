"use client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Wand2, ChevronRight, AlertCircle, CheckCircle2, Lightbulb, TrendingUp, FileText } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

const ENTITY_TYPES = [
  { value: "product",     label: "商品" },
  { value: "application", label: "應用場景" },
  { value: "category",    label: "商品分類" },
] as const;

type EntityType = typeof ENTITY_TYPES[number]["value"];

const PERIOD_OPTIONS = [
  { value: 7,  label: "近7 天" },
  { value: 30, label: "近30 天" },
  { value: 90, label: "近90 天" },
];

const SEVERITY_STYLES: Record<string, string> = {
  high:   "bg-red-100 text-red-700 border-red-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:    "bg-blue-100 text-blue-700 border-blue-200",
};

function scoreColor(score: number) {
  if (score >= 70) return { text: "text-green-600", bar: "bg-green-500", label: "良好" };
  if (score >= 50) return { text: "text-yellow-600", bar: "bg-yellow-400", label: "待改善" };
  return { text: "text-red-500", bar: "bg-red-400", label: "需立即優化" };
}

type EntityOption = { id: string; name: string };

type OptimizeResult = {
  overall_score: number;
  issues: { severity: string; message: string }[];
  suggestions: string[];
  priority_actions: string[];
  revised_title?: string;
  revised_description?: string;
  content_gaps?: string[];
};

export default function ContentOptimizerPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [entityType, setEntityType] = useState<EntityType>("product");
  const [entityList, setEntityList] = useState<EntityOption[]>([]);
  const [entityId, setEntityId] = useState("");
  const [periodDays, setPeriodDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [loadingEntities, setLoadingEntities] = useState(false);
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadEntities = useCallback(async (type: EntityType) => {
    setLoadingEntities(true);
    setEntityList([]);
    setEntityId("");
    try {
      const endpointMap: Record<EntityType, string> = {
        product:     "/content/products?page_size=200",
        application: "/content/applications?page_size=200",
        category:    "/content/categories?page_size=200",
      };
      const r = await fetch(`${API_BASE}${endpointMap[type]}`, { headers: buildApiHeaders(token) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const nameField: Record<EntityType, string> = { product: "name", application: "title", category: "name" };
      const items: EntityOption[] = (Array.isArray(d) ? d : d.data ?? []).map((item: Record<string, string>) => ({
        id: item.id,
        name: item[nameField[type]] ?? item.id,
      }));
      setEntityList(items);
    } catch {
      // silently ignore
    } finally {
      setLoadingEntities(false);
    }
  }, [token]);

  useEffect(() => { loadEntities(entityType); }, [entityType, loadEntities]);

  const handleOptimize = async () => {
    if (!entityId) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await fetch(`${API_BASE}/content/intelligence/optimize`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ entity_type: entityType, entity_id: entityId, period_days: periodDays }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail ?? "優化失敗");
      setResult(d);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  };

  const sc = result ? scoreColor(result.overall_score) : null;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">AI 文案優化</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          依近期瀏覽與詢價數據，產出可執行的文案優化建議
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Wand2 className="h-4 w-4 text-primary" />選擇分析目標
          </CardTitle>
          <CardDescription>選擇要優化的內容類型與具體品項</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">類型</label>
              <select
                value={entityType}
                onChange={e => setEntityType(e.target.value as EntityType)}
                className="rounded border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary min-w-[120px]"
              >
                {ENTITY_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1 min-w-[220px] flex-1">
              <label className="text-xs font-medium text-muted-foreground">
                品項 {loadingEntities && <span className="opacity-60">載入中…</span>}
              </label>
              {entityList.length > 0 ? (
                <select
                  value={entityId}
                  onChange={e => setEntityId(e.target.value)}
                  className="rounded border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">請選擇…</option>
                  {entityList.map(e => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={entityId}
                  onChange={e => setEntityId(e.target.value)}
                  placeholder="輸入內容編號"
                  className="rounded border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
              )}
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">資料範圍</label>
              <select
                value={periodDays}
                onChange={e => setPeriodDays(Number(e.target.value))}
                className="rounded border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {PERIOD_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            <Button onClick={handleOptimize} disabled={loading || !entityId} className="self-end">
              <Wand2 className="mr-1.5 h-4 w-4" />
              {loading ? "分析中…" : "開始優化"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && sc && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">內容健康分數</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-5xl font-bold tabular-nums ${sc.text}`}>{result.overall_score}</div>
              <Badge variant="outline" className={`mt-1 text-xs ${sc.text}`}>{sc.label}</Badge>
              <div className="mt-3 h-2 w-full rounded-full bg-muted">
                <div className={`h-2 rounded-full ${sc.bar}`} style={{ width: `${result.overall_score}%` }} />
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <AlertCircle className="h-4 w-4 text-orange-500" />問題診斷
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {result.issues.length === 0 && <p className="text-sm text-muted-foreground">無重大問題</p>}
              {result.issues.map((issue, i) => (
                <div key={i} className={`rounded border px-3 py-2 text-sm ${SEVERITY_STYLES[issue.severity] ?? "bg-muted"}`}>
                  <span className="mr-2 font-semibold capitalize">[{issue.severity}]</span>
                  {issue.message}
                </div>
              ))}
            </CardContent>
          </Card>

          {result.priority_actions?.length > 0 && (
            <Card className="lg:col-span-3 border-primary/30">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <TrendingUp className="h-4 w-4 text-primary" />優先執行項目
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-1.5">
                  {result.priority_actions.map((action, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      {action}
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          )}

          {result.suggestions?.length > 0 && (
            <Card className="lg:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <Lightbulb className="h-4 w-4 text-yellow-500" />優化建議
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1.5">
                  {result.suggestions.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
                      {s}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {result.content_gaps && result.content_gaps.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <FileText className="h-4 w-4 text-muted-foreground" />內容缺口
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {result.content_gaps.map((gap, i) => (
                  <p key={i} className="text-sm text-muted-foreground">{gap}</p>
                ))}
              </CardContent>
            </Card>
          )}

          {(result.revised_title || result.revised_description) && (
            <Card className="lg:col-span-3">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm font-medium">
                  <Wand2 className="h-4 w-4 text-violet-500" />AI 建議文案
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.revised_title && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">建議標題</p>
                    <p className="rounded bg-muted px-3 py-2 text-sm font-medium">{result.revised_title}</p>
                  </div>
                )}
                {result.revised_description && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">建議描述</p>
                    <p className="rounded bg-muted px-3 py-2 text-sm leading-relaxed">{result.revised_description}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
