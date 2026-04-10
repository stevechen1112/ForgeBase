"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, FileText, Package, LayoutGrid, ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import { apiClient } from "@/lib/api/client";

// ── 流量統計資料型別（來自 /tracking/analytics/* ）────────────────────────────
type SummaryRow = { total_events: number; total_pages: number; total_unique_visitors: number };
type PageRow = {
  page_id?: string; page_type?: string; page_name?: string;
  page_views?: number; unique_visitors?: number; spec_downloads?: number;
  rfq_count?: number; avg_intent_score?: number;
  // 商品專屬
  model_number?: string; category_slug?: string;
  // 應用場景專屬
  industry?: string;
  // 舊欄位相容
  slug?: string; title?: string; views?: number; events?: number;
};

const PAGE_TYPE_LABEL: Record<string, string> = {
  product: "商品頁",
  application: "應用場景",
  page: "一般頁面",
  category: "分類頁",
};
type AnalyticsResponse = {
  period_days: number;
  summary?: SummaryRow;
  pages?: PageRow[];
  products?: PageRow[];
  applications?: PageRow[];
};

// ── 主內容 tab 定義 ───────────────────────────────────────────────────────────
type ContentTab = "pages" | "products" | "applications";
const CONTENT_TABS: { key: ContentTab; label: string; icon: React.ElementType; endpoint: string; rowKey: ContentTab }[] = [
  { key: "pages",        label: "頁面",    icon: FileText,   endpoint: "tracking/analytics/pages",        rowKey: "pages" },
  { key: "products",     label: "商品",    icon: Package,    endpoint: "tracking/analytics/products",     rowKey: "products" },
  { key: "applications", label: "應用場景", icon: LayoutGrid, endpoint: "tracking/analytics/applications", rowKey: "applications" },
];

const DAYS_OPTIONS = [7, 14, 30, 90];

// ── 取顯示名稱 ────────────────────────────────────────────────────────────────
function rowName(r: PageRow) { return r.page_name ?? r.title ?? r.slug ?? r.page_id ?? "—"; }
function rowSubtext(r: PageRow, tab: ContentTab): string {
  if (tab === "products") {
    const parts = [r.model_number, r.category_slug].filter(Boolean);
    return parts.length > 0 ? parts.join(" · ") : (r.page_type ?? "");
  }
  if (tab === "applications") return r.industry ?? r.page_type ?? "";
  // pages tab: 顯示頁面類型文字
  return PAGE_TYPE_LABEL[r.page_type ?? ""] ?? r.page_type ?? "";
}
function rowViews(r: PageRow) { return r.page_views ?? r.views ?? 0; }

type SortKey = "views" | "unique_visitors" | "spec_downloads" | "rfq_count" | "rfq_rate";
type SortDir = "desc" | "asc";

