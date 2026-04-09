"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight, BarChart3, Brain, Check, Globe, Users, Zap, FileText, Shield,
} from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Brain,
    title: "AI 意圖評分",
    desc: "自動識別 Hot / Warm / Cold 買家，讓業務優先跟進最有潛力的詢價",
  },
  {
    icon: FileText,
    title: "AI 內容生成",
    desc: "基於 PageBrief 工作流，一鍵產出 SEO 優化的產品頁、應用情境、FAQ",
  },
  {
    icon: BarChart3,
    title: "行銷漏斗分析",
    desc: "完整追蹤 15 種訪客事件，從曝光到詢價的每一步全可視化",
  },
  {
    icon: Globe,
    title: "多語言官網",
    desc: "英文 + 繁體中文同步管理，hreflang 自動產生，打入全球買家市場",
  },
  {
    icon: Zap,
    title: "Dynamic CTA",
    desc: "依訪客意圖階段動態切換行動呼籲，大幅提升詢價轉換率",
  },
  {
    icon: Users,
    title: "RFQ 追蹤管理",
    desc: "結構化詢價收件箱、狀態管理、首次回覆計時，一筆詢價都不漏接",
  },
];

const PLANS = [
  {
    name: "Starter",
    price: 149,
    badge: null,
    desc: "數位型錄 + 詢價入口",
    features: [
      "前台 B2B 官網（英文）",
      "SEO 基礎設施",
      "RFQ 詢價表單",
      "基礎訪客追蹤",
      "50 筆商品",
      "2 位管理員帳號",
      "Email 技術支援",
    ],
    cta: "免費試用 Starter",
    plan: "starter",
    highlight: false,
  },
  {
    name: "Professional",
    price: 699,
    badge: "最受歡迎",
    desc: "意圖識別 + AI 導購 + 全閉環跟進",
    features: [
      "含 Starter 所有功能",
      "多語言（EN + zh-TW）",
      "AI 內容生成（PageBrief）",
      "意圖評分引擎 + 儀表板",
      "Dynamic CTA",
      "AI Product Advisor（Chat）",
      "Chat → RFQ Handoff",
      "無限商品 & 管理員",
      "優先技術支援",
    ],
    cta: "免費試用 Professional",
    plan: "professional",
    highlight: true,
  },
];

export default function LandingPage() {
  const { state } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (state.status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [state.status, router]);

  if (state.status === "loading" || state.status === "authenticated") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-muted-foreground text-sm">載入中…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* ─── Navbar ─── */}
      <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[hsl(211,100%,50%)] flex items-center justify-center text-white font-bold text-sm shadow-sm">
              FB
            </div>
            <span className="font-bold text-lg tracking-tight">ForgeBase</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">登入</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/register">
                免費試用 <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-20 text-center">
        <Badge
          variant="outline"
          className="mb-6 text-[hsl(211,100%,45%)] border-[hsl(211,100%,80%)] bg-[hsl(211,100%,97%)] px-3 py-1"
        >
          專為外銷製造商設計的 SaaS 平台
        </Badge>
        <h1 className="text-5xl font-bold tracking-tight text-slate-900 mb-6 leading-tight">
          讓製造專業
          <br />
          <span className="text-[hsl(211,100%,50%)]">轉化為全球訂單</span>
        </h1>
        <p className="text-xl text-slate-500 max-w-2xl mx-auto mb-10 leading-relaxed">
          ForgeBase 幫外銷製造商建立 AI 驅動的 B2B 官網，
          <br />
          自動識別買家意圖、接住每筆詢價、追蹤業務跟進。
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <Button size="lg" className="h-12 px-8 text-base" asChild>
            <Link href="/register">
              14 天免費試用 <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" className="h-12 px-8 text-base" asChild>
            <Link href="https://mitselect.com" target="_blank" rel="noreferrer">
              查看 Demo 網站
            </Link>
          </Button>
        </div>
        <p className="text-sm text-slate-400 mt-4">免費試用不需信用卡 · 隨時可取消</p>
      </section>

      {/* ─── Features ─── */}
      <section className="bg-slate-50 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">行銷漏斗四階段，全部接住</h2>
            <p className="text-slate-500">從 Google 搜尋到詢價成交，ForgeBase 管理每個關鍵觸點</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <Card key={title} className="border-0 shadow-sm hover:shadow-md transition-shadow">
                <CardContent className="pt-6">
                  <div className="w-10 h-10 rounded-lg bg-[hsl(211,100%,95%)] flex items-center justify-center mb-4">
                    <Icon className="h-5 w-5 text-[hsl(211,100%,50%)]" />
                  </div>
                  <h3 className="font-semibold text-slate-900 mb-2">{title}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Pricing ─── */}
      <section className="py-20" id="pricing">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">透明定價，隨需升級</h2>
            <p className="text-slate-500">從數位型錄到 AI 全閉環，選擇符合你成長階段的方案</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {PLANS.map((plan) => (
              <Card
                key={plan.name}
                className={`relative ${
                  plan.highlight
                    ? "border-[hsl(211,100%,50%)] shadow-lg shadow-blue-100"
                    : "border-slate-200"
                }`}
              >
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-[hsl(211,100%,50%)] text-white px-3 shadow">{plan.badge}</Badge>
                  </div>
                )}
                <CardHeader className="pb-4">
                  <CardTitle className="text-xl">{plan.name}</CardTitle>
                  <p className="text-sm text-slate-500">{plan.desc}</p>
                  <div className="pt-2 flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-slate-900">${plan.price}</span>
                    <span className="text-slate-400">/月</span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Button
                    className="w-full"
                    variant={plan.highlight ? "default" : "outline"}
                    asChild
                  >
                    <Link href={`/register?plan=${plan.plan}`}>{plan.cta}</Link>
                  </Button>
                  <ul className="space-y-2.5">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2.5 text-sm text-slate-600">
                        <Check className="h-4 w-4 text-[hsl(211,100%,50%)] shrink-0 mt-0.5" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-slate-100 py-10">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-[hsl(211,100%,50%)] flex items-center justify-center text-white font-bold text-xs">
              FB
            </div>
            <span className="font-semibold text-slate-800">ForgeBase</span>
          </div>
          <p className="text-sm text-slate-400">© 2026 ForgeBase. 外銷製造商官網成長系統</p>
          <div className="flex items-center gap-4 text-sm">
            <Link href="/login" className="text-slate-400 hover:text-slate-600 transition-colors">
              登入
            </Link>
            <Link href="/register" className="text-slate-400 hover:text-slate-600 transition-colors">
              免費試用
            </Link>
            <div className="flex items-center gap-1.5 text-slate-400">
              <Shield className="h-3 w-3" />
              <span>SSL 加密</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
