"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight, BarChart3, Brain, Check, Globe, Users, Zap, FileText,
  MessageSquare, Bell, MousePointerClick, Package,
} from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PublicNav } from "@/components/public/PublicNav";
import { PublicFooter } from "@/components/public/PublicFooter";

/* ─── Data ─── */

const FEATURES = [
  {
    icon: Brain,
    title: "買家意圖評分",
    desc: "自動識別 Hot / Warm / Cold 買家，讓業務優先跟進最有潛力的詢價",
  },
  {
    icon: Package,
    title: "商品與內容後台",
    desc: "商品、分類、FAQ、應用、認證可自行維護，官網即時反映",
  },
  {
    icon: BarChart3,
    title: "行銷漏斗分析",
    desc: "完整追蹤訪客事件，從曝光到詢價的每一步全可視化",
  },
  {
    icon: Globe,
    title: "多語言官網",
    desc: "英文 + 繁體中文人工維護，hreflang 自動產生，打入全球買家市場",
  },
  {
    icon: Zap,
    title: "動態行動按鈕",
    desc: "依訪客意圖階段動態切換行動呼籲，大幅提升詢價轉換率",
  },
  {
    icon: Users,
    title: "詢價追蹤管理",
    desc: "結構化詢價收件箱、狀態管理、首次回覆計時，一筆詢價都不漏接",
  },
  {
    icon: MessageSquare,
    title: "官網 AI 導購",
    desc: "在產品頁嵌入 AI 對話，買家問規格、認證、交期，聊到有興趣就導入詢價",
  },
  {
    icon: FileText,
    title: "搜尋引擎基礎",
    desc: "網站地圖、正規網址、結構化資料齊備，讓 Google 找得到你的產品",
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
      "多語言（英文 + 繁中，人工維護）",
      "意圖評分引擎 + 儀表板",
      "動態行動按鈕",
      "官網 AI 導購對話",
      "對話轉詢價",
      "無限商品 & 管理員",
      "優先技術支援",
    ],
    cta: "免費試用 Professional",
    plan: "professional",
    highlight: true,
  },
];

const STEPS = [
  {
    num: 1,
    title: "整理內容",
    desc: "在後台建立商品、分類、FAQ、應用與認證，必要時用外部 AI 協助寫稿後貼上即可",
  },
  {
    num: 2,
    title: "確認上線",
    desc: "在後台看過、改好，按一下就上線。不滿意的先跳過，分批處理不急",
  },
  {
    num: 3,
    title: "開始接單",
    desc: "上線後系統自動開始運作：辨識買家、引導詢價、通知業務。你只要等通知去跟進就好",
  },
];

const PROBLEMS = [
  { icon: Users, label: "不知道誰在看", text: "每天有人來逛網站，但不知道哪些人是真的想買" },
  { icon: Bell, label: "詢價常漏掉", text: "好不容易有人詢價，卻埋在 Email 裡沒人跟" },
  { icon: MousePointerClick, label: "花了錢沒效果", text: "做了網站、買了廣告，但不知道哪些真的有帶來生意" },
  { icon: BarChart3, label: "業務不知道先跟誰", text: "十筆詢價進來，不知道哪筆最有機會成交" },
];

const COMPARE = [
  ["重視頁面好不好看", "重視網站能不能帶來有效詢價"],
  ["報告給你看流量數字", "告訴你哪個買家最可能下單"],
  ["幫你管理網站內容", "幫你把訪客變成詢價單"],
  ["做完交件就結束了", "持續幫你優化，效果越來越好"],
  ["只有好看的網站", "有意圖評分與詢價追蹤，能真正接單"],
  ["業務要自己看報表找客戶", "有認真買家或新詢價，系統主動通知業務"],
];

