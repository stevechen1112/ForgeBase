"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { seoWorkbenchApi, type SEOHealthResponse, type SEOLinksResponse, type SEORevenueResponse } from "@/lib/api/content";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Link2, Search, TrendingUp } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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

export default function SEOAuditPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [health, setHealth] = useState<SEOHealthResponse | null>(null);
  const [links, setLinks] = useState<SEOLinksResponse | null>(null);
  const [revenue, setRevenue] = useState<SEORevenueResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
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

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card><CardContent className="pt-4"><p className="text-sm text-muted-foreground">已追蹤內容</p><p className="mt-1 text-3xl font-semibold">{summary?.total_entities ?? 0}</p></CardContent></Card>
        <Card><CardContent className="pt-4"><p className="text-sm text-muted-foreground">平均 SEO 健康度</p><p className="mt-1 text-3xl font-semibold">{summary?.avg_score ?? 0}</p><Progress className="mt-3" value={summary?.avg_score ?? 0} /></CardContent></Card>
        <Card><CardContent className="pt-4"><p className="text-sm text-muted-foreground">需優先處理</p><p className="mt-1 text-3xl font-semibold text-red-600">{summary?.critical ?? 0}</p></CardContent></Card>
        <Card><CardContent className="pt-4"><p className="text-sm text-muted-foreground">SEO 帶來的 RFQ</p><p className="mt-1 text-3xl font-semibold">{revenue?.summary.total_rfq ?? 0}</p><p className="mt-1 text-xs text-muted-foreground">近 30 天自然內容相關轉換</p></CardContent></Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview"><Search className="mr-2 h-4 w-4" />總覽</TabsTrigger>
          <TabsTrigger value="links"><Link2 className="mr-2 h-4 w-4" />內鏈建議</TabsTrigger>
          <TabsTrigger value="revenue"><TrendingUp className="mr-2 h-4 w-4" />轉換洞察</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-[1.1fr_1.3fr]">
            <Card>
              <CardHeader><CardTitle className="text-base">本週最值得先做的 3 件事</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {health?.tasks.length ? health.tasks.map((task) => (
                  <div key={task.id} className="rounded-md border p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-medium">{task.title}</div>
                        <div className="mt-1 text-sm text-muted-foreground">{task.description}</div>
                      </div>
                      <Badge variant={task.impact === "high" ? "destructive" : "secondary"}>{task.count} 項</Badge>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">影響內容類型：{task.entity_types.join(" / ")}</div>
                  </div>
                )) : <div className="text-sm text-muted-foreground">目前沒有待處理任務。</div>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">需要優先優化的內容</CardTitle></CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>內容</TableHead>
                      <TableHead>類型</TableHead>
                      <TableHead>分數</TableHead>
                      <TableHead>主要問題</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!health?.entities?.length && (
                      <TableRow><TableCell colSpan={4} className="py-6 text-center text-sm text-muted-foreground">尚無已發佈內容可進行診斷</TableCell></TableRow>
                    )}
                    {health?.entities?.map((entity) => (
                      <TableRow key={`${entity.entity_type}-${entity.id}`}>
                        <TableCell>
                          <div className="font-medium">{entity.name}</div>
                          <div className="text-xs text-muted-foreground">{entity.url}</div>
                        </TableCell>
                        <TableCell>{entity.entity_type}</TableCell>
                        <TableCell>
                          <div className="font-medium">{entity.score}</div>
                          <Badge variant={entity.status === "healthy" ? "default" : entity.status === "needs-work" ? "secondary" : "destructive"}>{STATUS_LABEL[entity.status] ?? entity.status}</Badge>
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

        <TabsContent value="links">
          <Card>
            <CardHeader><CardTitle className="text-base">內部連結與內容關聯建議</CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>來源頁面</TableHead>
                    <TableHead>建議連到</TableHead>
                    <TableHead>原因</TableHead>
                    <TableHead>信心</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                    {!links?.suggestions?.length && (
                      <TableRow><TableCell colSpan={4} className="py-6 text-center text-sm text-muted-foreground">尚無內鏈建議（需先建立產品與分類的關聯）</TableCell></TableRow>
                    )}
                  {links?.suggestions?.map((item, index) => (
                    <TableRow key={`${item.source_url}-${item.target_url}-${index}`}>
                      <TableCell>
                        <div className="font-medium">{item.source_name}</div>
                        <div className="text-xs text-muted-foreground">{item.source_type}</div>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium">{item.target_name}</div>
                        <div className="text-xs text-muted-foreground">{item.target_type}</div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{item.reason}</TableCell>
                      <TableCell><Badge variant="outline">{CONFIDENCE_LABEL[item.confidence] ?? item.confidence}</Badge></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="revenue" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card><CardContent className="pt-4"><p className="text-sm text-muted-foreground">總頁面瀏覽</p><p className="mt-1 text-2xl font-semibold">{revenue?.summary.total_views ?? 0}</p></CardContent></Card>
            <Card><CardContent className="pt-4"><p className="text-sm text-muted-foreground">有帶來 RFQ 的頁面</p><p className="mt-1 text-2xl font-semibold">{revenue?.summary.pages_with_rfq ?? 0}</p></CardContent></Card>
            <Card><CardContent className="pt-4"><p className="text-sm text-muted-foreground">平均轉換率</p><p className="mt-1 text-2xl font-semibold">{revenue?.summary.avg_conversion_rate ?? 0}%</p></CardContent></Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">最會帶來 RFQ 的頁面</CardTitle></CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>頁面</TableHead>
                      <TableHead>瀏覽</TableHead>
                      <TableHead>RFQ</TableHead>
                      <TableHead>轉換率</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!revenue?.top_converters?.length && (
                      <TableRow><TableCell colSpan={4} className="py-6 text-center text-sm text-muted-foreground">近 30 天尚無轉換記錄</TableCell></TableRow>
                    )}
                    {revenue?.top_converters?.map((row) => (
                      <TableRow key={`${row.page_type}-${row.page_id}`}>
                        <TableCell>
                          <div className="font-medium">{row.page_name}</div>
                          <div className="text-xs text-muted-foreground">{row.page_type}</div>
                        </TableCell>
                        <TableCell>{row.page_views}</TableCell>
                        <TableCell>{row.rfq_count}</TableCell>
                        <TableCell>{row.conversion_rate}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">高流量但尚未轉換的頁面</CardTitle></CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>頁面</TableHead>
                      <TableHead>瀏覽</TableHead>
                      <TableHead>平均意圖</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!revenue?.underperformers?.length && (
                      <TableRow><TableCell colSpan={3} className="py-6 text-center text-sm text-muted-foreground">尚無高流量未轉換記錄</TableCell></TableRow>
                    )}
                    {revenue?.underperformers?.map((row) => (
                      <TableRow key={`${row.page_type}-${row.page_id}`}>
                        <TableCell>
                          <div className="font-medium">{row.page_name}</div>
                          <div className="text-xs text-muted-foreground">{row.page_type}</div>
                        </TableCell>
                        <TableCell>{row.page_views}</TableCell>
                        <TableCell>{row.avg_intent_score}</TableCell>
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
