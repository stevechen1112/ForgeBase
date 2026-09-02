"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, ChevronRight, FileText, Globe2, Loader2, RefreshCw, WandSparkles } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useAuth } from "@/lib/auth/store";
import { localeCoverageApi, localeDraftApi } from "@/lib/api/content";

type LocaleDefinition = { content_locale: string; route_locale: string; label: string; native_label: string; public_shell_ready: boolean };
type CoverageEntity = { entity: string; source_total: number; translated: number; published: number; draft: number; stale: number; unpaired: number; unpaired_keys: string[]; coverage_pct: number | null; missing_keys: string[]; missing_ids: string[]; missing_count: number };
type Coverage = { source_locale: string; target_locale: string; source_total: number; translated: number; overall_coverage_pct: number | null; missing: number; draft: number; stale: number; unpaired: number; entities: CoverageEntity[] };

const ENTITY_LABELS: Record<string, string> = { products: "主要產品", categories: "產品分類", applications: "應用場景", pages: "基本網站頁面", faqs: "常見問題", comparisons: "產品比較", certifications: "認證與品質證明", capabilities: "工廠能力" };
const ENTITY_PATHS: Record<string, string> = { products: "/dashboard/products", categories: "/dashboard/categories", applications: "/dashboard/applications", pages: "/dashboard/pages", faqs: "/dashboard/faqs", comparisons: "/dashboard/comparisons", certifications: "/dashboard/certifications", capabilities: "/dashboard/capabilities" };
const WORK_GROUPS = [
  { title: "先準備基本網站內容", description: "讓海外買家先看得懂您是誰、做什麼、怎麼聯絡。", entities: ["pages"] },
  { title: "再準備主要產品", description: "把產品與分類補齊，讓買家能找到適合的品項。", entities: ["products", "categories"] },
  { title: "補足買家決策資訊", description: "應用、能力與品質證明，協助買家判斷是否要提出詢價。", entities: ["applications", "capabilities", "certifications"] },
  { title: "最後補齊說明內容", description: "常見問題與產品比較可在需要時再準備。", entities: ["faqs", "comparisons"] },
] as const;
const PRIORITY_ENTITIES = ["pages", "products", "categories", "applications", "capabilities", "certifications", "faqs", "comparisons"];