/* ─── Page ─── */

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
      <PublicNav />

      {/* ─── Hero ─── */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <Badge
              variant="outline"
              className="mb-6 text-[hsl(211,100%,45%)] border-[hsl(211,100%,80%)] bg-[hsl(211,100%,97%)] px-3 py-1"
            >
              專為外銷製造商設計的 SaaS 平台
            </Badge>
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-slate-900 mb-6 leading-tight">
              讓製造專業
              <br />
              <span className="text-[hsl(211,100%,50%)]">轉化為全球訂單</span>
            </h1>
            <p className="text-lg text-slate-500 max-w-lg leading-relaxed mb-8">
              ForgeBase 幫外銷製造商建立 AI 驅動的 B2B 官網，
              自動識別買家意圖、接住每筆詢價、追蹤業務跟進。
            </p>
            <div className="flex items-center gap-4 flex-wrap">
              <Button size="lg" className="h-12 px-8 text-base" asChild>
                <Link href="/register">
                  14 天免費試用 <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" className="h-12 px-8 text-base" asChild>
                <a href="/" target="_blank" rel="noreferrer">
                  查看 Demo 網站
                </a>
              </Button>
            </div>
            <p className="text-sm text-slate-400 mt-4">免費試用不需信用卡 · 隨時可取消</p>
          </div>

          {/* Dashboard preview */}
          <div className="hidden lg:block">
            <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 overflow-hidden shadow-xl relative">
              <img
                src="/backend/sales-page/sales-hero-dashboard-mockup.jpg"
                alt="ForgeBase Dashboard — Visitor Intent Scoring"
                className="w-full h-full object-cover relative z-10"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <BarChart3 className="w-16 h-16 text-slate-200" />
                <p className="text-slate-300 text-xs mt-2">Dashboard Preview</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Problem ─── */}
      <section className="bg-slate-900 py-20">
        <div className="max-w-5xl mx-auto px-6">
          <p className="text-[hsl(211,100%,70%)] text-sm font-semibold tracking-widest uppercase mb-4">
            你是不是也遇到這些問題？
          </p>
          <h2 className="text-3xl font-bold text-white mb-4 leading-tight">
            網站做好了、產品也上架了，
            <br className="hidden sm:block" />
            但詢價單還是寥寥無幾
          </h2>
          <p className="text-slate-400 max-w-2xl mb-12 leading-relaxed">
            你的官網不缺產品頁，也不缺公司介紹。真正缺的是一套能讓來看的人，走到送出詢價那一步的機制。
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {PROBLEMS.map(({ icon: Icon, label, text }) => (
              <div
                key={label}
                className="border border-white/10 rounded-xl p-6 bg-white/5"
              >
                <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-red-400" />
                </div>
                <p className="text-white font-medium">{label}</p>
                <p className="mt-2 text-sm text-slate-400">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Solution 3-step ─── */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <p className="text-[hsl(211,100%,50%)] text-sm font-semibold tracking-widest uppercase mb-3">
              ForgeBase 怎麼解決？
            </p>
            <h2 className="text-3xl font-bold text-slate-900 leading-tight">
              三步讓你的官網
              <br className="hidden sm:block" />
              從「被看看」變成「被詢價」
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {STEPS.map((s) => (
              <Card key={s.num} className="border-0 shadow-sm">
                <CardContent className="pt-6">
                  <div className="w-12 h-12 rounded-xl bg-[hsl(211,100%,95%)] flex items-center justify-center mb-5">
                    <span className="text-xl font-bold text-[hsl(211,100%,50%)]">{s.num}</span>
                  </div>
                  <h3 className="font-bold text-lg text-slate-900 mb-2">{s.title}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{s.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Features ─── */}
      <section className="py-20" id="features">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">
              不只是一個網站，是一整套幫你接單的系統
            </h2>
            <p className="text-slate-500">從 Google 搜尋到詢價成交，ForgeBase 管理每個關鍵觸點</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <Card
                key={title}
                className="border border-slate-100 shadow-sm hover:shadow-md hover:border-blue-200 transition-all duration-300"
              >
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

      {/* ─── AI Advisor Showcase ─── */}
      <section className="py-20 bg-slate-900">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-[hsl(211,100%,70%)] text-sm font-semibold tracking-widest uppercase mb-4">
                AI Product Advisor
              </p>
              <h2 className="text-3xl font-bold text-white leading-tight mb-6">
                買家問問題，
                <br />
                <span className="text-[hsl(211,100%,70%)]">AI 聊到他填詢價單</span>
              </h2>
              <p className="text-slate-400 leading-relaxed mb-8">
                在產品詳頁與 FAQ 頁嵌入情境式 AI 對話。買家用自然語言問規格、認證、交期——AI
                從你的產品資料即時作答，判定購買意圖後自動導向預填好的 RFQ 表單。
              </p>
              <ul className="space-y-3 text-sm text-slate-400">
                <li className="flex items-start gap-3">
                  <span className="text-[hsl(211,100%,70%)] mt-0.5">✦</span> 基於你的產品資料回答，不會亂講
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[hsl(211,100%,70%)] mt-0.5">✦</span> 自動偵測購買意圖，適時引導開單
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-[hsl(211,100%,70%)] mt-0.5">✦</span> 對話紀錄同步至 admin，業務可續接
                </li>
              </ul>
            </div>
            <div className="aspect-video rounded-2xl bg-gradient-to-br from-slate-800 to-slate-700 border border-white/10 overflow-hidden shadow-2xl relative">
              <img
                src="/backend/sales-page/sales-ai-advisor-chat.jpg"
                alt="AI Product Advisor 對話截圖"
                className="w-full h-full object-cover relative z-10"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <MessageSquare className="w-16 h-16 text-white/10" />
                <p className="text-white/20 text-xs mt-2">AI Advisor Preview</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Comparison ─── */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">
              跟一般做網站哪裡不同？
            </h2>
          </div>
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="py-4 px-6 text-sm font-semibold text-slate-500 w-1/2">一般做網站</th>
                  <th className="py-4 px-6 text-sm font-semibold text-[hsl(211,100%,50%)] w-1/2">ForgeBase</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {COMPARE.map(([before, after], i) => (
                  <tr key={i}>
                    <td className="py-4 px-6 text-sm text-slate-400">{before}</td>
                    <td className="py-4 px-6 text-sm text-slate-900 font-medium">{after}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
                    <Badge className="bg-[hsl(211,100%,50%)] text-white px-3 shadow">
                      {plan.badge}
                    </Badge>
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
                  <Button className="w-full" variant={plan.highlight ? "default" : "outline"} asChild>
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

      {/* ─── Final CTA ─── */}
      <section className="py-20 bg-slate-900">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white leading-tight">
            你的官網不缺好看，
            <br className="hidden sm:block" />
            <span className="text-[hsl(211,100%,70%)]">缺的是一套能幫你收到詢價單的機制</span>
          </h2>
          <p className="mt-6 text-lg text-slate-400 leading-relaxed max-w-xl mx-auto">
            不用再花大錢重做網站。ForgeBase 讓你現有的官網就能開始找到買家、收到詢價、通知業務。
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="h-14 px-10 text-lg" asChild>
              <Link href="/register">
                14 天免費試用 <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
          </div>
          <p className="mt-6 text-sm text-slate-400">
            不用付費 · 不用信用卡 · 30 分鐘搞定上線
          </p>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
