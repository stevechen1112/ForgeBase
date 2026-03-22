"use client";
import { useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Wand2, Copy, Check, RotateCcw, AlertCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type OptimizeResult = {
  optimized_title?: string;
  optimized_description?: string;
  seo_suggestions?: string[];
  readability_score?: number;
  keyword_density?: Record<string, number>;
  meta_title?: string;
  meta_description?: string;
};

function readabilityColor(score: number) {
  if (score >= 70) return { bar: "bg-green-500", text: "text-green-600", label: "易讀" };
  if (score >= 50) return { bar: "bg-yellow-400", text: "text-yellow-600", label: "普通" };
  return { bar: "bg-red-500", text: "text-red-600", label: "偏難" };
}

export default function ContentOptimizerPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [targetKeyword, setTargetKeyword] = useState("");
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const optimize = async () => {
    if (!content.trim()) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await fetch(`${API_BASE}/content/intelligence/optimize`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ title, content, target_keyword: targetKeyword }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail ?? "最佳化失敗");
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

  const handleReset = () => {
    setTitle(""); setContent(""); setTargetKeyword(""); setResult(null); setError(null);
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">AI 內容優化</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">輸入頁面標題與內容，AI 將分析並提供 SEO 優化建議</p>
      </div>

      {/* Fix #7: 左欄固定寬度，右欄彈性伸展，讓結果區有更多空間 */}
      <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
        {/* Input */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">輸入內容</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">頁面標題</label>
                <input
                  type="text"
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  placeholder="e.g. Industrial IoT Sensors for Manufacturing"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                {/* Fix #5: 加格式說明文字 */}
                <label className="mb-1 block text-sm font-medium">
                  目標關鍵字 <span className="text-muted-foreground">（選填）</span>
                </label>
                <input
                  type="text"
                  value={targetKeyword}
                  onChange={e => setTargetKeyword(e.target.value)}
                  placeholder="e.g. industrial sensor, smart manufacturing"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
                />
                <p className="mt-1 text-xs text-muted-foreground">多個關鍵字請用英文逗號分隔</p>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">頁面內容 <span className="text-red-500">*</span></label>
                <textarea
                  rows={10}
                  value={content}
                  onChange={e => setContent(e.target.value)}
                  placeholder="貼上頁面的主要文字內容…"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
                />
                <p className="mt-1 text-xs text-muted-foreground">{content.length} 字元</p>
              </div>
              <div className="flex gap-2">
                <Button onClick={optimize} disabled={loading || !content.trim()} className="flex-1">
                  <Wand2 className="mr-2 h-4 w-4" />
                  {loading ? "分析中…" : "AI 優化分析"}
                </Button>
                {/* Fix #6: 清除按鈕加 title + aria-label */}
                <Button
                  variant="outline"
                  title="清除所有內容"
                  aria-label="清除所有內容"
                  onClick={handleReset}
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Output */}
        <div className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!result && !loading && !error && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-20 text-center">
                <Wand2 className="mb-3 h-10 w-10 text-muted-foreground/30" />
                <p className="text-sm font-medium text-muted-foreground">輸入內容後點擊「AI 優化分析」</p>
                <p className="mt-1 text-xs text-muted-foreground">AI 將分析 SEO 關鍵字密度、可讀性並提供改寫建議</p>
              </CardContent>
            </Card>
          )}

          {loading && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-20 text-center">
                <div className="mb-3 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                <p className="text-sm text-muted-foreground">AI 分析中，請稍候…</p>
              </CardContent>
            </Card>
          )}

          {result && (
            <div className="space-y-6">
              {/* Fix #8: 視覺分組 — 優化文案建議 */}
              {(result.optimized_title || result.optimized_description || result.meta_description || (result.seo_suggestions && result.seo_suggestions.length > 0)) && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">優化文案建議</p>

                  {result.optimized_title && (
                    <Card>
                      <CardHeader className="pb-2"><CardTitle className="text-sm">優化標題建議</CardTitle></CardHeader>
                      <CardContent>
                        <div className="flex items-start justify-between gap-2">
                          <p className="font-medium leading-snug">{result.optimized_title}</p>
                          {/* Fix #4: 複製按鈕固定寬度不抖動 */}
                          <Button variant="ghost" size="sm" className="w-20 shrink-0" onClick={() => copy(result.optimized_title!, "title")}>
                            {copied === "title" ? <><Check className="mr-1 h-3.5 w-3.5 text-green-500" /><span className="text-green-500">已複製</span></> : <><Copy className="mr-1 h-3.5 w-3.5" />複製</>}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Fix #2: 顯示 optimized_description */}
                  {result.optimized_description && (
                    <Card>
                      <CardHeader className="pb-2"><CardTitle className="text-sm">優化描述建議</CardTitle></CardHeader>
                      <CardContent>
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm text-muted-foreground leading-relaxed">{result.optimized_description}</p>
                          <Button variant="ghost" size="sm" className="w-20 shrink-0" onClick={() => copy(result.optimized_description!, "desc")}>
                            {copied === "desc" ? <><Check className="mr-1 h-3.5 w-3.5 text-green-500" /><span className="text-green-500">已複製</span></> : <><Copy className="mr-1 h-3.5 w-3.5" />複製</>}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {result.meta_description && (
                    <Card>
                      <CardHeader className="pb-2"><CardTitle className="text-sm">Meta Description 建議</CardTitle></CardHeader>
                      <CardContent>
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm text-muted-foreground leading-relaxed">{result.meta_description}</p>
                          <Button variant="ghost" size="sm" className="w-20 shrink-0" onClick={() => copy(result.meta_description!, "meta")}>
                            {copied === "meta" ? <><Check className="mr-1 h-3.5 w-3.5 text-green-500" /><span className="text-green-500">已複製</span></> : <><Copy className="mr-1 h-3.5 w-3.5" />複製</>}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {result.seo_suggestions && result.seo_suggestions.length > 0 && (
                    <Card>
                      <CardHeader className="pb-2"><CardTitle className="text-sm">SEO 改善建議</CardTitle></CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {result.seo_suggestions.map((s, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm">
                              <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-primary/10 text-center text-xs font-bold text-primary leading-5">{i + 1}</span>
                              {s}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {/* Fix #8: 視覺分組 — 技術分析數據 */}
              {(result.readability_score !== undefined || (result.keyword_density && Object.keys(result.keyword_density).length > 0)) && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">技術分析數據</p>

                  {/* Fix #3: 可讀性分數語義顏色 */}
                  {result.readability_score !== undefined && (() => {
                    const { bar, text, label } = readabilityColor(result.readability_score);
                    return (
                      <Card>
                        <CardContent className="pt-4">
                          <div className="flex items-end justify-between">
                            <div>
                              <p className="text-sm text-muted-foreground">可讀性分數</p>
                              <p className={`mt-0.5 text-3xl font-bold ${text}`}>{result.readability_score}</p>
                            </div>
                            <span className={`mb-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${text} bg-current/10`}
                              style={{ backgroundColor: "color-mix(in srgb, currentColor 12%, transparent)" }}>
                              {label}
                            </span>
                          </div>
                          <div className="mt-3 h-2 rounded-full bg-muted">
                            <div className={`h-2 rounded-full ${bar} transition-all`} style={{ width: `${Math.min(100, result.readability_score)}%` }} />
                          </div>
                          <p className="mt-1.5 text-xs text-muted-foreground">滿分 100，建議 70 分以上</p>
                        </CardContent>
                      </Card>
                    );
                  })()}

                  {/* Fix #1: 顯示 keyword_density */}
                  {result.keyword_density && Object.keys(result.keyword_density).length > 0 && (
                    <Card>
                      <CardHeader className="pb-2"><CardTitle className="text-sm">關鍵字密度分析</CardTitle></CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {Object.entries(result.keyword_density)
                            .sort(([, a], [, b]) => b - a)
                            .map(([kw, density]) => {
                              const pct = Math.min(100, density * 100);
                              const isTarget = targetKeyword.toLowerCase().split(",").map(k => k.trim()).includes(kw.toLowerCase());
                              return (
                                <div key={kw}>
                                  <div className="flex items-center justify-between mb-0.5">
                                    <span className={`text-sm ${isTarget ? "font-semibold text-primary" : ""}`}>
                                      {kw}{isTarget && <span className="ml-1.5 rounded bg-primary/10 px-1 py-0.5 text-xs text-primary">目標</span>}
                                    </span>
                                    <span className="text-xs text-muted-foreground">{(density * 100).toFixed(1)}%</span>
                                  </div>
                                  <div className="h-1.5 rounded-full bg-muted">
                                    <div
                                      className={`h-1.5 rounded-full ${isTarget ? "bg-primary" : "bg-muted-foreground/40"}`}
                                      style={{ width: `${pct}%` }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                        </div>
                        <p className="mt-3 text-xs text-muted-foreground">建議目標關鍵字密度落在 1–3% 之間</p>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
