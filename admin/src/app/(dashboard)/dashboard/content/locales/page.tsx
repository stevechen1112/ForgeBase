"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Languages, Loader2, RefreshCw, WandSparkles } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth/store";
import { localeCoverageApi, localeDraftApi } from "@/lib/api/content";

type LocaleDefinition = {
  content_locale: string;
  route_locale: string;
  label: string;
  native_label: string;
  public_shell_ready: boolean;
};

type CoverageEntity = {
  entity: string;
  source_total: number;
  translated: number;
  published: number;
  draft: number;
  stale: number;
  coverage_pct: number;
  published_pct: number;
  missing_keys: string[];
  missing_ids: string[];
  missing_count: number;
};

type Coverage = {
  source_locale: string;
  target_locale: string;
  overall_coverage_pct: number;
  missing: number;
  draft: number;
  stale: number;
  entities: CoverageEntity[];
  policy: string;
};

const ENTITY_LABELS: Record<string, string> = {
  products: "商品",
  categories: "分類",
  applications: "應用場景",
  pages: "頁面",
  faqs: "常見問題",
  comparisons: "產品比較",
  certifications: "認證",
  capabilities: "廠能",
};

const ENTITY_PATHS: Record<string, string> = {
  products: "/dashboard/products",
  categories: "/dashboard/categories",
  applications: "/dashboard/applications",
  pages: "/dashboard/pages",
  faqs: "/dashboard/faqs",
  comparisons: "/dashboard/comparisons",
  certifications: "/dashboard/certifications",
  capabilities: "/dashboard/capabilities",
};

export default function LocaleOperationsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [locales, setLocales] = useState<LocaleDefinition[]>([]);
  const [sourceLocale, setSourceLocale] = useState("");
  const [targetLocale, setTargetLocale] = useState("");
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [loading, setLoading] = useState(true);
  const [batching, setBatching] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const targets = useMemo(
    () => locales.filter((locale) => locale.content_locale !== sourceLocale),
    [locales, sourceLocale],
  );

  const load = useCallback(async (requestedTarget?: string) => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const settings = await localeCoverageApi.settings(token);
      const target = requestedTarget
        || settings.content_locales.find((locale) => locale.content_locale !== settings.source_locale)?.content_locale
        || "en";
      const nextCoverage = await localeCoverageApi.get(token, target);
      setLocales(settings.content_locales);
      setSourceLocale(settings.source_locale);
      setTargetLocale(target);
      setCoverage(nextCoverage);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法載入多語內容狀態");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function changeTarget(next: string) {
    setTargetLocale(next);
    setMessage(null);
    await load(next);
  }

  async function createMissingDrafts(row: CoverageEntity) {
    const ids = row.missing_ids.slice(0, 25);
    if (!ids.length || !targetLocale) return;
    setBatching(row.entity);
    setError(null);
    setMessage(null);
    try {
      const result = await localeDraftApi.createBatch(token, row.entity, ids, targetLocale);
      const failureText = result.failed ? `，${result.failed} 筆失敗並保留原狀` : "";
      setMessage(`已建立或更新 ${result.created_or_updated} 筆草稿${failureText}；本次自動發布 0 筆。`);
      await load(targetLocale);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "批次建立草稿失敗");
    } finally {
      setBatching(null);
    }
  }

  const targetDefinition = locales.find((locale) => locale.content_locale === targetLocale);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-emerald-700"><Languages className="h-4 w-4" />客戶語言內容</div>
          <h1 className="text-2xl font-bold tracking-tight">多語內容與草稿審核</h1>
          <p className="mt-1 text-sm text-muted-foreground">以內容正本語言維護資料；AI 只協助起草，仍由人員確認後逐筆上架。</p>
        </div>
        <Button variant="outline" onClick={() => void load(targetLocale)} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {message && <Alert><AlertDescription>{message}</AlertDescription></Alert>}

      <Card>
        <CardHeader>
          <CardTitle>內容正本與客戶語言</CardTitle>
          <CardDescription>目前內容正本語言為 {sourceLocale || "載入中"}。請選擇要檢查的客戶使用語言；網站介面與內容草稿分開管理。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium" htmlFor="target-locale">要檢查的客戶語言</label>
          <select id="target-locale" className="h-9 rounded-md border bg-background px-3 text-sm" value={targetLocale} onChange={(event) => void changeTarget(event.target.value)} disabled={loading}>
            {targets.map((locale) => <option key={locale.content_locale} value={locale.content_locale}>{locale.native_label} ({locale.label})</option>)}
          </select>
          {targetDefinition && (
            <Badge variant={targetDefinition.public_shell_ready ? "default" : "outline"}>
              {targetDefinition.public_shell_ready ? "完整官網介面已就緒" : "內容草稿可用；官網介面包待交付"}
            </Badge>
          )}
        </CardContent>
      </Card>

      {loading && !coverage ? <p className="text-sm text-muted-foreground">載入中…</p> : null}
      {coverage ? (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <Metric label="整體覆蓋" value={`${coverage.overall_coverage_pct}%`} />
            <Metric label="缺少草稿" value={String(coverage.missing)} />
            <Metric label="待審草稿" value={String(coverage.draft)} />
            <Metric label="來源更新後過期" value={String(coverage.stale)} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {coverage.entities.map((row) => (
              <Card key={row.entity}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div><CardTitle>{ENTITY_LABELS[row.entity] ?? row.entity}</CardTitle><CardDescription>{row.translated}/{row.source_total} 已有翻譯版本；{row.published} 已上架</CardDescription></div>
                    <Badge variant="outline">{row.coverage_pct}%</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>缺少 {row.missing_count}</span><span>草稿 {row.draft}</span><span>需更新 {row.stale}</span>
                  </div>
                  {row.missing_keys.length ? <p className="line-clamp-2 text-xs text-muted-foreground">缺少：{row.missing_keys.slice(0, 8).join("、")}</p> : null}
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" onClick={() => void createMissingDrafts(row)} disabled={!row.missing_ids.length || batching !== null}>
                      {batching === row.entity ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                      產生缺少草稿{row.missing_ids.length > 25 ? "（前 25 筆）" : ""}
                    </Button>
                    <Button size="sm" variant="outline" asChild><Link href={ENTITY_PATHS[row.entity] ?? "/dashboard/content"}>開啟內容逐筆審核</Link></Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-semibold">{value}</p></CardContent></Card>;
}
