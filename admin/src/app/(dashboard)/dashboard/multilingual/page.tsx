"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Globe } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

const LOCALES = [
  { code: "en",    label: "English",   flag: "🇺🇸" },
  { code: "zh-TW", label: "繁體中文",  flag: "🇹🇼" },
  { code: "zh-CN", label: "简体中文",  flag: "🇨🇳" },
  { code: "ja",    label: "日本語",    flag: "🇯🇵" },
  { code: "de",    label: "Deutsch",   flag: "🇩🇪" },
  { code: "fr",    label: "Français",  flag: "🇫🇷" },
];

// 需要追蹤翻譯覆蓋率的內容類型
const CONTENT_TYPES = [
  { key: "products",       label: "商品",       endpoint: "/content/products" },
  { key: "faqs",           label: "FAQs",       endpoint: "/content/faqs" },
  { key: "applications",   label: "應用場景",   endpoint: "/content/applications" },
  { key: "capabilities",   label: "廠能",       endpoint: "/content/capabilities" },
  { key: "certifications", label: "認證",       endpoint: "/content/certifications" },
  { key: "categories",     label: "商品分類",   endpoint: "/content/categories" },
  { key: "pages",          label: "落地頁",     endpoint: "/content/pages" },
  { key: "ctas",           label: "CTAs",       endpoint: "/content/ctas" },
];

type Coverage = Record<string, Record<string, number>>;
// coverage[locale][contentKey] = count

async function fetchCount(endpoint: string, locale: string, token: string): Promise<number> {
  const r = await fetch(`${API_BASE}${endpoint}?locale=${locale}&page_size=1`, {
    headers: buildApiHeaders(token),
  });
  if (!r.ok) return 0;
  const d = await r.json();
  // API 回傳格式可能是 array 或 { total, data }
  if (Array.isArray(d)) return d.length;
  if (typeof d.total === "number") return d.total;
  if (Array.isArray(d.data)) return d.data.length;
  return 0;
}

export default function MultilingualPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [coverage, setCoverage] = useState<Coverage>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 並行抓取所有語言 × 所有內容類型
      const pairs = LOCALES.flatMap(loc =>
        CONTENT_TYPES.map(ct => ({ locale: loc.code, contentKey: ct.key, endpoint: ct.endpoint }))
      );
      const results = await Promise.all(
        pairs.map(async ({ locale, contentKey, endpoint }) => ({
          locale,
          contentKey,
          count: await fetchCount(endpoint, locale, token),
        }))
      );
      const map: Coverage = {};
      for (const { locale, contentKey, count } of results) {
        if (!map[locale]) map[locale] = {};
        map[locale][contentKey] = count;
      }
      setCoverage(map);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  // 英文為基準（100%）
  const baseCounts = coverage["en"] ?? {};

  // 整體覆蓋率：各語言所有類型加總 / 英文加總
  const totalBase = Object.values(baseCounts).reduce((a, b) => a + b, 0);
  const overallPct = (locale: string) => {
    if (totalBase === 0) return 0;
    const total = Object.values(coverage[locale] ?? {}).reduce((a, b) => a + b, 0);
    return Math.min(100, Math.round((total / totalBase) * 100));
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">多語管理</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            以英文（en）為基準，追蹤各語言版本的內容翻譯覆蓋率
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && !Object.keys(coverage).length ? (
        <p className="py-16 text-center text-sm text-muted-foreground">載入中…</p>
      ) : (
        <div className="space-y-4">
          {LOCALES.map(loc => {
            const isBase = loc.code === "en";
            const pct = isBase ? 100 : overallPct(loc.code);
            const locData = coverage[loc.code] ?? {};

            return (
              <Card key={loc.code}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center justify-between text-base">
                    <span className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-primary" />
                      <span className="text-lg">{loc.flag}</span>
                      {loc.label}
                      <span className="text-sm font-normal text-muted-foreground">{loc.code}</span>
                      {isBase && (
                        <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
                          基準語言
                        </span>
                      )}
                    </span>
                    <span className={`text-sm font-semibold ${pct === 100 ? "text-green-600" : pct > 0 ? "text-amber-600" : "text-muted-foreground"}`}>
                      {pct}%
                    </span>
                  </CardTitle>
                  {/* 整體進度條 */}
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className={`h-full rounded-full transition-all ${pct === 100 ? "bg-green-500" : pct > 0 ? "bg-amber-400" : "bg-muted-foreground/20"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
                    {CONTENT_TYPES.map(ct => {
                      const count = locData[ct.key] ?? 0;
                      const base = baseCounts[ct.key] ?? 0;
                      const typePct = base === 0 ? (isBase ? 100 : 0) : Math.min(100, Math.round((count / base) * 100));
                      return (
                        <div key={ct.key} className="flex items-center justify-between gap-2 text-sm">
                          <span className="text-muted-foreground">{ct.label}</span>
                          <span className={`font-medium tabular-nums ${typePct === 100 ? "text-green-600" : typePct > 0 ? "text-amber-600" : "text-muted-foreground"}`}>
                            {isBase ? base : `${count} / ${base}`}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
