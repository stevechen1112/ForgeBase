"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type SiteTemplate } from "@/lib/api/platform-admin";

export default function TemplateLibraryPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [templates, setTemplates] = useState<SiteTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try { setTemplates(await platformAdminApi.siteTemplates(token)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "無法讀取範本庫。"); }
    finally { setLoading(false); }
  }, [token]);
  useEffect(() => { void load(); }, [load]);

  return <div className="space-y-6"><div className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold">範本中心</h1><p className="mt-1 text-sm text-muted-foreground">靜態 Demo 與可正式交付的 CMS 範本必須清楚區分，避免銷售展示被誤當成可直接發布的網站。</p></div><Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button></div>{error && <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}<div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{templates.map((template) => <article key={template.key} className="rounded-xl border bg-card p-5 shadow-sm"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{template.industry}</p><h2 className="mt-1 text-lg font-bold">{template.name}</h2></div>{template.publish_supported ? <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-800"><ShieldCheck className="h-3.5 w-3.5" />可交付</span> : <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800"><TriangleAlert className="h-3.5 w-3.5" />靜態展示</span>}</div><dl className="mt-5 space-y-2 text-sm"><div className="flex justify-between gap-3"><dt className="text-muted-foreground">範本 Key</dt><dd className="font-mono text-xs">{template.key}</dd></div><div className="flex justify-between gap-3"><dt className="text-muted-foreground">CMS Adapter</dt><dd>{template.cms_connected ? "已具備" : "尚未具備"}</dd></div></dl><a href={template.demo_url} target="_blank" rel="noreferrer" className="mt-5 inline-flex items-center gap-1 text-sm text-primary hover:underline">查看範本<ExternalLink className="h-3.5 w-3.5" /></a></article>)}{!loading && !templates.length && <p className="text-sm text-muted-foreground">尚無範本資料。</p>}</div></div>;
}
