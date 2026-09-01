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
  unpaired: number;
  unpaired_keys: string[];
  coverage_pct: number | null;
  published_pct: number | null;
  missing_keys: string[];
  missing_ids: string[];
  missing_count: number;
};

type Coverage = {
  source_locale: string;
  target_locale: string;
  source_total: number;
  translated: number;
  overall_coverage_pct: number | null;
  missing: number;
  draft: number;
  stale: number;
  unpaired: number;
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
  const sourceDefinition = locales.find((locale) => locale.content_locale === sourceLocale);
  const sourceLabel = sourceDefinition?.native_label || sourceLocale || "載入中";
  const targetLabel = targetDefinition?.native_label || targetLocale || "載入中";

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
          <CardDescription>先以 {sourceLabel} 維護正本，再逐項確認 {targetLabel} 的翻譯。這一頁是完整度檢查表，不是文章編輯器。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium" htmlFor="target-locale">要檢查的客戶語言</label>
          <select id="target-locale" className="h-9 rounded-md border bg-background px-3 text-sm" value={targetLocale} onChange={(event) => void changeTarget(event.target.value)} disabled={loading}>
            {targets.map((locale) => <option key={locale.content_locale} value={locale.content_locale}>{locale.native_label} ({locale.label})</option>)}
          </select>
          {targetDefinition && (
            <Badge variant={targetDefinition.public_shell_ready ? "default" : "outline"}>
              {targetDefinition.public_shell_ready ? "網站選單與按鈕已支援" : "網站操作介面待補齊"}
            </Badge>
          )}
          <p className="basis-full text-xs text-muted-foreground">介面支援只代表網站選單、按鈕與系統提示可顯示該語言；商品、頁面與規格內容仍須依下方清單逐項確認。</p>
        </CardContent>
      </Card>

      {loading && !coverage ? <p className="text-sm text-muted-foreground">載入中…</p> : null}
      {coverage ? (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <Metric
              label="翻譯完整度"
              value={coverage.overall_coverage_pct === null ? "—" : `${coverage.overall_coverage_pct}%`}
              hint={coverage.source_total ? `${coverage.translated}/${coverage.source_total} 筆已有翻譯` : "沒有正本可供比較"}
            />
            <Metric label="缺少翻譯" value={String(coverage.missing)} hint="尚未建立客戶語言版本" />
            <Metric label="待人工確認" value={String(coverage.draft)} hint="草稿不會自動公開" />
            <Metric label="正本更新後需重審" value={String(coverage.stale)} hint="避免客戶看到舊內容" />
          </div>
          {coverage.source_total === 0 ? (
            <Alert><AlertDescription>目前找不到 {sourceLabel} 正本內容，因此沒有可計算的翻譯完整度。請先到各內容管理頁建立正本；系統不會再把 0/0 誤顯示成 100%。</AlertDescription></Alert>
          ) : null}
          {coverage.unpaired > 0 ? (
            <Alert><AlertDescription>發現 {coverage.unpaired} 筆 {targetLabel} 內容沒有同名正本，暫時無法列入完整度。請到對應內容頁確認識別網址（slug）是否一致。</AlertDescription></Alert>
          ) : null}
          <div className="grid gap-4 lg:grid-cols-2">
            {coverage.entities.map((row) => {
              const label = ENTITY_LABELS[row.entity] ?? row.entity;
              const hasSource = row.source_total > 0;
              return <Card key={row.entity}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div><CardTitle>{label}</CardTitle><CardDescription>{hasSource ? `${row.translated}/${row.source_total} 筆已有翻譯；${row.published} 筆已上架` : `尚無 ${sourceLabel} 正本內容`}</CardDescription></div>
                    <Badge variant="outline">{row.coverage_pct === null ? "無資料" : `${row.coverage_pct}%`}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {hasSource ? <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>缺少 {row.missing_count}</span><span>待確認 {row.draft}</span><span>需重審 {row.stale}</span>
                  </div> : <p className="text-sm text-muted-foreground">先建立正本後，這裡才會顯示缺少、待確認與需重審的數量。</p>}
                  {row.missing_keys.length ? <p className="line-clamp-2 text-xs text-muted-foreground">缺少：{row.missing_keys.slice(0, 8).join("、")}</p> : null}
                  {row.unpaired_keys.length ? <p className="line-clamp-2 text-xs text-amber-700">未配對：{row.unpaired_keys.slice(0, 8).join("、")}</p> : null}
                  <div className="flex flex-wrap gap-2">
                    {hasSource ? <Button size="sm" onClick={() => void createMissingDrafts(row)} disabled={!row.missing_ids.length || batching !== null}>
                      {batching === row.entity ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                      產生缺少草稿{row.missing_ids.length > 25 ? "（前 25 筆）" : ""}
                    </Button> : null}
                    <Button size="sm" variant="outline" asChild><Link href={ENTITY_PATHS[row.entity] ?? "/dashboard/content"}>前往{label}管理</Link></Button>
                  </div>
                </CardContent>
              </Card>
            })}
          </div>
        </>
      ) : null}
    </div>
  );
}

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-semibold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{hint}</p></CardContent></Card>;
}
