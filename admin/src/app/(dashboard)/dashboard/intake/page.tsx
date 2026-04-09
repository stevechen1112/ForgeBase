"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Globe, Loader2, Plus, RefreshCw, ArrowRight, Search, CheckCircle2,
  XCircle, Eye, Zap, FileText, PenLine, Package, FolderOpen,
  HelpCircle, Factory, Trophy, Download,
} from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";

// ── Types ──────────────────────────────────────────────────────────────────

type IntakeProject = {
  id: string;
  project_name: string;
  source_url: string;
  status: string;
  locale: string;
  notes: string | null;
  total_urls_found: number;
  total_entities_extracted: number;
  created_at: string;
  updated_at: string;
};

type IntakeUrlCandidate = {
  id: string;
  project_id: string;
  url: string;
  page_type: string;
  title: string | null;
  meta_description: string | null;
  http_status: number | null;
  content_length: number | null;
  confidence: number | null;
  review_status: string;
  created_at: string;
};

type IntakeEntityCandidate = {
  id: string;
  project_id: string;
  source_url_id: string | null;
  entity_type: string;
  extracted_data: string;
  display_name: string | null;
  confidence: number | null;
  review_status: string;
  committed_entity_id: string | null;
  created_at: string;
};

type IntakeRedirectCandidate = {
  id: string;
  project_id: string;
  from_path: string;
  suggested_to_path: string | null;
  review_status: string;
  created_at: string;
};

type IntakeBriefCandidate = {
  id: string;
  project_id: string;
  entity_candidate_id: string | null;
  target_page_type: string;
  suggested_slug: string | null;
  title_draft: string | null;
  primary_keyword: string | null;
  review_status: string;
  created_at: string;
};

type ProjectSummary = {
  project_id: string;
  status: string;
  total_urls: number;
  urls_by_type: Record<string, number>;
  total_entities: number;
  entities_by_type: Record<string, number>;
  total_redirects: number;
  total_briefs: number;
};

// ── Helpers ────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  created: { label: "已建立", variant: "outline" },
  crawling: { label: "爬取中...", variant: "default" },
  discovered: { label: "已探索", variant: "default" },
  extracting: { label: "抽取中...", variant: "default" },
  ready_for_review: { label: "待審核", variant: "secondary" },
  committed: { label: "已匯入", variant: "default" },
  archived: { label: "已歸檔", variant: "outline" },
};

const PAGE_TYPE_ICONS: Record<string, React.ElementType> = {
  product: Package,
  category: FolderOpen,
  application: Factory,
  faq: HelpCircle,
  certification: Trophy,
  resource: Download,
  company: Globe,
  contact: FileText,
  blog: PenLine,
  unknown: Search,
};

const REVIEW_BADGE: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "待審", variant: "outline" },
  accepted: { label: "✓ 接受", variant: "default" },
  skipped: { label: "跳過", variant: "secondary" },
  merged: { label: "已合併", variant: "default" },
};

