"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Search, CheckCircle2, AlertTriangle, XCircle, Globe } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type OnPage = {
  total_published_pages: number;
  ok: number;
  warning: number;
  critical: number;
  no_meta_description: number;
  no_structured_data: number;
  has_canonical: number;
  structured_data_coverage_pct: number;
};

type GSC = {
  total_clicks: number;
  total_impressions: number;
  avg_ctr_pct: number;
  avg_position: number | null;
  opportunity_pages: number;
  days: number;
  data_available: boolean;
};

type SEOSummary = { on_page: OnPage; gsc: GSC };

export default function SEOAuditPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [data, setData] = useState<SEOSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/content/seo-audit/summary`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(setData).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const op = data?.on_page;
  const gsc = data?.gsc;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">SEO 診斷</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">頁面 On-Page SEO 健康度分析與 Google Search Console 整合</p>
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

      {/* On-Page SEO */}
      <h2 className="mb-3 font-semibold">On-Page SEO 總覽</h2>
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-4 flex items-center gap-3">
            <Search className="h-7 w-7 text-primary/60" />
            <div><p className="text-xs text-muted-foreground">已發佈頁面</p><p className="text-2xl font-bold">{op?.total_published_pages ?? 0}</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 flex items-center gap-3">
            <CheckCircle2 className="h-7 w-7 text-green-500" />
            <div><p className="text-xs text-muted-foreground">正常</p><p className="text-2xl font-bold text-green-600">{op?.ok ?? 0}</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 flex items-center gap-3">
            <AlertTriangle className="h-7 w-7 text-yellow-500" />
            <div><p className="text-xs text-muted-foreground">警告</p><p className="text-2xl font-bold text-yellow-600">{op?.warning ?? 0}</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 flex items-center gap-3">
            <XCircle className="h-7 w-7 text-red-500" />
            <div><p className="text-xs text-muted-foreground">嚴重</p><p className="text-2xl font-bold text-red-600">{op?.critical ?? 0}</p></div>
          </CardContent>
        </Card>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">缺少 Meta Description</p>
            <p className="mt-1 text-2xl font-bold">{op?.no_meta_description ?? 0}</p>
            <p className="text-xs text-muted-foreground">頁</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">缺少結構化資料</p>
            <p className="mt-1 text-2xl font-bold">{op?.no_structured_data ?? 0}</p>
            <p className="text-xs text-muted-foreground">頁</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">結構化資料覆蓋率</p>
            <p className="mt-1 text-2xl font-bold">{op?.structured_data_coverage_pct?.toFixed(1) ?? 0}%</p>
            <div className="mt-2 h-2 rounded-full bg-muted">
              <div
                className="h-2 rounded-full bg-primary"
                style={{ width: `${op?.structured_data_coverage_pct ?? 0}%` }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Google Search Console */}
      <h2 className="mb-3 font-semibold">Google Search Console</h2>
      {gsc?.data_available === false ? (
        <Card>
          <CardContent className="flex items-center gap-3 py-6">
            <Globe className="h-8 w-8 text-muted-foreground/40" />
            <div>
              <p className="font-medium text-muted-foreground">GSC 資料尚未連接</p>
              <p className="text-sm text-muted-foreground">
                請在整合設定中配置 Google Search Console API 金鑰，即可獲得點擊率、曝光數與搜尋排名資料。
              </p>
            </div>
            <Badge variant="outline" className="ml-auto">未連接</Badge>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Card><CardContent className="pt-4 pb-4"><p className="text-sm text-muted-foreground">總點擊</p><p className="mt-1 text-2xl font-bold">{gsc?.total_clicks ?? 0}</p></CardContent></Card>
          <Card><CardContent className="pt-4 pb-4"><p className="text-sm text-muted-foreground">曝光數</p><p className="mt-1 text-2xl font-bold">{gsc?.total_impressions ?? 0}</p></CardContent></Card>
          <Card><CardContent className="pt-4 pb-4"><p className="text-sm text-muted-foreground">平均 CTR</p><p className="mt-1 text-2xl font-bold">{gsc?.avg_ctr_pct?.toFixed(2) ?? 0}%</p></CardContent></Card>
          <Card><CardContent className="pt-4 pb-4"><p className="text-sm text-muted-foreground">平均排名</p><p className="mt-1 text-2xl font-bold">{gsc?.avg_position?.toFixed(1) ?? "—"}</p></CardContent></Card>
        </div>
      )}
    </div>
  );
}
