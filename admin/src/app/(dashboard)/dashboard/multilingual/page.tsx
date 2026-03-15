"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Globe, FileText } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const LOCALES = [
  { code: "en", label: "English", flag: "🇺🇸" },
  { code: "zh-TW", label: "繁體中文", flag: "🇹🇼" },
  { code: "zh-CN", label: "简体中文", flag: "🇨🇳" },
  { code: "ja", label: "日本語", flag: "🇯🇵" },
  { code: "de", label: "Deutsch", flag: "🇩🇪" },
  { code: "fr", label: "Français", flag: "🇫🇷" },
];

type Page = {
  id: string;
  title: string;
  slug: string;
  locale?: string;
  is_published?: boolean;
  created_at?: string;
};

export default function MultilingualPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [pagesByLocale, setPagesByLocale] = useState<Record<string, Page[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeLocale, setActiveLocale] = useState("en");

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const results = await Promise.all(
        LOCALES.map(async loc => {
          const r = await fetch(`${API_BASE}/content/pages?locale=${loc.code}&page_size=50`, { headers });
          const d = await r.json();
          const pages = Array.isArray(d) ? d : d.data ?? d.items ?? [];
          return { locale: loc.code, pages };
        })
      );
      const map: Record<string, Page[]> = {};
      results.forEach(({ locale, pages }) => { map[locale] = pages; });
      setPagesByLocale(map);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const pages = pagesByLocale[activeLocale] ?? [];
  const totalByLocale = LOCALES.map(l => ({ ...l, count: pagesByLocale[l.code]?.length ?? 0 }));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">多語管理</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">檢視各語言版本的頁面數量與發佈狀態</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Locale overview */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {totalByLocale.map(l => (
          <button
            key={l.code}
            onClick={() => setActiveLocale(l.code)}
            className={`rounded-lg border p-3 text-left transition-colors ${activeLocale === l.code ? "border-primary bg-primary/5" : "hover:border-primary/30"}`}
          >
            <p className="text-2xl">{l.flag}</p>
            <p className="mt-1 text-sm font-medium">{l.label}</p>
            <p className="text-xs text-muted-foreground">{l.count} 頁</p>
          </button>
        ))}
      </div>

      {/* Pages table for selected locale */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="h-4 w-4 text-primary" />
            {LOCALES.find(l => l.code === activeLocale)?.flag}{" "}
            {LOCALES.find(l => l.code === activeLocale)?.label} 頁面列表（{pages.length}）
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : pages.length === 0 ? (
            <div className="py-12 text-center">
              <FileText className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">
                {LOCALES.find(l => l.code === activeLocale)?.label} 尚無頁面
              </p>
              <p className="mt-1 text-xs text-muted-foreground">在建立頁面時選擇對應的語言版本</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">標題</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">Slug</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">語言</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {pages.map(p => (
                  <tr key={p.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">{p.title}</td>
                    <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{p.slug}</td>
                    <td className="px-4 py-2 text-center">
                      <Badge className={p.is_published !== false ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
                        {p.is_published !== false ? "已發佈" : "草稿"}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{p.locale ?? activeLocale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
