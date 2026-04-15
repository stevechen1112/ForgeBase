#!/usr/bin/env python3
# Script to generate clean content-optimizer page with proper UTF-8
import os

CONTENT = '''\
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
  { value: "product",     label: "\u5546\u54c1" },
  { value: "application", label: "\u61c9\u7528\u5834\u666f" },
  { value: "category",    label: "\u5546\u54c1\u5206\u985e" },
] as const;

type EntityType = typeof ENTITY_TYPES[number]["value"];

const PERIOD_OPTIONS = [
  { value: 7,  label: "\u8fd17 \u5929" },
  { value: 30, label: "\u8fd130 \u5929" },
  { value: 90, label: "\u8fd190 \u5929" },
];

const SEVERITY_STYLES: Record<string, string> = {
  high:   "bg-red-100 text-red-700 border-red-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:    "bg-blue-100 text-blue-700 border-blue-200",
};

function scoreColor(score: number) {
  if (score >= 70) return { text: "text-green-600", bar: "bg-green-500", label: "\u826f\u597d" };
  if (score >= 50) return { text: "text-yellow-600", bar: "bg-yellow-400", label: "\u5f85\u6539\u5584" };
  return { text: "text-red-500", bar: "bg-red-400", label: "\u9700\u7acb\u5373\u512a\u5316" };
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
      if (!r.ok) throw new Error(d.detail ?? "\u512a\u5316\u5931\u6557");
      setResult(d);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  };

  const sc = result ? scoreColor(result.overall_score) : null;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">AI \u5167\u5bb9\u512a\u5316</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          \u9078\u64c7\u5be6\u9ad4\uff0cAI \u5206\u6790\u8fd1\u671f\u6d41\u91cf\u8207\u8f49\u63db\u6578\u64da\uff0c\u7d66\u51fa\u53ef\u57f7\u884c\u7684\u512a\u5316\u5efa\u8b70
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Wand2 className="h-4 w-4 text-primary" />\u9078\u64c7\u5206\u6790\u76ee\u6a19
          </CardTitle>
          <CardDescription>\u9078\u64c7\u8981\u512a\u5316\u7684\u5be6\u9ad4\u985e\u578b\u8207\u5177\u9ad4\u54c1\u9805</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">\u985e\u578b</label>
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
                \u54c1\u9805 {loadingEntities && <span className="opacity-60">\u8f09\u5165\u4e2d\u2026</span>}
              </label>
              {entityList.length > 0 ? (
                <select
                  value={entityId}
                  onChange={e => setEntityId(e.target.value)}
                  className="rounded border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">\u8acb\u9078\u64c7\u2026</option>
                  {entityList.map(e => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={entityId}
                  onChange={e => setEntityId(e.target.value)}
                  placeholder="\u8f38\u5165 Entity ID"
                  className="rounded border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
              )}
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">\u8cc7\u6599\u7bc4\u570d</label>
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
              {loading ? "\u5206\u6790\u4e2d\u2026" : "\u958b\u59cb\u512a\u5316"}
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
              <CardTitle className="text-sm font-medium text-muted-foreground">\u5167\u5bb9\u5065\u5eb7\u5206\u6578</CardTitle>
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
                <AlertCircle className="h-4 w-4 text-orange-500" />\u554f\u984c\u8a3a\u65b7
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {result.issues.length === 0 && <p className="text-sm text-muted-foreground">\u7121\u91cd\u5927\u554f\u984c</p>}
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
                  <TrendingUp className="h-4 w-4 text-primary" />\u512a\u5148\u57f7\u884c\u9805\u76ee
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
                  <Lightbulb className="h-4 w-4 text-yellow-500" />\u512a\u5316\u5efa\u8b70
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
                  <FileText className="h-4 w-4 text-muted-foreground" />\u5167\u5bb9\u7f3a\u53e3
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
                  <Wand2 className="h-4 w-4 text-violet-500" />AI \u5efa\u8b70\u6587\u6848
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.revised_title && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">\u5efa\u8b70\u6a19\u984c</p>
                    <p className="rounded bg-muted px-3 py-2 text-sm font-medium">{result.revised_title}</p>
                  </div>
                )}
                {result.revised_description && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">\u5efa\u8b70\u63cf\u8ff0</p>
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
'''

# Write with proper UTF-8
out_path = r'C:\Users\User\Desktop\ForgeBase\admin\src\app\(dashboard)\dashboard\content-optimizer\page.tsx'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(CONTENT)
print('Written', len(CONTENT.splitlines()), 'lines to', out_path)