export default function ContentPerformancePage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  // ── 狀態 ──────────────────────────────────────────────────────────────────
  const [days, setDays] = useState(30);
  const [contentTab, setContentTab] = useState<ContentTab>("pages");

  const [contentData, setContentData] = useState<Record<ContentTab, AnalyticsResponse | null>>({
    pages: null, products: null, applications: null,
  });
  const [sortKey, setSortKey] = useState<SortKey>("views");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── 載入內容流量資料 ───────────────────────────────────────────────────────
  const loadContent = useCallback(async (t: ContentTab, d: number) => {
    setLoading(true); setError(null);
    try {
      const ep = CONTENT_TABS.find(x => x.key === t)!.endpoint;
      const json = await apiClient.get<AnalyticsResponse>(`/${ep}?days=${d}&limit=100`, token);
      setContentData(prev => ({ ...prev, [t]: json }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { loadContent(contentTab, days); }, [loadContent, contentTab, days]);

  const cur = contentData[contentTab];
  const rawRows: PageRow[] = cur ? (cur[contentTab] ?? []) : [];

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === "desc" ? "asc" : "desc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const rows = [...rawRows].sort((a, b) => {
    let av = 0, bv = 0;
    if (sortKey === "views") { av = rowViews(a); bv = rowViews(b); }
    else if (sortKey === "unique_visitors") { av = a.unique_visitors ?? 0; bv = b.unique_visitors ?? 0; }
    else if (sortKey === "spec_downloads") { av = a.spec_downloads ?? 0; bv = b.spec_downloads ?? 0; }
    else if (sortKey === "rfq_count") { av = a.rfq_count ?? 0; bv = b.rfq_count ?? 0; }
    else if (sortKey === "rfq_rate") {
      const va = rowViews(a); const vb = rowViews(b);
      av = va > 0 ? (a.rfq_count ?? 0) / va : 0;
      bv = vb > 0 ? (b.rfq_count ?? 0) / vb : 0;
    }
    return sortDir === "desc" ? bv - av : av - bv;
  });

  const SortIcon = ({ k }: { k: SortKey }) => {
    if (sortKey !== k) return <ChevronsUpDown className="inline h-3 w-3 ml-1 opacity-40" />;
    return sortDir === "desc"
      ? <ChevronDown className="inline h-3 w-3 ml-1" />
      : <ChevronUp className="inline h-3 w-3 ml-1" />;
  };

  return (
    <div>
      {/* ── 標題列 ─────────────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">頁面成效分析</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">各內容類型的流量、訪客與轉換行為統計</p>
        </div>
        <div className="flex items-center gap-2">
          {/* 日期選擇 */}
          <div className="flex rounded-md border overflow-hidden text-sm">
            {DAYS_OPTIONS.map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1.5 transition-colors ${
                  days === d ? "bg-primary text-primary-foreground" : "hover:bg-muted/50 text-muted-foreground"
                }`}
              >
                {d}天
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={() => loadContent(contentTab, days)} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* ── 內容類型 Tabs + 流量表格 ───────────────────────────────────────── */}
      <Card className="mb-6">
        <CardHeader className="pb-0">
          <div className="flex items-center gap-2">
            {CONTENT_TABS.map(t => (
              <button
                key={t.key}
                onClick={() => setContentTab(t.key)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  contentTab === t.key
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted hover:bg-muted/80 text-muted-foreground"
                }`}
              >
                <t.icon className="h-4 w-4" />{t.label}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="p-0 mt-3">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : rows.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">尚無流量資料</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">#</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">內容</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground" onClick={() => handleSort("views")}>瀏覽量<SortIcon k="views" /></th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground" onClick={() => handleSort("unique_visitors")}>不重複訪客<SortIcon k="unique_visitors" /></th>
                  {contentTab === "products" && (
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground" onClick={() => handleSort("spec_downloads")}>規格下載<SortIcon k="spec_downloads" /></th>
                  )}
                  {(contentTab === "products" || contentTab === "applications") && (
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground" onClick={() => handleSort("rfq_count")}>詢價數<SortIcon k="rfq_count" /></th>
                  )}
                  {(contentTab === "products" || contentTab === "applications") && (
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground" onClick={() => handleSort("rfq_rate")}>詢價率<SortIcon k="rfq_rate" /></th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((r, i) => {
                  const subtext = rowSubtext(r, contentTab);
                  const views = rowViews(r);
                  const rfqRate = views > 0
                    ? ((r.rfq_count ?? 0) / views * 100).toFixed(1)
                    : "0.0";
                  return (
                    <tr key={i} className="hover:bg-muted/30">
                      <td className="px-4 py-2 text-muted-foreground">{i + 1}</td>
                      <td className="px-4 py-2">
                        <p className="font-medium">{rowName(r)}</p>
                        {subtext && (
                          <span className="mt-0.5 inline-block rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                            {subtext}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right font-bold">{views.toLocaleString()}</td>
                      <td className="px-4 py-2 text-right">{(r.unique_visitors ?? 0).toLocaleString()}</td>
                      {contentTab === "products" && (
                        <td className="px-4 py-2 text-right text-muted-foreground">{(r.spec_downloads ?? 0).toLocaleString()}</td>
                      )}
                      {(contentTab === "products" || contentTab === "applications") && (
                        <td className="px-4 py-2 text-right text-muted-foreground">{(r.rfq_count ?? 0).toLocaleString()}</td>
                      )}
                      {(contentTab === "products" || contentTab === "applications") && (
                        <td className="px-4 py-2 text-right">
                          <span className={`font-medium ${
                            parseFloat(rfqRate) >= 2 ? "text-green-600" :
                            parseFloat(rfqRate) >= 0.5 ? "text-yellow-600" :
                            "text-muted-foreground"
                          }`}>{rfqRate}%</span>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>


    </div>
  );
}
