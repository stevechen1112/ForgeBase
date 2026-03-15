"use client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Flame, TrendingUp, Zap, Eye, Target, RefreshCcw, MousePointerClick, FileText, ClipboardList, Globe, Download, HelpCircle, Scale } from "lucide-react";

const SCORE_RULES = [
  { event: "product_view", label: "商品頁瀏覽", score: 5, icon: Eye, color: "text-blue-500", note: "每次檢視商品頁面" },
  { event: "application_view", label: "應用場景瀏覽", score: 4, icon: Globe, color: "text-indigo-500", note: "每次檢視應用頁面" },
  { event: "spec_download", label: "規格書下載", score: 15, icon: Download, color: "text-green-600", note: "下載 PDF 規格書" },
  { event: "faq_expand", label: "FAQ 展開", score: 3, icon: HelpCircle, color: "text-gray-500", note: "展開任一 FAQ 問答" },
  { event: "comparison_view", label: "比較表查看", score: 8, icon: Scale, color: "text-purple-500", note: "查看競品比較頁" },
  { event: "cta_click", label: "CTA 點擊", score: 10, icon: MousePointerClick, color: "text-orange-500", note: "點擊詢價或下載 CTA" },
  { event: "form_start", label: "表單開始填寫", score: 12, icon: FileText, color: "text-yellow-600", note: "開始填寫非 RFQ 表單" },
  { event: "rfq_start", label: "RFQ 開始填寫", score: 20, icon: ClipboardList, color: "text-red-500", note: "開始填寫詢價表單" },
  { event: "rfq_submit", label: "RFQ 提交", score: 50, icon: Flame, color: "text-red-600 font-bold", note: "成功提交詢價" },
  { event: "return_visit", label: "回訪（24h+）", score: 8, icon: RefreshCcw, color: "text-teal-500", note: "24 小時後再次到訪" },
  { event: "session_depth_5", label: "深度瀏覽≥5頁", score: 10, icon: TrendingUp, color: "text-blue-600", note: "單次 session 瀏覽 5 頁以上" },
];

const STAGES = [
  { stage: "Cold", range: "0–19", color: "bg-gray-100 text-gray-700", desc: "未顯示明確購買意圖", action: "持續曝光，不主動跟進" },
  { stage: "Warm", range: "20–49", color: "bg-yellow-100 text-yellow-800", desc: "有瀏覽行為，輕度意圖", action: "加入再行銷受眾，可發送 nurture" },
  { stage: "Hot", range: "50–99", color: "bg-orange-100 text-orange-800", desc: "高頻瀏覽，強烈購買意圖", action: "發出 Sales Alert，業務主動聯繫" },
  { stage: "Sales-Ready", range: "100+", color: "bg-red-100 text-red-800", desc: "已提交 RFQ 或極高分", action: "高優先 Alert + 立即業務跟進" },
];

const DECAY_RULES = [
  { days: "7 天內", multiplier: "×1.0", desc: "分數完整保留" },
  { days: "8–14 天", multiplier: "×0.8", desc: "分數衰減 20%" },
  { days: "15–30 天", multiplier: "×0.5", desc: "分數衰減 50%" },
  { days: "31–60 天", multiplier: "×0.2", desc: "分數衰減 80%" },
  { days: "60 天以上", multiplier: "×0.0", desc: "分數歸零" },
];

export default function IntentRulesPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">評分規則設定</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">意圖評分系統的行為權重、分數衰減與 Stage 門檻設定</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Score Rules */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4 text-yellow-500" />行為評分規則
            </CardTitle>
            <CardDescription>每個訪客行為對應的意圖分數加分</CardDescription>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">事件</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">說明</th>
                  <th className="px-3 py-2 text-right font-medium text-muted-foreground">加分</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {SCORE_RULES.map(r => (
                  <tr key={r.event} className="hover:bg-muted/30">
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <r.icon className={`h-4 w-4 ${r.color}`} />
                        <span className="font-medium">{r.label}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{r.note}</td>
                    <td className="px-3 py-2 text-right">
                      <Badge className={r.score >= 20 ? "bg-red-100 text-red-700" : r.score >= 10 ? "bg-orange-100 text-orange-700" : "bg-blue-100 text-blue-700"}>
                        +{r.score}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        {/* Intent Stages */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Target className="h-4 w-4 text-primary" />Intent Stage 門檻
            </CardTitle>
            <CardDescription>訪客依累積分數判定的購買意圖階段</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {STAGES.map(s => (
              <div key={s.stage} className={`rounded-lg p-3 ${s.color}`}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{s.stage}</span>
                  <Badge variant="outline" className="font-mono text-xs">{s.range} 分</Badge>
                </div>
                <p className="mt-1 text-xs opacity-80">{s.desc}</p>
                <p className="mt-0.5 text-xs font-medium">→ {s.action}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Decay Rules */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <RefreshCcw className="h-4 w-4 text-muted-foreground" />分數衰減規則
            </CardTitle>
            <CardDescription>閒置時間越長，意圖分數自動衰減（每日批次計算）</CardDescription>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">閒置時間</th>
                  <th className="px-3 py-2 text-center font-medium text-muted-foreground">係數</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">說明</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {DECAY_RULES.map(d => (
                  <tr key={d.days} className="hover:bg-muted/30">
                    <td className="px-3 py-2 font-medium">{d.days}</td>
                    <td className="px-3 py-2 text-center font-mono font-bold">{d.multiplier}</td>
                    <td className="px-3 py-2 text-muted-foreground">{d.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-muted-foreground">
              * 衰減計算於每日 00:00 UTC 批次執行，不影響即時評分
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
