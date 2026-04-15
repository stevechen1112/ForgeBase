"use client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Wand2, Copy, Check, RotateCcw, AlertCircle } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

// ?�?� Types matching the actual backend response ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�

type Issue = { severity: "high" | "medium" | "low"; category: string; issue: string };
type Suggestion = { priority: number; category: string; action: string; expected_impact: string };
type OptimizeResult = {
  overall_score: number;
  performance_diagnosis: string;
  issues: Issue[];
  suggestions: Suggestion[];
  priority_actions: string[];
  revised_title: string;
  revised_description: string;
  content_gaps: string[];
};

type EntityOption = { id: string; name: string };

const ENTITY_TYPES = [
  { value: "product",     label: "?��?" },
  { value: "application", label: "?�用?�景" },
  { value: "category",    label: "?��??��?" },
] as const;

type EntityType = typeof ENTITY_TYPES[number]["value"];

const PERIOD_OPTIONS = [
  { value: 7,  label: "?��?7 �? },
  { value: 30, label: "?��?30 �? },
  { value: 90, label: "?��?90 �? },
];

const SEVERITY_STYLES: Record<string, string> = {
  high:   "bg-red-100 text-red-700 border-red-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:    "bg-blue-100 text-blue-700 border-blue-200",
};

const IMPACT_STYLES: Record<string, string> = {
  high:   "text-green-600",
  medium: "text-yellow-600",
  low:    "text-gray-400",
};

function scoreColor(score: number) {
  if (score >= 70) return { text: "text-green-600", bar: "bg-green-500", label: "?�好" };
  if (score >= 50) return { text: "text-yellow-600", bar: "bg-yellow-400", label: "?��? };
  return { text: "text-red-500", bar: "bg-red-400", label: "?�?��?" };
}

export default function ContentOptimizerPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  // Selection state
  const [entityType, setEntityType] = useState<EntityType>("product");
  const [entities, setEntities] = useState<EntityOption[]>([]);
  const [entityId, setEntityId] = useState("");
  const [periodDays, setPeriodDays] = useState(30);
  const [loadingEntities, setLoadingEntities] = useState(false);

  // Analysis state
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // ?�?� Load entity list when type changes ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
  const loadEntities = useCallback(async (type: EntityType) => {
    setLoadingEntities(true); setEntityId(""); setEntities([]);
    const endpointMap: Record<EntityType, string> = {
      product:     "/content/products?page_size=200",
      application: "/content/applications?page_size=200",
      category:    "/content/categories?page_size=200",
    };
    const nameField: Record<EntityType, string> = {
      product:     "product_name",
      application: "application_name",
      category:    "category_name",
    };
    try {
      const r = await fetch(`${API_BASE}${endpointMap[type]}`, { headers: buildApiHeaders(token) });
      const d = await r.json();
      const items: EntityOption[] = (Array.isArray(d) ? d : d.data ?? []).map((item: Record<string, string>) => ({
        id: item.id,
        name: item[nameField[type]] ?? item.id,
      }));
      setEntities(items);
    } catch {
      setEntities([]);
    } finally { setLoadingEntities(false); }
  }, [token]);

  useEffect(() => { loadEntities(entityType); }, [entityType, loadEntities]);

  const analyze = async () => {
    if (!entityId) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await fetch(`${API_BASE}/content/intelligence/optimize`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ entity_type: entityType, entity_id: entityId, period_days: periodDays }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail ?? "?��?失�?");
      setResult(d);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  };

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const reset = () => { setResult(null); setError(null); };

  const selectedEntity = entities.find(e => e.id === entityId);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">AI ?�容?��?</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          ?��??��??��??�場?��??��?，AI 結�?實�?流�??��??��??�面?�康度並?��??��?建議
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        {/* ?�?� 左�?：選?�設�??�?� */}
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">?��?設�?</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {/* Entity Type */}
              <div>
                <label className="mb-1.5 block text-sm font-medium">?�容類�?</label>
                <div className="flex gap-2">
                  {ENTITY_TYPES.map(t => (
                    <button
                      key={t.value}
                      onClick={() => setEntityType(t.value)}
                      className={`flex-1 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                        entityType === t.value
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border hover:bg-muted"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Entity Picker */}
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  ?��?{ENTITY_TYPES.find(t => t.value === entityType)?.label}
                  <span className="ml-1 text-red-500">*</span>
                </label>
                <select
                  value={entityId}
                  onChange={e => setEntityId(e.target.value)}
                  disabled={loadingEntities}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
                >
                  <option value="">{loadingEntities ? "載入中�? : `???��?${ENTITY_TYPES.find(t => t.value === entityType)?.label} ?�`}</option>
                  {entities.map(e => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
                {entities.length === 0 && !loadingEntities && (
                  <p className="mt-1 text-xs text-muted-foreground">此�??�目?�無?��??��??�容</p>
                )}
              </div>

              {/* Period */}
              <div>
                <label className="mb-1.5 block text-sm font-medium">?��??��?範�?</label>
                <select
                  value={periodDays}
                  onChange={e => setPeriodDays(Number(e.target.value))}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {PERIOD_OPTIONS.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>

              <div className="flex gap-2 pt-1">
                <Button onClick={analyze} disabled={loading || !entityId} className="flex-1">
                  <Wand2 className="mr-2 h-4 w-4" />
                  {loading ? "?��?中�? : "AI ?��??��?"}
                </Button>
                {result && (
                  <Button variant="outline" onClick={reset} title="清除結�?">
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {selectedEntity && result && (
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs font-medium text-muted-foreground mb-1">?��?對象</p>
                <p className="font-semibold">{selectedEntity.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5 capitalize">{entityType} · ?��?{periodDays} �?/p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* ?�?� ?��?：�??��????�?� */}
        <div className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!result && !loading && !error && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-24 text-center">
                <Wand2 className="mb-3 h-10 w-10 text-muted-foreground/30" />
                <p className="text-sm font-medium text-muted-foreground">?��??�容後�??�「AI ?��??��???/p>
                <p className="mt-1 text-xs text-muted-foreground">
                  AI 將�??�實?��??�、�?載�??�RFQ 轉�??��??��??�健康度
                </p>
              </CardContent>
            </Card>
          )}

          {loading && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-24 text-center">
                <div className="mb-3 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                <p className="text-sm text-muted-foreground">AI �?��?��?流�??��??�內容�?請�??��?/p>
              </CardContent>
            </Card>
          )}

          {result && (
            <div className="space-y-4">
              {/* ?��??�康?�數 */}
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-end justify-between mb-3">
                    <div>
                      <p className="text-sm text-muted-foreground">?��??�容?�康?�數</p>
                      <p className={`text-4xl font-bold mt-0.5 ${scoreColor(result.overall_score).text}`}>
                        {result.overall_score}
                        <span className="text-base font-normal text-muted-foreground"> / 100</span>
                      </p>
                    </div>
                    <Badge className={`${scoreColor(result.overall_score).text} bg-current/10 rounded-full px-3`}>
                      {scoreColor(result.overall_score).label}
                    </Badge>
                  </div>
                  <div className="h-2 rounded-full bg-muted">
                    <div
                      className={`h-2 rounded-full ${scoreColor(result.overall_score).bar} transition-all`}
                      style={{ width: `${result.overall_score}%` }}
                    />
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{result.performance_diagnosis}</p>
                </CardContent>
              </Card>

              {/* ?��?行�? */}
              {result.priority_actions?.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-orange-600">???��?行�?（�??��??��?</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ol className="space-y-2">
                      {result.priority_actions.map((a, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-orange-100 text-center text-xs font-bold text-orange-700 leading-5">
                            {i + 1}
                          </span>
                          {a}
                        </li>
                      ))}
                    </ol>
                  </CardContent>
                </Card>
              )}

              {/* 建議標�? + ?�述 */}
              {(result.revised_title || result.revised_description) && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">AI 建議?�寫?��?</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {result.revised_title && (
                      <div>
                        <p className="mb-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide">標�?建議</p>
                        <div className="flex items-start justify-between gap-2 rounded-md bg-muted/40 px-3 py-2">
                          <p className="text-sm font-medium leading-snug">{result.revised_title}</p>
                          <Button variant="ghost" size="sm" className="h-7 w-16 shrink-0" onClick={() => copy(result.revised_title, "title")}>
                            {copied === "title" ? <><Check className="mr-1 h-3.5 w-3.5 text-green-500" /><span className="text-xs text-green-500">??/span></> : <><Copy className="mr-1 h-3.5 w-3.5" /><span className="text-xs">複製</span></>}
                          </Button>
                        </div>
                      </div>
                    )}
                    {result.revised_description && (
                      <div>
                        <p className="mb-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide">?�述建議</p>
                        <div className="flex items-start justify-between gap-2 rounded-md bg-muted/40 px-3 py-2">
                          <p className="text-sm text-muted-foreground leading-relaxed">{result.revised_description}</p>
                          <Button variant="ghost" size="sm" className="h-7 w-16 shrink-0" onClick={() => copy(result.revised_description, "desc")}>
                            {copied === "desc" ? <><Check className="mr-1 h-3.5 w-3.5 text-green-500" /><span className="text-xs text-green-500">??/span></> : <><Copy className="mr-1 h-3.5 w-3.5" /><span className="text-xs">複製</span></>}
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* ?��?清單 */}
              {result.issues?.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">?�現?��?（{result.issues.length}�?/CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {result.issues.map((issue, i) => (
                        <div key={i} className={`rounded-md border px-3 py-2 text-sm ${SEVERITY_STYLES[issue.severity] ?? "border-border"}`}>
                          <div className="flex items-center gap-2 mb-0.5">
                            <Badge variant="outline" className="text-xs capitalize px-1.5 py-0 border-current">
                              {issue.severity}
                            </Badge>
                            <span className="text-xs text-muted-foreground capitalize">{issue.category}</span>
                          </div>
                          {issue.issue}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* ?��?建議 */}
              {result.suggestions?.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">?��?建議（�??��?級�?序�?</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {[...result.suggestions]
                        .sort((a, b) => a.priority - b.priority)
                        .map((s, i) => (
                          <div key={i} className="flex items-start gap-3 rounded-md bg-muted/30 px-3 py-2 text-sm">
                            <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-primary/10 text-center text-xs font-bold text-primary leading-5">
                              {s.priority}
                            </span>
                            <div className="flex-1">
                              <span className="text-xs text-muted-foreground capitalize mr-2">[{s.category}]</span>
                              {s.action}
                            </div>
                            <span className={`text-xs font-medium shrink-0 ${IMPACT_STYLES[s.expected_impact] ?? "text-muted-foreground"}`}>
                              {s.expected_impact === "high" ? "高�??? : s.expected_impact === "medium" ? "中�??? : "低�???}
                            </span>
                          </div>
                        ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* ?�容缺口 */}
              {result.content_gaps?.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">?�容缺口（建議�??��?主�?�?/CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {result.content_gaps.map((gap, i) => (
                        <Badge key={i} variant="outline" className="text-sm px-3 py-1">{gap}</Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