export default function LocaleOperationsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [locales, setLocales] = useState<LocaleDefinition[]>([]);
  const [sourceLocale, setSourceLocale] = useState("");
  const [targetLocale, setTargetLocale] = useState("");
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [loading, setLoading] = useState(true);
  const [batching, setBatching] = useState<string | null>(null);
  const [draftTarget, setDraftTarget] = useState<CoverageEntity | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const targets = useMemo(() => locales.filter((locale) => locale.content_locale !== sourceLocale), [locales, sourceLocale]);
  const load = useCallback(async (requestedTarget?: string) => {
    if (!token) return;
    setLoading(true); setError(null);
    try {
      const settings = await localeCoverageApi.settings(token);
      const target = requestedTarget || settings.content_locales.find((locale) => locale.content_locale !== settings.source_locale)?.content_locale || "en";
      const nextCoverage = await localeCoverageApi.get(token, target);
      setLocales(settings.content_locales); setSourceLocale(settings.source_locale); setTargetLocale(target); setCoverage(nextCoverage);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "無法載入海外網站語言狀態"); }
    finally { setLoading(false); }
  }, [token]);
  useEffect(() => { void load(); }, [load]);

  async function changeTarget(next: string) { setMessage(null); await load(next); }
  async function createMissingDrafts(row: CoverageEntity) {
    const ids = row.missing_ids.slice(0, 25);
    if (!ids.length || !targetLocale) return;
    setBatching(row.entity); setError(null); setMessage(null);
    try {
      const result = await localeDraftApi.createBatch(token, row.entity, ids, targetLocale);
      const failed = result.failed ? `；${result.failed} 項未建立，原內容未受影響。` : "";
      setMessage(`${ENTITY_LABELS[row.entity] ?? row.entity}已建立 ${result.created_or_updated} 項草稿${failed} 草稿尚未公開。`);
      setDraftTarget(null); await load(targetLocale);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "建立草稿失敗，既有公開內容未變更"); }
    finally { setBatching(null); }
  }

  const sourceDefinition = locales.find((locale) => locale.content_locale === sourceLocale);
  const targetDefinition = locales.find((locale) => locale.content_locale === targetLocale);
  const sourceLabel = sourceDefinition?.native_label || sourceLocale || "載入中";
  const targetLabel = targetDefinition?.native_label || targetLocale || "載入中";
  const rowsByEntity = useMemo(() => new Map(coverage?.entities.map((row) => [row.entity, row]) ?? []), [coverage]);
  const published = coverage?.entities.reduce((sum, row) => sum + row.published, 0) ?? 0;
  const firstMissing = PRIORITY_ENTITIES.map((entity) => rowsByEntity.get(entity)).find((row) => row && row.missing_ids.length > 0) ?? null;
  const firstReview = PRIORITY_ENTITIES.map((entity) => rowsByEntity.get(entity)).find((row) => row && (row.draft > 0 || row.stale > 0)) ?? null;
  const nextStep = !coverage ? null : coverage.draft + coverage.stale > 0
    ? { title: "先確認已準備好的草稿", detail: `目前有 ${coverage.draft + coverage.stale} 項內容等待人工確認；確認後才可上架。`, row: firstReview, action: "開始確認" }
    : coverage.missing > 0
      ? { title: `先準備${ENTITY_LABELS[firstMissing?.entity ?? "pages"] ?? "基本網站頁面"}草稿`, detail: `${targetLabel}尚有 ${coverage.missing} 項內容未準備。先從這一類開始即可；草稿不會自動公開。`, row: firstMissing, action: "準備草稿" }
      : { title: "這個語言版本已準備完成", detail: "沒有尚未建立或等待確認的內容。您可回到內容管理頁查看已上架版本。", row: null, action: "查看內容" };

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><div className="mb-2 flex items-center gap-2 text-sm font-medium text-emerald-700"><Globe2 className="h-4 w-4" />網站與產品準備</div><h1 className="text-2xl font-bold tracking-tight">海外網站語言準備</h1><p className="mt-1 text-sm text-muted-foreground">先選擇要準備的網站語言，再建立草稿、人工確認並上架。草稿不會自動公開。</p></div>
      <Button variant="outline" onClick={() => void load(targetLocale)} disabled={loading}><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button>
    </div>
    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
    {message && <Alert><AlertDescription>{message}</AlertDescription></Alert>}

    <Card className="border-[#b9e1e4] bg-[#f7fbfc]"><CardContent className="p-5"><div className="flex flex-wrap items-end gap-x-5 gap-y-4">
      <div><p className="text-xs font-semibold text-slate-500">網站內容正本</p><p className="mt-1 font-extrabold text-[#10263b]">{sourceLabel}</p><p className="mt-1 text-xs text-slate-500">所有翻譯都以此版本為依據。</p></div>
      <ChevronRight className="mb-3 h-5 w-5 text-[#087b8f]" />
      <div><label className="text-xs font-semibold text-slate-500" htmlFor="target-locale">正在準備的網站語言版本</label><select id="target-locale" className="mt-1 h-10 min-w-56 rounded-md border bg-white px-3 text-sm font-semibold text-[#10263b]" value={targetLocale} onChange={(event) => void changeTarget(event.target.value)} disabled={loading}>{targets.map((locale) => <option key={locale.content_locale} value={locale.content_locale}>{locale.native_label}（{locale.label}）</option>)}</select></div>
      {targetDefinition && <Badge className="mb-2 border border-[#b9e1e4] bg-white text-[#087b8f]">{targetDefinition.public_shell_ready ? "網站介面可顯示此語言" : "網站介面尚待準備"}</Badge>}
    </div></CardContent></Card>

    {loading && !coverage ? <p className="text-sm text-muted-foreground">正在整理這個語言版本的準備狀態…</p> : null}
    {coverage && nextStep && <>
      <section className="grid gap-3 md:grid-cols-4"><Step number="1" title="選擇語言" detail={targetLabel} active /><Step number="2" title="建立草稿" detail={coverage.missing ? `尚有 ${coverage.missing} 項` : "已準備"} active={!coverage.missing} /><Step number="3" title="人工確認" detail={coverage.draft + coverage.stale ? `${coverage.draft + coverage.stale} 項等待確認` : "尚無待確認"} active={coverage.missing === 0 && coverage.draft === 0 && coverage.stale === 0} /><Step number="4" title="上架官網" detail={`目前 ${published} 項已上架`} active={coverage.missing === 0 && coverage.draft === 0 && coverage.stale === 0} /></section>
      <Card className="border-l-4 border-l-[#087b8f]"><CardContent className="flex flex-wrap items-center justify-between gap-4 p-5"><div><p className="text-sm font-semibold text-[#087b8f]">建議下一步</p><h2 className="mt-1 text-lg font-extrabold text-[#10263b]">{nextStep.title}</h2><p className="mt-1 text-sm text-slate-600">{nextStep.detail}</p></div>{nextStep.row ? nextStep.action === "準備草稿" ? <Button onClick={() => setDraftTarget(nextStep.row)} disabled={batching !== null}><WandSparkles className="h-4 w-4" />{nextStep.action}</Button> : <Button asChild><Link href={ENTITY_PATHS[nextStep.row.entity] ?? "/dashboard/content"}>{nextStep.action}<ChevronRight className="h-4 w-4" /></Link></Button> : <Button variant="outline" asChild><Link href="/dashboard/content">{nextStep.action}</Link></Button>}</CardContent></Card>
      <section className="grid gap-3 sm:grid-cols-3"><Metric label="語言準備進度" value={`${coverage.translated}/${coverage.source_total}`} hint={coverage.source_total ? "已有翻譯的內容數" : "尚無可比較的正本內容"} /><Metric label="等待我確認" value={String(coverage.draft + coverage.stale)} hint="確認後才會出現在官網" /><Metric label="目前已上架" value={String(published)} hint="海外買家現在可看到的內容" /></section>
      {coverage.source_total === 0 && <Alert><AlertDescription>目前找不到 {sourceLabel} 正本內容，請先建立正本後再準備其他語言版本。</AlertDescription></Alert>}
      {coverage.unpaired > 0 && <Alert><AlertDescription>有 {coverage.unpaired} 項現有翻譯找不到對應正本，請到相關內容頁確認；其他內容仍可照正常流程處理。</AlertDescription></Alert>}
      <section className="space-y-4"><div><h2 className="text-xl font-extrabold text-[#10263b]">依網站準備順序處理</h2><p className="mt-1 text-sm text-slate-500">先完成買家最先看到的內容，再逐步補足產品與技術資訊。所有內容類型都保留在這裡。</p></div>{WORK_GROUPS.map((group) => { const rows = group.entities.map((entity) => rowsByEntity.get(entity)).filter((row): row is CoverageEntity => Boolean(row)); if (!rows.length) return null; return <Card key={group.title}><CardHeader className="pb-3"><CardTitle>{group.title}</CardTitle><CardDescription>{group.description}</CardDescription></CardHeader><CardContent className="space-y-3">{rows.map((row) => <EntityRow key={row.entity} row={row} onPrepare={() => setDraftTarget(row)} batching={batching === row.entity} />)}</CardContent></Card>; })}</section>
    </>}
    <Dialog open={Boolean(draftTarget)} onOpenChange={(open) => { if (!open && !batching) setDraftTarget(null); }}><DialogContent><DialogHeader><DialogTitle>準備 {targetLabel} 的{draftTarget ? ENTITY_LABELS[draftTarget.entity] : ""}草稿？</DialogTitle><DialogDescription>將建立 {Math.min(draftTarget?.missing_ids.length ?? 0, 25)} 項翻譯草稿。草稿不會自動公開，也不會覆蓋已上架內容。</DialogDescription></DialogHeader>{draftTarget?.missing_keys.length ? <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">本次包含：{draftTarget.missing_keys.slice(0, 8).join("、")}{draftTarget.missing_keys.length > 8 ? "等內容" : ""}</div> : null}<DialogFooter><Button variant="outline" onClick={() => setDraftTarget(null)} disabled={batching !== null}>取消</Button><Button onClick={() => draftTarget && void createMissingDrafts(draftTarget)} disabled={batching !== null}>{batching ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}建立草稿</Button></DialogFooter></DialogContent></Dialog>
  </div>;
}