function confidencePct(c: number | null): string {
  return c != null ? `${Math.round(c * 100)}%` : "—";
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "剛才";
  if (mins < 60) return `${mins} 分鐘前`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} 小時前`;
  const days = Math.floor(hrs / 24);
  return days === 1 ? "昨天" : `${days} 天前`;
}

function intakeApi<T = unknown>(path: string, token: string, options?: { method?: string; body?: unknown }): Promise<T> {
  const method = options?.method || "GET";
  const intakePath = `/intake${path}`;
  if (method === "POST") return apiClient.post<T>(intakePath, options?.body ?? null, token);
  if (method === "PATCH") return apiClient.patch<T>(intakePath, options?.body ?? null, token);
  return apiClient.get<T>(intakePath, token);
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function IntakePage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  // State
  const [projects, setProjects] = useState<IntakeProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<IntakeProject | null>(null);
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [urls, setUrls] = useState<IntakeUrlCandidate[]>([]);
  const [entities, setEntities] = useState<IntakeEntityCandidate[]>([]);
  const [redirects, setRedirects] = useState<IntakeRedirectCandidate[]>([]);
  const [briefs, setBriefs] = useState<IntakeBriefCandidate[]>([]);

  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newUrl, setNewUrl] = useState("");

  // Entity editing modal
  const [editingEntity, setEditingEntity] = useState<IntakeEntityCandidate | null>(null);
  const [editData, setEditData] = useState<Record<string, unknown>>({});
  const [editDisplayName, setEditDisplayName] = useState("");

  // ── Load projects ──
  const loadProjects = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await intakeApi<IntakeProject[]>("/projects", token);
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "無法載入專案");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  // ── Load project detail ──
  const loadProjectDetail = useCallback(async (project: IntakeProject) => {
    if (!token) return;
    setSelectedProject(project);
    setError(null);
    setSuccess(null);
    try {
      const [sumData, urlData, entData, redData, briData] = await Promise.all([
        intakeApi<ProjectSummary>(`/projects/${project.id}/summary`, token),
        intakeApi<IntakeUrlCandidate[]>(`/projects/${project.id}/urls`, token),
        intakeApi<IntakeEntityCandidate[]>(`/projects/${project.id}/entities`, token),
        intakeApi<IntakeRedirectCandidate[]>(`/projects/${project.id}/redirects`, token),
        intakeApi<IntakeBriefCandidate[]>(`/projects/${project.id}/briefs`, token),
      ]);
      setSummary(sumData);
      setUrls(urlData);
      setEntities(entData);
      setRedirects(redData);
      setBriefs(briData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "無法載入專案明細");
    }
  }, [token]);

  // ── Create project ──
  async function handleCreate() {
    if (!newName.trim() || !newUrl.trim()) return;
    setActionLoading("create");
    setError(null);
    try {
      await intakeApi("/projects", token, {
        method: "POST",
        body: { project_name: newName.trim(), source_url: newUrl.trim() },
      });
      setSuccess("專案已建立！");
      setNewName("");
      setNewUrl("");
      setShowCreate(false);
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "建立失敗");
    } finally {
      setActionLoading(null);
    }
  }

  // ── Trigger discovery ──
  async function handleDiscover() {
    if (!selectedProject) return;
    setActionLoading("discover");
    setError(null);
    try {
      await intakeApi(`/projects/${selectedProject.id}/discover`, token, { method: "POST" });
      setSuccess("網站探索已啟動，請稍後重新整理檢視結果...");
    } catch (err) {
      setError(err instanceof Error ? err.message : "探索失敗");
    } finally {
      setActionLoading(null);
    }
  }

  // ── Trigger extraction ──
  async function handleExtract() {
    if (!selectedProject) return;
    setActionLoading("extract");
    setError(null);
    try {
      await intakeApi(`/projects/${selectedProject.id}/extract`, token, { method: "POST" });
      setSuccess("內容抽取已啟動，請稍後重新整理檢視結果...");
    } catch (err) {
      setError(err instanceof Error ? err.message : "抽取失敗");
    } finally {
      setActionLoading(null);
    }
  }

  // ── Commit ──
  async function handleCommit() {
    if (!selectedProject) return;
    setActionLoading("commit");
    setError(null);
    try {
      const result = await intakeApi<{ committed?: { entities?: number; redirects?: number; briefs?: number } }>(`/projects/${selectedProject.id}/commit`, token, { method: "POST" });
      setSuccess(`匯入完成！實體: ${result.committed?.entities ?? 0}, Redirect: ${result.committed?.redirects ?? 0}, Brief: ${result.committed?.briefs ?? 0}`);
      await loadProjectDetail(selectedProject);
    } catch (err) {
      setError(err instanceof Error ? err.message : "匯入失敗");
    } finally {
      setActionLoading(null);
    }
  }

  // ── Review candidate ──
  async function reviewItem(type: "urls" | "entities" | "redirects" | "briefs", id: string, status: "accepted" | "skipped") {
    if (!selectedProject) return;
    const pathMap = { urls: "urls", entities: "entities", redirects: "redirects", briefs: "briefs" };
    try {
      await intakeApi(`/${pathMap[type]}/${id}/review`, token, {
        method: "PATCH",
        body: { review_status: status },
      });
      await loadProjectDetail(selectedProject);
    } catch (err) {
      setError(err instanceof Error ? err.message : "審核失敗");
    }
  }

  // ── Batch accept all ──
  async function batchAccept(type: "urls" | "entities" | "redirects" | "briefs", items: { id: string; review_status: string }[]) {
    if (!selectedProject) return;
    const pending = items.filter(i => i.review_status === "pending");
    for (const item of pending) {
      await reviewItem(type, item.id, "accepted");
    }
  }

  // ── Entity editing ──
  function openEntityEditor(entity: IntakeEntityCandidate) {
    setEditingEntity(entity);
    setEditDisplayName(entity.display_name || "");
    try {
      setEditData(JSON.parse(entity.extracted_data));
    } catch {
      setEditData({});
    }
  }

  async function saveEntityEdit() {
    if (!editingEntity || !selectedProject) return;
    setActionLoading("edit-entity");
    try {
      await intakeApi(`/entities/${editingEntity.id}/review`, token, {
        method: "PATCH",
        body: {
          review_status: editingEntity.review_status,
          extracted_data: JSON.stringify(editData, null, 2),
        },
      });
      setEditingEntity(null);
      setSuccess("實體資料已更新");
      await loadProjectDetail(selectedProject);
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新失敗");
    } finally {
      setActionLoading(null);
    }
  }

  function updateEditField(key: string, value: unknown) {
    setEditData(prev => ({ ...prev, [key]: value }));
  }

  // ──────────────────────────────────────────────────────────────────────────
  // RENDER
  // ──────────────────────────────────────────────────────────────────────────

  // ── Project list view ──
  if (!selectedProject) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Legacy Site Intake</h1>
            <p className="text-muted-foreground">將舊型錄網站轉為 ForgeBase 結構化內容</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={loadProjects} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              重新整理
            </Button>
            <Button size="sm" onClick={() => setShowCreate(!showCreate)}>
              <Plus className="mr-2 h-4 w-4" />
              新建專案
            </Button>
          </div>
        </div>

        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        {success && <Alert><AlertDescription>{success}</AlertDescription></Alert>}

        {showCreate && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">建立導入專案</CardTitle>
              <CardDescription>輸入目標網站網址，系統將自動探索與分析網站結構</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>專案名稱</Label>
                  <Input
                    placeholder="例如：欣榮貿易官網導入"
                    value={newName}
                    onChange={e => setNewName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>網站網址</Label>
                  <Input
                    placeholder="https://king-a.com.tw"
                    value={newUrl}
                    onChange={e => setNewUrl(e.target.value)}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleCreate}
                  disabled={actionLoading === "create" || !newName.trim() || !newUrl.trim()}
                >
                  {actionLoading === "create" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  建立專案
                </Button>
                <Button variant="outline" onClick={() => setShowCreate(false)}>取消</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Project list */}
        {projects.length === 0 && !loading ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              <Globe className="mx-auto mb-4 h-12 w-12 opacity-50" />
              <p>尚未建立任何導入專案</p>
              <p className="text-sm mt-1">點擊「新建專案」開始導入舊網站</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {projects.map(p => {
              const st = STATUS_LABELS[p.status] || { label: p.status, variant: "outline" as const };
              return (
                <Card key={p.id} className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => loadProjectDetail(p)}>
                  <CardContent className="flex items-center justify-between py-4">
                    <div className="flex items-center gap-4">
                      <Globe className="h-8 w-8 text-muted-foreground" />
                      <div>
                        <h3 className="font-semibold">{p.project_name}</h3>
                        <p className="text-sm text-muted-foreground">{p.source_url}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right text-sm text-muted-foreground">
                        <div>{p.total_urls_found} 頁面 · {p.total_entities_extracted} 實體</div>
                        <div>{relativeTime(p.updated_at)}</div>
                      </div>
                      <Badge variant={st.variant}>{st.label}</Badge>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
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

  // ── Project detail view ──
  const st = STATUS_LABELS[selectedProject.status] || { label: selectedProject.status, variant: "outline" as const };
  const pendingUrls = urls.filter(u => u.review_status === "pending").length;
  const pendingEntities = entities.filter(e => e.review_status === "pending").length;
  const acceptedEntities = entities.filter(e => e.review_status === "accepted").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => { setSelectedProject(null); setSummary(null); }}>
            ← 返回列表
          </Button>
          <div>
            <h1 className="text-xl font-bold">{selectedProject.project_name}</h1>
            <p className="text-sm text-muted-foreground">{selectedProject.source_url}</p>
          </div>
          <Badge variant={st.variant}>{st.label}</Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => loadProjectDetail(selectedProject)}>
            <RefreshCw className="mr-2 h-4 w-4" /> 重新整理
          </Button>
        </div>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {success && <Alert><AlertDescription>{success}</AlertDescription></Alert>}

      {/* Action pipeline */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">導入流程</CardTitle>
          <CardDescription>依序執行：探索 → 審核 URL → 抽取實體 → 審核實體 → 匯入 ForgeBase</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <Button
              onClick={handleDiscover}
              disabled={actionLoading === "discover" || selectedProject.status === "crawling"}
              variant={selectedProject.status === "created" ? "default" : "outline"}
              size="sm"
            >
              {actionLoading === "discover" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              1. 探索網站
            </Button>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <Button
              onClick={handleExtract}
              disabled={actionLoading === "extract" || !["discovered", "ready_for_review"].includes(selectedProject.status)}
              variant={selectedProject.status === "discovered" ? "default" : "outline"}
              size="sm"
            >
              {actionLoading === "extract" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
              2. AI 抽取
            </Button>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <Button
              onClick={handleCommit}
              disabled={actionLoading === "commit" || selectedProject.status !== "ready_for_review" || acceptedEntities === 0}
              variant={selectedProject.status === "ready_for_review" ? "default" : "outline"}
              size="sm"
            >
              {actionLoading === "commit" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
              3. 匯入 ForgeBase
            </Button>
          </div>
          {(selectedProject.status === "crawling" || selectedProject.status === "extracting") && (
            <div className="mt-4">
              <Progress value={undefined} className="h-2" />
              <p className="text-xs text-muted-foreground mt-1">處理中，請稍候後按「重新整理」查看結果...</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{summary.total_urls}</div>
              <div className="text-sm text-muted-foreground">發現頁面</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{summary.total_entities}</div>
              <div className="text-sm text-muted-foreground">抽取實體</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{summary.total_redirects}</div>
              <div className="text-sm text-muted-foreground">Redirect 候選</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{summary.total_briefs}</div>
              <div className="text-sm text-muted-foreground">PageBrief 草稿</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs for Overview / URL / Entity / Redirect / Brief review */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">總覽報告</TabsTrigger>
          <TabsTrigger value="urls">
            頁面 URL ({urls.length})
            {pendingUrls > 0 && <Badge variant="secondary" className="ml-2">{pendingUrls}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="entities">
            實體 ({entities.length})
            {pendingEntities > 0 && <Badge variant="secondary" className="ml-2">{pendingEntities}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="redirects">Redirect ({redirects.length})</TabsTrigger>
          <TabsTrigger value="briefs">PageBrief ({briefs.length})</TabsTrigger>
        </TabsList>

        {/* Overview tab */}
        <TabsContent value="overview" className="space-y-6">
          {summary && (
            <>
              {/* Page type distribution */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">頁面類型分佈</CardTitle>
                  <CardDescription>根據 AI 分類的網站頁面結構</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4">
                    {Object.entries(summary.urls_by_type)
                      .sort(([, a], [, b]) => b - a)
                      .map(([type, count]) => {
                        const Icon = PAGE_TYPE_ICONS[type] || Search;
                        const pct = summary.total_urls > 0 ? Math.round((count / summary.total_urls) * 100) : 0;
                        return (
                          <div key={type} className="flex items-center gap-3 p-3 rounded-lg border">
                            <Icon className="h-5 w-5 text-muted-foreground" />
                            <div className="flex-1">
                              <div className="flex justify-between items-center">
                                <span className="font-medium capitalize">{type}</span>
                                <span className="text-sm text-muted-foreground">{count} 頁 ({pct}%)</span>
                              </div>
                              <Progress value={pct} className="h-1.5 mt-1" />
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </CardContent>
              </Card>

              {/* Entity extraction summary */}
              {summary.total_entities > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">實體抽取結果</CardTitle>
                    <CardDescription>從網站內容中萃取的結構化資料</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      {Object.entries(summary.entities_by_type)
                        .sort(([, a], [, b]) => b - a)
                        .map(([type, count]) => {
                          const Icon = PAGE_TYPE_ICONS[type] || Search;
                          return (
                            <div key={type} className="flex items-center gap-3 p-4 rounded-lg border">
                              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                                <Icon className="h-5 w-5 text-primary" />
                              </div>
                              <div>
                                <div className="text-2xl font-bold">{count}</div>
                                <div className="text-sm text-muted-foreground capitalize">{type}</div>
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Review progress */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">審核進度</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[
                      { label: "URL 頁面", total: urls.length, accepted: urls.filter(u => u.review_status === "accepted").length, skipped: urls.filter(u => u.review_status === "skipped").length },
                      { label: "實體", total: entities.length, accepted: entities.filter(e => e.review_status === "accepted").length, skipped: entities.filter(e => e.review_status === "skipped").length },
                      { label: "Redirect", total: redirects.length, accepted: redirects.filter(r => r.review_status === "accepted").length, skipped: redirects.filter(r => r.review_status === "skipped").length },
                      { label: "PageBrief", total: briefs.length, accepted: briefs.filter(b => b.review_status === "accepted").length, skipped: briefs.filter(b => b.review_status === "skipped").length },
                    ].map(item => {
                      const reviewed = item.accepted + item.skipped;
                      const pct = item.total > 0 ? Math.round((reviewed / item.total) * 100) : 0;
                      return (
                        <div key={item.label} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span>{item.label}</span>
                            <span className="text-muted-foreground">
                              {item.accepted} 已接受 · {item.skipped} 已跳過 · {item.total - reviewed} 待審
                            </span>
                          </div>
                          <Progress value={pct} className="h-2" />
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Quick actions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">建議下一步</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {selectedProject.status === "created" && (
                    <div className="flex items-center gap-3 p-3 rounded-lg border border-primary/30 bg-primary/5">
                      <Search className="h-5 w-5 text-primary" />
                      <div className="flex-1">
                        <div className="font-medium">啟動網站探索</div>
                        <div className="text-sm text-muted-foreground">系統將自動爬取網站、分類頁面並建立 URL 清單</div>
                      </div>
                      <Button size="sm" onClick={handleDiscover} disabled={actionLoading === "discover"}>
                        {actionLoading === "discover" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                        開始探索
                      </Button>
                    </div>
                  )}
                  {selectedProject.status === "discovered" && (
                    <div className="flex items-center gap-3 p-3 rounded-lg border border-primary/30 bg-primary/5">
                      <Zap className="h-5 w-5 text-primary" />
                      <div className="flex-1">
                        <div className="font-medium">啟動 AI 實體抽取</div>
                        <div className="text-sm text-muted-foreground">AI 將從已分類頁面中抽取產品、分類、應用等結構化資料</div>
                      </div>
                      <Button size="sm" onClick={handleExtract} disabled={actionLoading === "extract"}>
                        {actionLoading === "extract" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                        開始抽取
                      </Button>
                    </div>
                  )}
                  {selectedProject.status === "ready_for_review" && acceptedEntities > 0 && (
                    <div className="flex items-center gap-3 p-3 rounded-lg border border-green-500/30 bg-green-50 dark:bg-green-950/20">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      <div className="flex-1">
                        <div className="font-medium">一鍵匯入 ForgeBase</div>
                        <div className="text-sm text-muted-foreground">
                          將 {acceptedEntities} 個已接受的實體、Redirect 與 PageBrief 匯入 ForgeBase
                        </div>
                      </div>
                      <Button size="sm" onClick={handleCommit} disabled={actionLoading === "commit"}>
                        {actionLoading === "commit" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                        匯入 ForgeBase
                      </Button>
                    </div>
                  )}
                  {selectedProject.status === "committed" && (
                    <div className="flex items-center gap-3 p-3 rounded-lg border border-green-500/30 bg-green-50 dark:bg-green-950/20">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      <div className="flex-1">
                        <div className="font-medium">匯入已完成</div>
                        <div className="text-sm text-muted-foreground">所有資料已匯入 ForgeBase，請前往 PageBrief 頁面啟動 AI 內容生成</div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
          {!summary && (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Search className="mx-auto mb-4 h-12 w-12 opacity-50" />
                <p>尚未執行探索，請點擊上方「探索網站」按鈕開始</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* URL tab */}
        <TabsContent value="urls" className="space-y-4">
          {urls.length > 0 && (
            <div className="flex justify-end">
              <Button size="sm" variant="outline" onClick={() => batchAccept("urls", urls)}>
                <CheckCircle2 className="mr-2 h-4 w-4" /> 全部接受
              </Button>
            </div>
          )}
          {/* Type distribution */}
          {summary && Object.keys(summary.urls_by_type).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(summary.urls_by_type).map(([type, count]) => {
                const Icon = PAGE_TYPE_ICONS[type] || Search;
                return (
                  <Badge key={type} variant="outline" className="gap-1 py-1">
                    <Icon className="h-3 w-3" /> {type}: {count}
                  </Badge>
                );
              })}
            </div>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>類型</TableHead>
                <TableHead>URL</TableHead>
                <TableHead>標題</TableHead>
                <TableHead>置信度</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {urls.map(u => {
                const Icon = PAGE_TYPE_ICONS[u.page_type] || Search;
                const rv = REVIEW_BADGE[u.review_status] || { label: u.review_status, variant: "outline" as const };
                return (
                  <TableRow key={u.id}>
                    <TableCell>
                      <Badge variant="outline" className="gap-1">
                        <Icon className="h-3 w-3" /> {u.page_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-xs font-mono">{u.url}</TableCell>
                    <TableCell className="max-w-[200px] truncate">{u.title || "—"}</TableCell>
                    <TableCell>{confidencePct(u.confidence)}</TableCell>
                    <TableCell><Badge variant={rv.variant}>{rv.label}</Badge></TableCell>
                    <TableCell className="text-right">
                      {u.review_status === "pending" && (
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={() => reviewItem("urls", u.id, "accepted")}>
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => reviewItem("urls", u.id, "skipped")}>
                            <XCircle className="h-4 w-4 text-gray-400" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TabsContent>

        {/* Entity tab */}
        <TabsContent value="entities" className="space-y-4">
          {entities.length > 0 && (
            <div className="flex justify-end">
              <Button size="sm" variant="outline" onClick={() => batchAccept("entities", entities)}>
                <CheckCircle2 className="mr-2 h-4 w-4" /> 全部接受
              </Button>
            </div>
          )}
          {summary && Object.keys(summary.entities_by_type).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(summary.entities_by_type).map(([type, count]) => {
                const Icon = PAGE_TYPE_ICONS[type] || Search;
                return (
                  <Badge key={type} variant="outline" className="gap-1 py-1">
                    <Icon className="h-3 w-3" /> {type}: {count}
                  </Badge>
                );
              })}
            </div>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>類型</TableHead>
                <TableHead>名稱</TableHead>
                <TableHead>抽取資料預覽</TableHead>
                <TableHead>置信度</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entities.map(e => {
                const Icon = PAGE_TYPE_ICONS[e.entity_type] || Search;
                const rv = REVIEW_BADGE[e.review_status] || { label: e.review_status, variant: "outline" as const };
                let preview = "";
                try {
                  const data = JSON.parse(e.extracted_data);
                  preview = data.product_name || data.category_name || data.application_name || JSON.stringify(data).slice(0, 80);
                } catch {
                  preview = e.extracted_data?.slice(0, 80) || "";
                }
                return (
                  <TableRow key={e.id}>
                    <TableCell>
                      <Badge variant="outline" className="gap-1">
                        <Icon className="h-3 w-3" /> {e.entity_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{e.display_name || "—"}</TableCell>
                    <TableCell className="max-w-[300px] truncate text-xs text-muted-foreground">{preview}</TableCell>
                    <TableCell>{confidencePct(e.confidence)}</TableCell>
                    <TableCell><Badge variant={rv.variant}>{rv.label}</Badge></TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="ghost" onClick={() => openEntityEditor(e)} title="編輯">
                          <Eye className="h-4 w-4 text-blue-500" />
                        </Button>
                        {e.review_status === "pending" && (
                          <>
                            <Button size="sm" variant="ghost" onClick={() => reviewItem("entities", e.id, "accepted")}>
                              <CheckCircle2 className="h-4 w-4 text-green-600" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => reviewItem("entities", e.id, "skipped")}>
                              <XCircle className="h-4 w-4 text-gray-400" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TabsContent>

        {/* Redirect tab */}
        <TabsContent value="redirects" className="space-y-4">
          {redirects.length > 0 && (
            <div className="flex justify-end">
              <Button size="sm" variant="outline" onClick={() => batchAccept("redirects", redirects)}>
                <CheckCircle2 className="mr-2 h-4 w-4" /> 全部接受
              </Button>
            </div>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>舊路徑</TableHead>
                <TableHead>建議新路徑</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {redirects.map(r => {
                const rv = REVIEW_BADGE[r.review_status] || { label: r.review_status, variant: "outline" as const };
                return (
                  <TableRow key={r.id}>
                    <TableCell className="font-mono text-xs">{r.from_path}</TableCell>
                    <TableCell className="font-mono text-xs">{r.suggested_to_path || "—"}</TableCell>
                    <TableCell><Badge variant={rv.variant}>{rv.label}</Badge></TableCell>
                    <TableCell className="text-right">
                      {r.review_status === "pending" && (
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={() => reviewItem("redirects", r.id, "accepted")}>
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => reviewItem("redirects", r.id, "skipped")}>
                            <XCircle className="h-4 w-4 text-gray-400" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TabsContent>

        {/* Brief tab */}
        <TabsContent value="briefs" className="space-y-4">
          {briefs.length > 0 && (
            <div className="flex justify-end">
              <Button size="sm" variant="outline" onClick={() => batchAccept("briefs", briefs)}>
                <CheckCircle2 className="mr-2 h-4 w-4" /> 全部接受
              </Button>
            </div>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>頁面類型</TableHead>
                <TableHead>標題草稿</TableHead>
                <TableHead>建議 Slug</TableHead>
                <TableHead>主關鍵字</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {briefs.map(b => {
                const rv = REVIEW_BADGE[b.review_status] || { label: b.review_status, variant: "outline" as const };
                return (
                  <TableRow key={b.id}>
                    <TableCell><Badge variant="outline">{b.target_page_type}</Badge></TableCell>
                    <TableCell className="font-medium">{b.title_draft || "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{b.suggested_slug || "—"}</TableCell>
                    <TableCell>{b.primary_keyword || "—"}</TableCell>
                    <TableCell><Badge variant={rv.variant}>{rv.label}</Badge></TableCell>
                    <TableCell className="text-right">
                      {b.review_status === "pending" && (
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={() => reviewItem("briefs", b.id, "accepted")}>
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => reviewItem("briefs", b.id, "skipped")}>
                            <XCircle className="h-4 w-4 text-gray-400" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TabsContent>
      </Tabs>

      {/* Entity Edit Modal */}
      {editingEntity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">編輯實體：{editingEntity.display_name}</CardTitle>
                  <CardDescription>類型：{editingEntity.entity_type} · 置信度：{confidencePct(editingEntity.confidence)}</CardDescription>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setEditingEntity(null)}>
                  <XCircle className="h-5 w-5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Display name */}
              <div className="space-y-2">
                <Label className="font-semibold">顯示名稱</Label>
                <Input
                  value={editDisplayName}
                  onChange={e => setEditDisplayName(e.target.value)}
                />
              </div>

              {/* Dynamic fields from extracted_data */}
              {Object.entries(editData).map(([key, value]) => {
                if (key === "entity_type" || key === "confidence" || key === "display_name") return null;

                const isArray = Array.isArray(value);
                const isObject = typeof value === "object" && value !== null && !isArray;

                return (
                  <div key={key} className="space-y-2">
                    <Label className="font-semibold capitalize">
                      {key.replace(/_/g, " ")}
                    </Label>
                    {isArray || isObject ? (
                      <textarea
                        className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono min-h-[100px]"
                        value={JSON.stringify(value, null, 2)}
                        onChange={e => {
                          try {
                            updateEditField(key, JSON.parse(e.target.value));
                          } catch {
                            // Allow partial edits
                          }
                        }}
                      />
                    ) : (
                      <Input
                        value={String(value ?? "")}
                        onChange={e => updateEditField(key, e.target.value)}
                      />
                    )}
                  </div>
                );
              })}

              {/* Actions */}
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setEditingEntity(null)}>取消</Button>
                <Button variant="outline" onClick={() => { reviewItem("entities", editingEntity.id, "skipped"); setEditingEntity(null); }}>
                  <XCircle className="mr-2 h-4 w-4" /> 跳過此實體
                </Button>
                <Button
                  onClick={async () => { await saveEntityEdit(); reviewItem("entities", editingEntity.id, "accepted"); }}
                  disabled={actionLoading === "edit-entity"}
                >
                  {actionLoading === "edit-entity" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <CheckCircle2 className="mr-2 h-4 w-4" /> 儲存並接受
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
