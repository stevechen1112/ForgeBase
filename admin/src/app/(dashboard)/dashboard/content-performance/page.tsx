"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, FileText, Package, LayoutGrid, MousePointerClick, Download, ClipboardList } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

// ── 流量統計資料型別（來自 /tracking/analytics/* ）────────────────────────────
type SummaryRow = { total_events: number; total_pages: number; total_unique_visitors: number };
type PageRow = {
  page_id?: string; page_type?: string; page_name?: string;
  page_views?: number; unique_visitors?: number; spec_downloads?: number;
  rfq_count?: number; avg_intent_score?: number;
  // 舊欄位相容
  slug?: string; title?: string; views?: number; events?: number;
};
type AnalyticsResponse = {
  period_days: number;
  summary?: SummaryRow;
  pages?: PageRow[];
  products?: PageRow[];
  applications?: PageRow[];
};

// ── 轉換漏斗資料型別（來自 /tracking/events/entities ）───────────────────────
type EntityRow = {
  page_type: string; page_id: string; page_url: string;
  page_view: number; rfq_start: number; rfq_submit: number;
  spec_download: number; cta_click: number;
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
function rowPath(r: PageRow) { return r.slug ?? r.page_id ?? ""; }
function rowViews(r: PageRow) { return r.page_views ?? r.views ?? 0; }

export default function ContentPerformancePage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  // ── 狀態 ──────────────────────────────────────────────────────────────────
  const [days, setDays] = useState(30);
  const [contentTab, setContentTab] = useState<ContentTab>("pages");
  const [showFunnel, setShowFunnel] = useState(false);

  const [contentData, setContentData] = useState<Record<ContentTab, AnalyticsResponse | null>>({
    pages: null, products: null, applications: null,
  });
  const [entities, setEntities] = useState<EntityRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [funnelLoading, setFunnelLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── 載入內容流量資料 ───────────────────────────────────────────────────────
  const loadContent = useCallback(async (t: ContentTab, d: number) => {
    setLoading(true); setError(null);
    try {
      const ep = CONTENT_TABS.find(x => x.key === t)!.endpoint;
      const r = await fetch(`${API_BASE}/${ep}?days=${d}&limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await r.json();
      setContentData(prev => ({ ...prev, [t]: json }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [token]);

  // ── 載入轉換漏斗資料 ───────────────────────────────────────────────────────
  const loadEntities = useCallback(async (d: number) => {
    setFunnelLoading(true);
    try {
      const r = await fetch(`${API_BASE}/tracking/events/entities?days=${d}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await r.json();
      setEntities(Array.isArray(json) ? json : []);
    } catch { /* 靜默失敗 */ }
    finally { setFunnelLoading(false); }
  }, [token]);

  useEffect(() => { loadContent(contentTab, days); }, [loadContent, contentTab, days]);
  useEffect(() => { if (showFunnel) loadEntities(days); }, [loadEntities, showFunnel, days]);

  const cur = contentData[contentTab];
  const rows: PageRow[] = cur ? (cur[contentTab] ?? []) : [];

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
          <Button variant="outline" size="sm" onClick={() => { loadContent(contentTab, days); if (showFunnel) loadEntities(days); }} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* ── 摘要卡片 ───────────────────────────────────────────────────────── */}
      {cur?.summary && (
        <div className="mb-6 grid grid-cols-3 gap-4">
          {[
            { label: "涵蓋內容", val: cur.summary.total_pages },
            { label: "唯一訪客", val: cur.summary.total_unique_visitors },
            { label: "總事件數", val: cur.summary.total_events },
          ].map(s => (
            <Card key={s.label}>
              <CardContent className="pb-4 pt-4">
                <p className="text-sm text-muted-foreground">{s.label}</p>
                <p className="mt-1 text-3xl font-bold">{s.val.toLocaleString()}</p>
              </CardContent>
            </Card>
          ))}
        </div>
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
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">瀏覽量</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">唯一訪客</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">規格下載</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">詢價數</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">意圖分</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((r, i) => (
                  <tr key={i} className="hover:bg-muted/30">
                    <td className="px-4 py-2 text-muted-foreground">{i + 1}</td>
                    <td className="px-4 py-2">
                      <p className="font-medium">{rowName(r)}</p>
                      <p className="text-xs text-muted-foreground font-mono">{rowPath(r)}</p>
                    </td>
                    <td className="px-4 py-2 text-right font-bold">{rowViews(r).toLocaleString()}</td>
                    <td className="px-4 py-2 text-right">{(r.unique_visitors ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-2 text-right text-muted-foreground">{(r.spec_downloads ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-2 text-right text-muted-foreground">{(r.rfq_count ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-2 text-right">
                      {r.avg_intent_score != null
                        ? <span className={`font-medium ${r.avg_intent_score >= 60 ? "text-orange-600" : r.avg_intent_score >= 30 ? "text-yellow-600" : "text-muted-foreground"}`}>
                            {r.avg_intent_score}
                          </span>
                        : <span className="text-muted-foreground">—</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* ── 轉換漏斗（實體維度）─────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">產品／應用轉換漏斗</CardTitle>
            <button
              onClick={() => setShowFunnel(v => !v)}
              className="text-xs text-primary hover:underline"
            >
              {showFunnel ? "隱藏" : "展開查看"}
            </button>
          </div>
          {!showFunnel && (
            <p className="text-xs text-muted-foreground mt-0.5">
              每個產品頁的完整行為路徑：瀏覽 → RFQ 開始 → RFQ 送出 → 規格下載 → CTA 點擊
            </p>
          )}
        </CardHeader>
        {showFunnel && (
          <CardContent className="p-0">
            {funnelLoading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">載入中…</p>
            ) : entities.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">尚無轉換資料</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">頁面</th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">類型</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">
                      <span className="inline-flex items-center gap-1"><FileText className="h-3 w-3" />瀏覽</span>
                    </th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">
                      <span className="inline-flex items-center gap-1"><ClipboardList className="h-3 w-3" />RFQ開始</span>
                    </th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">
                      <span className="inline-flex items-center gap-1"><ClipboardList className="h-3 w-3" />RFQ送出</span>
                    </th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">
                      <span className="inline-flex items-center gap-1"><Download className="h-3 w-3" />下載</span>
                    </th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">
                      <span className="inline-flex items-center gap-1"><MousePointerClick className="h-3 w-3" />CTA</span>
                    </th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">RFQ轉換率</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {entities.map((e, i) => {
                    const rfqRate = e.page_view > 0
                      ? ((e.rfq_submit / e.page_view) * 100).toFixed(1)
                      : "0.0";
                    return (
                      <tr key={i} className="hover:bg-muted/30">
                        <td className="px-4 py-2 max-w-[200px]">
                          <p className="truncate text-xs font-mono text-muted-foreground" title={e.page_url}>{e.page_url || e.page_id}</p>
                        </td>
                        <td className="px-4 py-2">
                          <span className="inline-block rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                            {e.page_type ?? "—"}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-right font-bold">{e.page_view.toLocaleString()}</td>
                        <td className="px-4 py-2 text-right text-muted-foreground">{e.rfq_start.toLocaleString()}</td>
                        <td className="px-4 py-2 text-right text-muted-foreground">{e.rfq_submit.toLocaleString()}</td>
                        <td className="px-4 py-2 text-right text-muted-foreground">{e.spec_download.toLocaleString()}</td>
                        <td className="px-4 py-2 text-right text-muted-foreground">{e.cta_click.toLocaleString()}</td>
                        <td className="px-4 py-2 text-right">
                          <span className={`font-medium ${parseFloat(rfqRate) >= 2 ? "text-green-600" : parseFloat(rfqRate) >= 0.5 ? "text-yellow-600" : "text-muted-foreground"}`}>
                            {rfqRate}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