function Step({ number, title, detail, active }: { number: string; title: string; detail: string; active?: boolean }) { return <Card className={active ? "border-[#8bcfd7] bg-[#f7fbfc]" : ""}><CardContent className="flex items-start gap-3 p-4"><span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-black ${active ? "bg-[#087b8f] text-white" : "bg-slate-100 text-slate-500"}`}>{active ? <CheckCircle2 className="h-4 w-4" /> : number}</span><div><p className="font-bold text-[#10263b]">{title}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></div></CardContent></Card>; }
function Metric({ label, value, hint }: { label: string; value: string; hint: string }) { return <Card><CardContent className="p-4"><p className="text-xs font-semibold text-slate-500">{label}</p><p className="mt-1 text-2xl font-black text-[#10263b]">{value}</p><p className="mt-1 text-xs text-slate-500">{hint}</p></CardContent></Card>; }
function EntityRow({ row, onPrepare, batching }: { row: CoverageEntity; onPrepare: () => void; batching: boolean }) { const label = ENTITY_LABELS[row.entity] ?? row.entity; const hasSource = row.source_total > 0; const reviewCount = row.draft + row.stale; return <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 px-4 py-4"><div className="flex min-w-0 items-start gap-3"><span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#e8f6f7] text-[#087b8f]"><FileText className="h-4 w-4" /></span><div><p className="font-extrabold text-[#10263b]">{label}</p><p className="mt-1 text-sm text-slate-500">{hasSource ? `${row.translated}/${row.source_total} 項已有翻譯；${row.published} 項已上架` : "請先建立內容正本"}</p>{hasSource && <div className="mt-2 flex flex-wrap gap-2 text-xs"><Badge variant="outline">尚未準備 {row.missing_count}</Badge>{reviewCount > 0 && <Badge className="border border-amber-200 bg-amber-50 text-amber-800">等待確認 {reviewCount}</Badge>}{row.unpaired > 0 && <Badge className="border border-slate-200 bg-slate-50 text-slate-600">需配對 {row.unpaired}</Badge>}</div>}</div></div><div className="flex flex-wrap gap-2">{hasSource && row.missing_ids.length > 0 && <Button size="sm" onClick={onPrepare} disabled={batching}><WandSparkles className="h-4 w-4" />準備 {Math.min(row.missing_ids.length, 25)} 項草稿</Button>}<Button size="sm" variant="outline" asChild><Link href={ENTITY_PATHS[row.entity] ?? "/dashboard/content"}>{reviewCount > 0 ? "開始確認" : "查看內容"}</Link></Button></div></div>; }
