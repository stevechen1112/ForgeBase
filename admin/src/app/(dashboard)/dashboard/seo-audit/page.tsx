"use client";
import { useEffect, useState, useCallback, useMemo } from "react";
import { useAuth } from "@/lib/auth/store";
import { seoWorkbenchApi, type SEOHealthResponse, type SEOLinksResponse, type SEORevenueResponse } from "@/lib/api/content";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Link2, Search, TrendingUp, CheckCircle2, X, AlertTriangle, Info } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const STATUS_LABEL: Record<string, string> = {
  healthy: "健康",
  "needs-work": "需優化",
  critical: "嚴重問題",
};
const CONFIDENCE_LABEL: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};
const ENTITY_TYPE_LABEL: Record<string, string> = {
  product: "產品",
  page: "頁面",
  capability: "能力",
  application: "應用場景",
  certification: "認證",
  faq: "FAQ",
  comparison: "比較",
};

// 從 entities 資料推導出優先任務（當後端 tasks 為空但有需要優化的內容時）
function deriveTasksFromEntities(entities: SEOHealthResponse["entities"]) {
  const issueGroups: Record<string, { count: number; types: Set<string>; example: string }> = {};
  for (const e of entities) {
    if (e.status === "healthy" || !e.top_issue) continue;
    const key = e.top_issue;
    if (!issueGroups[key]) issueGroups[key] = { count: 0, types: new Set(), example: e.top_issue };
    issueGroups[key].count++;
    issueGroups[key].types.add(ENTITY_TYPE_LABEL[e.entity_type] ?? e.entity_type);
  }
  return Object.entries(issueGroups)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 3)
    .map(([issue, data], i) => ({
      id: `derived-${i}`,
      title: issue,
      description: `共有 ${data.count} 筆內容有此問題，建議逐一修正以提升搜尋排名。`,
      count: data.count,
      impact: data.count >= 5 ? "high" : "medium",
      entity_types: Array.from(data.types),
    }));
}

// 進度條顏色：依分數區間顯示語義顏色
function scoreProgressColor(score: number) {
  if (score >= 90) return "bg-green-500";
  if (score >= 70) return "bg-yellow-400";
  return "bg-red-500";
}

