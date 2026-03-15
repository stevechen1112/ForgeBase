"use client";
import { useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Wand2, Copy, RotateCcw } from "lucide-react";

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

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">AI 內容優化</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">輸入頁面標題與內容，AI 將分析並提供 SEO 優化建議</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
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
                <label className="mb-1 block text-sm font-medium">目標關鍵字 <span className="text-muted-foreground">（選填）</span></label>
                <input
                  type="text"
                  value={targetKeyword}
                  onChange={e => setTargetKeyword(e.target.value)}
                  placeholder="e.g. industrial sensor, smart manufacturing"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
                />
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
                <Button variant="outline" onClick={() => { setTitle(""); setContent(""); setTargetKeyword(""); setResult(null); }}>
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
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!result && !loading && !error && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <Wand2 className="mb-3 h-10 w-10 text-muted-foreground/30" />
                <p className="text-sm font-medium text-muted-foreground">輸入內容後點擊「AI 優化分析」</p>
                <p className="mt-1 text-xs text-muted-foreground">AI 將分析 SEO 關鍵字密度、可讀性並提供改寫建議</p>
              </CardContent>
            </Card>
          )}

          {loading && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <div className="mb-3 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                <p className="text-sm text-muted-foreground">AI 分析中，請稍候…</p>
              </CardContent>
            </Card>
          )}

          {result && (
            <div className="space-y-4">
              {result.optimized_title && (
                <Card>
                  <CardHeader><CardTitle className="text-sm">優化標題建議</CardTitle></CardHeader>
                  <CardContent>
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-medium">{result.optimized_title}</p>
                      <Button variant="ghost" size="sm" onClick={() => copy(result.optimized_title!, "title")}>
                        <Copy className="h-4 w-4" />{copied === "title" ? "已複製" : ""}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
              {result.meta_description && (
                <Card>
                  <CardHeader><CardTitle className="text-sm">Meta Description 建議</CardTitle></CardHeader>
                  <CardContent>
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm text-muted-foreground">{result.meta_description}</p>
                      <Button variant="ghost" size="sm" onClick={() => copy(result.meta_description!, "meta")}>
                        <Copy className="h-4 w-4" />{copied === "meta" ? "已複製" : ""}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
              {result.seo_suggestions && result.seo_suggestions.length > 0 && (
                <Card>
                  <CardHeader><CardTitle className="text-sm">SEO 改善建議</CardTitle></CardHeader>
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
              {result.readability_score !== undefined && (
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-sm text-muted-foreground">可讀性分數</p>
                    <p className="mt-1 text-3xl font-bold">{result.readability_score}</p>
                    <div className="mt-2 h-2 rounded-full bg-muted">
                      <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.min(100, result.readability_score)}%` }} />
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
