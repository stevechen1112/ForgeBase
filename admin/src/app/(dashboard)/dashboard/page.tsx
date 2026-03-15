import {
  TrendingUp, TrendingDown, Users, Package, ClipboardList, DollarSign,
  Globe, Eye, MousePointerClick, Percent, ArrowUpRight,
  RefreshCcw, Download,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const KPI_CARDS = [
  {
    title: "本月詢價 (RFQ)",
    value: "148",
    change: "+23%",
    trend: "up",
    sub: "較上月增加 28 件",
    icon: ClipboardList,
    color: "text-blue-500",
    bg: "bg-blue-50",
  },
  {
    title: "活躍訪客",
    value: "8,432",
    change: "+12%",
    trend: "up",
    sub: "本週日均 1,204",
    icon: Eye,
    color: "text-violet-500",
    bg: "bg-violet-50",
  },
  {
    title: "產品目錄",
    value: "524",
    change: "+8",
    trend: "up",
    sub: "本月新增 8 項商品",
    icon: Package,
    color: "text-emerald-500",
    bg: "bg-emerald-50",
  },
  {
    title: "轉換率",
    value: "3.8%",
    change: "-0.3%",
    trend: "down",
    sub: "RFQ / 訪客比率",
    icon: Percent,
    color: "text-amber-500",
    bg: "bg-amber-50",
  },
  {
    title: "全球買家",
    value: "1,283",
    change: "+156",
    trend: "up",
    sub: "覆蓋 40+ 個國家",
    icon: Globe,
    color: "text-cyan-500",
    bg: "bg-cyan-50",
  },
  {
    title: "估計成交額",
    value: "US$ 2.4M",
    change: "+18%",
    trend: "up",
    sub: "本季詢價估算值",
    icon: DollarSign,
    color: "text-green-500",
    bg: "bg-green-50",
  },
];

const RECENT_RFQS = [
  { id: "RFQ-2026-0148", company: "Bosch GmbH", product: "精密齒輪組 (×500)", country: "🇩🇪 德國", status: "new", time: "5 分鐘前" },
  { id: "RFQ-2026-0147", company: "Siemens AG", product: "液壓缸總成 (×200)", country: "🇩🇪 德國", status: "reviewing", time: "32 分鐘前" },
  { id: "RFQ-2026-0146", company: "Caterpillar Inc.", product: "高強度螺栓 M20 (×10K)", country: "🇺🇸 美國", status: "quoted", time: "2 小時前" },
  { id: "RFQ-2026-0145", company: "Sumitomo Corp.", product: "鋁合金鑄件 (×150)", country: "🇯🇵 日本", status: "new", time: "3 小時前" },
  { id: "RFQ-2026-0144", company: "SKF Group", product: "深溝球軸承 6208 (×2K)", country: "🇸🇪 瑞典", status: "closed", time: "昨天" },
];

const STATUS_CONFIG: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" }> = {
  new:       { label: "新進", variant: "info" },
  reviewing: { label: "審核中", variant: "warning" },
  quoted:    { label: "已報價", variant: "success" },
  closed:    { label: "已結案", variant: "secondary" },
};

const TRAFFIC_SOURCES = [
  { source: "Google Organic", visits: 3420, pct: 41 },
  { source: "直連", visits: 1680, pct: 20 },
  { source: "LinkedIn", visits: 1180, pct: 14 },
  { source: "Email Campaign", visits: 890, pct: 11 },
  { source: "其他", visits: 1262, pct: 15 },
];

const TOP_PRODUCTS = [
  { name: "精密齒輪組", rfqs: 42, trend: "+15%" },
  { name: "液壓缸總成", rfqs: 38, trend: "+8%" },
  { name: "深溝球軸承", rfqs: 31, trend: "+22%" },
  { name: "鋁合金鑄件", rfqs: 27, trend: "-3%" },
  { name: "高強度螺栓", rfqs: 24, trend: "+5%" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* ─── Header ─── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">儀表板</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            歡迎回來！以下是今日的業務摘要。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-2">
            <RefreshCcw className="h-3.5 w-3.5" />
            重新整理
          </Button>
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="h-3.5 w-3.5" />
            匯出報表
          </Button>
        </div>
      </div>

      {/* ─── KPI Grid ─── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {KPI_CARDS.map((kpi) => {
          const Icon = kpi.icon;
          const isUp = kpi.trend === "up";
          return (
            <Card key={kpi.title} className="hover:shadow-card-hover transition-shadow duration-200">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {kpi.title}
                </CardTitle>
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${kpi.bg}`}>
                  <Icon className={`h-4.5 w-4.5 ${kpi.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-end justify-between">
                  <p className="text-2xl font-bold tracking-tight">{kpi.value}</p>
                  <div className={`flex items-center gap-1 text-xs font-medium ${isUp ? "text-emerald-600" : "text-red-500"}`}>
                    {isUp ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                    {kpi.change}
                  </div>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{kpi.sub}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* ─── Main content grid ─── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent RFQs (2/3) */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base">最新詢價單</CardTitle>
              <CardDescription className="text-xs mt-0.5">本月共 148 件，較上月成長 23%</CardDescription>
            </div>
            <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-primary">
              查看全部
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              {RECENT_RFQS.map((rfq) => {
                const cfg = STATUS_CONFIG[rfq.status];
                return (
                  <div key={rfq.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-muted/40 transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-medium text-foreground truncate">{rfq.company}</span>
                        <Badge variant={cfg.variant} className="shrink-0 text-[10px] h-4 px-1.5">{cfg.label}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{rfq.product}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs font-medium">{rfq.country}</p>
                      <p className="text-[11px] text-muted-foreground">{rfq.time}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Right column */}
        <div className="space-y-6">
          {/* Traffic Sources */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">流量來源</CardTitle>
              <CardDescription className="text-xs">本週共 8,432 次訪問</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {TRAFFIC_SOURCES.map((src) => (
                <div key={src.source}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium">{src.source}</span>
                    <span className="text-xs text-muted-foreground">{src.pct}%</span>
                  </div>
                  <Progress value={src.pct} className="h-1.5" />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Top Products */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">熱門商品</CardTitle>
              <CardDescription className="text-xs">依詢價數量排序</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {TOP_PRODUCTS.map((p, i) => (
                <div key={p.name} className="flex items-center gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground shrink-0">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{p.name}</p>
                    <p className="text-[11px] text-muted-foreground">{p.rfqs} 件詢價</p>
                  </div>
                  <span className={`text-xs font-medium shrink-0 ${p.trend.startsWith("+") ? "text-emerald-600" : "text-red-500"}`}>
                    {p.trend}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ─── Quick stats bar ─── */}
      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "平均回應時間", value: "< 2 小時", icon: RefreshCcw },
              { label: "活躍買家國家", value: "40+", icon: Globe },
              { label: "本月新用戶", value: "156", icon: Users },
              { label: "點擊率 (CTR)", value: "4.2%", icon: MousePointerClick },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm font-semibold">{value}</p>
                  <p className="text-[11px] text-muted-foreground">{label}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