export default function SEOAuditPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [health, setHealth] = useState<SEOHealthResponse | null>(null);
  const [links, setLinks] = useState<SEOLinksResponse | null>(null);
  const [revenue, setRevenue] = useState<SEORevenueResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dismissedLinks, setDismissedLinks] = useState<Set<number>>(new Set());
  const [acceptedLinks, setAcceptedLinks] = useState<Set<number>>(new Set());
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>("all");

  const load = useCallback(() => {
    setLoading(true); setError(null);
    setDismissedLinks(new Set()); setAcceptedLinks(new Set());
    Promise.allSettled([
      seoWorkbenchApi.health(token),
      seoWorkbenchApi.links(token),
      seoWorkbenchApi.revenue(token),
    ])
      .then(([healthResult, linksResult, revenueResult]) => {
        if (healthResult.status === "fulfilled") setHealth(healthResult.value);
        if (linksResult.status === "fulfilled") setLinks(linksResult.value);
        if (revenueResult.status === "fulfilled") setRevenue(revenueResult.value);
        const firstErr = [healthResult, linksResult, revenueResult]
          .find((r): r is PromiseRejectedResult => r.status === "rejected");
        if (firstErr) setError(firstErr.reason?.message ?? "資料載入失敗");
      })
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);
  const summary = health?.summary;
  const avgScore = summary?.avg_score ?? 0;

  // 問題一：當後端 tasks 為空但 entities 有需優化項目時，自動推導任務
  const displayTasks = useMemo(() => {
    if (health?.tasks?.length) return health.tasks;
    if (health?.entities?.length) return deriveTasksFromEntities(health.entities);
    return [];
  }, [health]);

  // 問題六：類型篩選
  const entityTypes = useMemo(() => {
    const types = new Set(health?.entities?.map((e) => e.entity_type) ?? []);
    return Array.from(types);
  }, [health]);

  const filteredEntities = useMemo(() => {
    if (!health?.entities) return [];
    if (entityTypeFilter === "all") return health.entities;
    return health.entities.filter((e) => e.entity_type === entityTypeFilter);
  }, [health, entityTypeFilter]);

  // 問題四：只顯示未被處理的內鏈建議
  const visibleLinks = useMemo(
    () => links?.suggestions?.filter((_, i) => !dismissedLinks.has(i)) ?? [],
    [links, dismissedLinks]
  );

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">SEO 診斷</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">把 SEO 問題翻譯成可執行任務，並直接對照商機結果。</p>
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

      {/* 問題二：0 = 好事用綠色，有問題才紅色；問題五：進度條語義顏色 */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">已追蹤內容</p>
            <p className="mt-1 text-3xl font-semibold">{summary?.total_entities ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">平均 SEO 健康度</p>
            <p className={`mt-1 text-3xl font-semibold ${avgScore >= 90 ? "text-green-600" : avgScore >= 70 ? "text-yellow-600" : "text-red-600"}`}>
              {avgScore}
            </p>
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full transition-all ${scoreProgressColor(avgScore)}`}
                style={{ width: `${avgScore}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {avgScore >= 90 ? "✓ 整體狀況良好" : avgScore >= 70 ? "尚有改善空間" : "需要立即處理"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">需優先處理</p>
            <p className={`mt-1 text-3xl font-semibold ${(summary?.critical ?? 0) > 0 ? "text-red-600" : "text-green-600"}`}>
              {summary?.critical ?? 0}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {(summary?.critical ?? 0) === 0 ? "✓ 目前無嚴重問題" : "嚴重問題待處理"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">SEO 帶來的 RFQ</p>
            <p className="mt-1 text-3xl font-semibold">{revenue?.summary.total_rfq ?? 0}</p>
            <p className="mt-1 text-xs text-muted-foreground">近 30 天自然內容相關轉換</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview"><Search className="mr-2 h-4 w-4" />總覽</TabsTrigger>
          <TabsTrigger value="links">
            <Link2 className="mr-2 h-4 w-4" />內鏈建議
            {visibleLinks.length > 0 && (
              <Badge variant="secondary" className="ml-2 h-4 px-1 text-xs">{visibleLinks.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="revenue"><TrendingUp className="mr-2 h-4 w-4" />轉換洞察</TabsTrigger>
        </TabsList>

        {/* Tab 1：總覽 */}
        <TabsContent value="overview" className="space-y-4">
          {/* 問題八：Layout 調整為左窄右寬，左側任務卡片固定，右側表格彈性 */}
          <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
            <Card className="h-fit">
              <CardHeader>
                <CardTitle className="text-base">本週最值得先做的 3 件事</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {displayTasks.length > 0 ? displayTasks.map((task) => (
                  <div key={task.id} className="rounded-md border p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm leading-snug">{task.title}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{task.description}</div>
                      </div>
                      <Badge
                        variant={task.impact === "high" ? "destructive" : "secondary"}
                        className="shrink-0"
                      >
                        {task.count} 項
                      </Badge>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      影響：{task.entity_types.join(" / ")}
                    </div>
                  </div>
                )) : (
                  <div className="flex flex-col items-center gap-2 py-6 text-center">
                    <CheckCircle2 className="h-8 w-8 text-green-500" />
                    <p className="text-sm font-medium text-green-700">本週無待處理任務</p>
                    <p className="text-xs text-muted-foreground">所有內容 SEO 狀態良好</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              {/* 問題六：類型篩選器 */}
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="text-base">需要優先優化的內容</CardTitle>
                {entityTypes.length > 1 && (
                  <Select value={entityTypeFilter} onValueChange={setEntityTypeFilter}>
                    <SelectTrigger className="h-8 w-32 text-xs">
                      <SelectValue placeholder="全部類型" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部類型</SelectItem>
                      {entityTypes.map((t) => (
                        <SelectItem key={t} value={t}>{ENTITY_TYPE_LABEL[t] ?? t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </CardHeader>
              <CardContent className="pt-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>內容</TableHead>
                      <TableHead className="w-20">類型</TableHead>
                      <TableHead className="w-24">健康度</TableHead>
                      <TableHead>主要問題</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredEntities.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={4} className="py-6 text-center text-sm text-muted-foreground">
                          {health?.entities?.length ? "此類型無待優化內容" : "尚無已發佈內容可進行診斷"}
                        </TableCell>
                      </TableRow>
                    )}
                    {filteredEntities.map((entity) => (
                      <TableRow key={`${entity.entity_type}-${entity.id}`}>
                        <TableCell>
                          <div className="font-medium text-sm">{entity.name}</div>
                          <div className="text-xs text-muted-foreground truncate max-w-xs">{entity.url}</div>
                        </TableCell>
                        <TableCell>
                          <span className="text-xs text-muted-foreground">
                            {ENTITY_TYPE_LABEL[entity.entity_type] ?? entity.entity_type}
                          </span>
                        </TableCell>
                        {/* 問題三：分數與狀態分開顯示 */}
                        <TableCell>
                          <div className={`text-lg font-semibold leading-none ${
                            entity.status === "healthy" ? "text-green-600"
                            : entity.status === "needs-work" ? "text-yellow-600"
                            : "text-red-600"
                          }`}>
                            {entity.score}
                          </div>
                          <Badge
                            variant={entity.status === "healthy" ? "default" : entity.status === "needs-work" ? "secondary" : "destructive"}
                            className="mt-1 text-xs"
                          >
                            {STATUS_LABEL[entity.status] ?? entity.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{entity.top_issue}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab 2：內鏈建議 */}
        <TabsContent value="links" className="space-y-4">
          {/* 問題四：顯示採納/忽略統計 */}
          {(acceptedLinks.size > 0 || dismissedLinks.size > 0) && (
            <div className="flex gap-3 text-sm text-muted-foreground">
              {acceptedLinks.size > 0 && (
                <span className="flex items-center gap-1 text-green-600">
                  <CheckCircle2 className="h-4 w-4" />已採納 {acceptedLinks.size} 條
                </span>
              )}
              {dismissedLinks.size > 0 && (
                <span className="flex items-center gap-1">
                  <X className="h-4 w-4" />已忽略 {dismissedLinks.size} 條
                </span>
              )}
            </div>
          )}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">內部連結與內容關聯建議</CardTitle>
              <p className="text-xs text-muted-foreground mt-1">
                系統根據內容主題相關性自動偵測，建議在來源頁面中加入至目標頁面的連結，有助提升 SEO 爬取效率與訪客瀏覽深度。
              </p>
            </CardHeader>
            <CardContent>
              {visibleLinks.length === 0 ? (
                <div className="py-10 text-center">
                  {links?.suggestions?.length ? (
                    <div className="flex flex-col items-center gap-2">
                      <CheckCircle2 className="h-8 w-8 text-green-500" />
                      <p className="text-sm font-medium">所有建議已處理完畢</p>
                      <Button variant="outline" size="sm" onClick={load} className="mt-2">重新整理建議</Button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                      <Info className="h-8 w-8" />
                      <p className="text-sm font-medium">尚無內鏈建議</p>
                      <p className="text-xs max-w-sm">建議在產品管理中建立產品與分類、應用場景的關聯，系統即可自動生成連結建議。</p>
                    </div>
                  )}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>來源頁面</TableHead>
                      <TableHead>建議連到</TableHead>
                      <TableHead>原因</TableHead>
                      <TableHead className="w-12">信心</TableHead>
                      <TableHead className="w-28 text-right">動作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleLinks.map((item, visibleIndex) => {
                      // 找回原始 index 以正確標記
                      const idx = links!.suggestions!.indexOf(item);
                      const accepted = acceptedLinks.has(idx);
                      return (
                        <TableRow key={`${item.source_url}-${item.target_url}-${visibleIndex}`} className={accepted ? "bg-green-50" : ""}>
                          <TableCell>
                            <div className="font-medium text-sm">{item.source_name}</div>
                            <div className="text-xs text-muted-foreground">{ENTITY_TYPE_LABEL[item.source_type] ?? item.source_type}</div>
                          </TableCell>
                          <TableCell>
                            <div className="font-medium text-sm">{item.target_name}</div>
                            <div className="text-xs text-muted-foreground">{ENTITY_TYPE_LABEL[item.target_type] ?? item.target_type}</div>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground max-w-xs">{item.reason}</TableCell>
                          <TableCell>
                            <Badge variant={item.confidence === "high" ? "default" : "outline"} className="text-xs">
                              {CONFIDENCE_LABEL[item.confidence] ?? item.confidence}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            {accepted ? (
                              <span className="text-xs text-green-600 flex items-center justify-end gap-1">
                                <CheckCircle2 className="h-3.5 w-3.5" />已採納
                              </span>
                            ) : (
                              <div className="flex items-center justify-end gap-1">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 px-2 text-xs text-green-600 hover:text-green-700 hover:bg-green-50"
                                  onClick={() => setAcceptedLinks((prev) => new Set([...prev, idx]))}
                                >
                                  <CheckCircle2 className="mr-1 h-3.5 w-3.5" />採納
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                                  onClick={() => setDismissedLinks((prev) => new Set([...prev, idx]))}
                                >
                                  <X className="h-3.5 w-3.5" />
                                </Button>
                              </div>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3：轉換洞察 */}
        <TabsContent value="revenue" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardContent className="pt-4">
                <p className="text-sm text-muted-foreground">總頁面瀏覽</p>
                <p className="mt-1 text-2xl font-semibold">{revenue?.summary.total_views ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <p className="text-sm text-muted-foreground">有帶來 RFQ 的頁面</p>
                <p className="mt-1 text-2xl font-semibold">{revenue?.summary.pages_with_rfq ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <p className="text-sm text-muted-foreground">平均轉換率</p>
                <p className={`mt-1 text-2xl font-semibold ${(revenue?.summary.avg_conversion_rate ?? 0) > 0 ? "text-green-600" : ""}`}>
                  {revenue?.summary.avg_conversion_rate ?? 0}%
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 問題七：空狀態加說明引導 */}
          {(revenue?.summary.total_views ?? 0) === 0 && (
            <Alert className="border-blue-200 bg-blue-50 text-blue-800">
              <AlertTriangle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-700 text-sm">
                近 30 天尚無流量記錄。可能原因：① 訪客追蹤腳本尚未在前台啟用，② 網站尚未有實際訪客，③ 或造訪事件尚未累積到本系統。
                請確認前台 <code className="bg-blue-100 px-1 rounded">PageViewTracker</code> 元件已正常掛載。
              </AlertDescription>
            </Alert>
          )}

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">最會帶來 RFQ 的頁面</CardTitle>
                <p className="text-xs text-muted-foreground">訪客瀏覽後在 30 天內送出詢價的頁面</p>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>頁面</TableHead>
                      <TableHead className="w-16 text-right">瀏覽</TableHead>
                      <TableHead className="w-16 text-right">RFQ</TableHead>
                      <TableHead className="w-20 text-right">轉換率</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!revenue?.top_converters?.length ? (
                      <TableRow>
                        <TableCell colSpan={4} className="py-8 text-center text-sm text-muted-foreground">
                          近 30 天尚無轉換記錄
                        </TableCell>
                      </TableRow>
                    ) : revenue.top_converters.map((row) => (
                      <TableRow key={`${row.page_type}-${row.page_id}`}>
                        <TableCell>
                          <div className="font-medium text-sm">{row.page_name}</div>
                          <div className="text-xs text-muted-foreground">{ENTITY_TYPE_LABEL[row.page_type] ?? row.page_type}</div>
                        </TableCell>
                        <TableCell className="text-right">{row.page_views}</TableCell>
                        <TableCell className="text-right font-medium text-green-600">{row.rfq_count}</TableCell>
                        <TableCell className="text-right font-medium">{row.conversion_rate}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">高流量但尚未轉換的頁面</CardTitle>
                <p className="text-xs text-muted-foreground">有訪客但未送出詢價，可考慮優化 CTA 或內容深度</p>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>頁面</TableHead>
                      <TableHead className="w-16 text-right">瀏覽</TableHead>
                      <TableHead className="w-20 text-right">平均意圖分</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!revenue?.underperformers?.length ? (
                      <TableRow>
                        <TableCell colSpan={3} className="py-8 text-center text-sm text-muted-foreground">
                          尚無高流量未轉換記錄
                        </TableCell>
                      </TableRow>
                    ) : revenue.underperformers.map((row) => (
                      <TableRow key={`${row.page_type}-${row.page_id}`}>
                        <TableCell>
                          <div className="font-medium text-sm">{row.page_name}</div>
                          <div className="text-xs text-muted-foreground">{ENTITY_TYPE_LABEL[row.page_type] ?? row.page_type}</div>
                        </TableCell>
                        <TableCell className="text-right">{row.page_views}</TableCell>
                        <TableCell className="text-right">
                          <span className={`font-medium ${row.avg_intent_score >= 50 ? "text-yellow-600" : "text-muted-foreground"}`}>
                            {row.avg_intent_score}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
