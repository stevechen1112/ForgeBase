"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Search, Sparkles, Wand2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { seoWorkbenchApi, type SEOEvaluation } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

type Props = {
  entityType: "product" | "category" | "application" | "page";
  data: Record<string, unknown>;
  onApplyField: (field: string, value: string) => void;
};

export function SEOAssistantPanel({ entityType, data, onApplyField }: Props) {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [result, setResult] = useState<SEOEvaluation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const entityName = useMemo(() => {
    if (entityType === "product") return String(data.product_name || data.model_number || "目前產品");
    if (entityType === "category") return String(data.category_name || "目前分類");
    if (entityType === "application") return String(data.application_name || "目前應用場景");
    return String(data.title || data.slug || "目前頁面");
  }, [data, entityType]);

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    try {
      const response = await seoWorkbenchApi.evaluate(token, { entity_type: entityType, data });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "SEO 分析失敗");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="border-blue-200 bg-blue-50/30">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="h-4 w-4" /> SEO 助手
          </CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            用一般人看得懂的方式檢查 {entityName} 的搜尋曝光準備度。
          </p>
        </div>
        <Button type="button" variant="outline" onClick={handleAnalyze} disabled={loading}>
          {loading ? <Wand2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
          {loading ? "分析中…" : "分析目前內容"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {result ? (
          <>
            <div className="grid gap-4 md:grid-cols-[140px_1fr]">
              <div className="rounded-lg border bg-background p-4">
                <div className="text-sm text-muted-foreground">SEO 健康度</div>
                <div className="mt-2 text-3xl font-semibold">{result.score}</div>
                <Progress className="mt-3" value={result.score} />
                <Badge className="mt-3" variant={result.status === "healthy" ? "default" : result.status === "needs-work" ? "secondary" : "destructive"}>
                  {result.status === "healthy" ? "穩定" : result.status === "needs-work" ? "可再優化" : "需先補強"}
                </Badge>
              </div>

              <div className="rounded-lg border bg-background p-4">
                <div className="text-sm text-muted-foreground">Google 搜尋結果預覽</div>
                <div className="mt-3 space-y-1">
                  <div className="text-lg font-medium text-blue-700">{result.search_preview.title}</div>
                  <div className="text-xs text-green-700">{result.search_preview.url}</div>
                  <div className="text-sm text-muted-foreground">{result.search_preview.description}</div>
                </div>
              </div>
            </div>

            <Alert>
              <AlertDescription>{result.summary}</AlertDescription>
            </Alert>

            {!!result.focus_keywords.length && (
              <div className="space-y-2">
                <div className="text-sm font-medium">系統辨識到的重點主題</div>
                <div className="flex flex-wrap gap-2">
                  {result.focus_keywords.map((keyword) => (
                    <Badge key={keyword} variant="outline">{keyword}</Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2">
              <div className="text-sm font-medium">目前檢查結果</div>
              <div className="space-y-2">
                {result.checks.map((check) => (
                  <div key={check.id} className="flex items-start gap-3 rounded-md border bg-background p-3">
                    {check.status === "good" ? (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 text-green-600" />
                    ) : (
                      <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-600" />
                    )}
                    <div>
                      <div className="text-sm font-medium">{check.label}</div>
                      <div className="text-sm text-muted-foreground">{check.message}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {!!result.suggestions.length && (
              <div className="space-y-2">
                <div className="text-sm font-medium">建議先做的事</div>
                <div className="space-y-2">
                  {result.suggestions.map((suggestion) => (
                    <div key={suggestion.id} className="rounded-md border bg-background p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-medium">{suggestion.title}</div>
                          <div className="mt-1 text-sm text-muted-foreground">{suggestion.detail}</div>
                        </div>
                        <Badge variant={suggestion.priority === "high" ? "destructive" : suggestion.priority === "medium" ? "secondary" : "outline"}>
                          {suggestion.priority}
                        </Badge>
                      </div>
                      {suggestion.field && suggestion.suggested_value && (
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => onApplyField(suggestion.field!, suggestion.suggested_value!)}
                          >
                            套用建議
                          </Button>
                          <span className="text-xs text-muted-foreground">{suggestion.suggested_value}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="rounded-md border border-dashed bg-background p-4 text-sm text-muted-foreground">
            按一下「分析目前內容」，系統會檢查 Google 標題、搜尋摘要、內容深度與主題清晰度，並直接給可採用的建議。
          </div>
        )}
      </CardContent>
    </Card>
  );
}