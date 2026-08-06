"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Check, HelpCircle } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PublicNav } from "@/components/public/PublicNav";
import { PublicFooter } from "@/components/public/PublicFooter";

/* ─── Data ─── */

const PLANS = [
  {
    name: "Starter",
    price: 149,
    badge: null,
    desc: "數位型錄 + 詢價入口",
    subtitle: "適合剛起步的外銷製造商，先建立 SEO 基礎與 RFQ 捕捉能力。",
    features: [
      "前台 B2B 官網（英文）",
      "SEO 基礎設施（canonical / sitemap / schema）",
      "RFQ 結構化詢價表單 + 聯絡表單",
      "基礎訪客追蹤（page_view）",
      "SEO Redirect 管理",
      "最多 50 筆產品",
      "2 位管理員帳號",
      "Email 技術支援",
    ],
    excluded: [
      "意圖評分引擎",
      "AI Product Advisor",
      "Dynamic CTA",
      "多語言官網（EN + zh-TW）",
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
    subtitle: "含 Starter 全部功能，加上完整 Capture → Intent → Conversion 鏈路。",
    features: [
      "含 Starter 所有功能",
      "多語言官網（EN + zh-TW，人工維護）",
      "產品／分類／FAQ／應用／認證 CMS",
      "完整行為追蹤（15 種事件）+ 意圖評分",
      "Dynamic CTA — 依意圖自動切換",
      "AI Product Advisor + Chat → RFQ Handoff",
      "GeoIP 訪客國家辨識",
      "即時通知 + 逾時催辦 + RFQ 事件審計",
      "無限產品 & 無限管理員",
      "優先技術支援",
    ],
    excluded: [],
    cta: "免費試用 Professional",
    plan: "professional",
    highlight: true,
  },
];

const FAQ = [
  {
    q: "免費試用期間有什麼限制嗎？",
    a: "14 天免費試用包含所選方案的全部功能，不需信用卡。試用期滿後可選擇付費升級或取消，資料保留 30 天。",
  },
  {
    q: "可以隨時升降方案嗎？",
    a: "可以。從 Starter 升級到 Professional 時，系統會按比例計算差額。降級則在下個計費週期生效。",
  },
  {
    q: "舊網站的資料怎麼搬過來？",
    a: "目前以後台 CMS 手動建立為主：產品、分類、FAQ、應用與認證皆可直接在後台維護；也可上傳圖片／PDF 規格書後掛到商品。若有大量資料需求，可洽詢協助匯入。",
  },
  {
    q: "支援哪些付款方式？",
    a: "目前支援信用卡月付與年付（年付享 2 個月免費）。企業客戶可洽詢銀行匯款方案。",
  },
  {
    q: "有合約期限嗎？",
    a: "沒有。月付方案按月計費，隨時可取消。年付方案享優惠價，承諾 12 個月。",
  },
];

/* ─── Page ─── */

export default function PricingPage() {
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
      <section className="max-w-4xl mx-auto px-6 pt-24 pb-16 text-center">
        <Badge
          variant="outline"
          className="mb-6 text-[hsl(211,100%,45%)] border-[hsl(211,100%,80%)] bg-[hsl(211,100%,97%)] px-3 py-1"
        >
          透明定價
        </Badge>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-slate-900 mb-4 leading-tight">
          選擇符合你
          <span className="text-[hsl(211,100%,50%)]">成長階段</span>的方案
        </h1>
        <p className="text-lg text-slate-500 max-w-xl mx-auto leading-relaxed">
          從數位型錄到 AI 全閉環，所有功能內建、不另外加價。14 天免費試用，不需信用卡。
        </p>
      </section>

      {/* ─── Plans ─── */}
      <section className="max-w-4xl mx-auto px-6 pb-20">
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
                <p className="text-sm font-medium text-slate-700">{plan.desc}</p>
                <div className="pt-2 flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-slate-900">${plan.price}</span>
                  <span className="text-slate-400">/月</span>
                </div>
                <p className="text-sm text-slate-400 mt-2">{plan.subtitle}</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button className="w-full" variant={plan.highlight ? "default" : "outline"} asChild>
                  <Link href={`/register?plan=${plan.plan}`}>
                    {plan.cta} <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                  </Link>
                </Button>
                <ul className="space-y-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-600">
                      <Check className="h-4 w-4 text-[hsl(211,100%,50%)] shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                  {plan.excluded.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-300">
                      <span className="w-4 text-center shrink-0">—</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>

        <p className="text-center text-sm text-slate-400 mt-8">
          年付方案享 2 個月免費 ·{" "}
          <a href="mailto:steve@bace.ai" className="text-[hsl(211,100%,50%)] hover:underline">
            企業客戶洽詢
          </a>
        </p>
      </section>

      {/* ─── FAQ ─── */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-3xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">常見問題</h2>
          </div>
          <div className="space-y-4">
            {FAQ.map(({ q, a }) => (
              <details
                key={q}
                className="group bg-white rounded-xl border border-slate-200 overflow-hidden"
              >
                <summary className="flex items-center gap-3 px-6 py-4 cursor-pointer hover:bg-slate-50 transition-colors">
                  <HelpCircle className="h-4 w-4 text-[hsl(211,100%,50%)] shrink-0" />
                  <span className="font-medium text-slate-900">{q}</span>
                  <ArrowRight className="h-4 w-4 text-slate-400 ml-auto shrink-0 transition-transform group-open:rotate-90" />
                </summary>
                <div className="px-6 pb-4 text-sm text-slate-500 leading-relaxed">{a}</div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="py-16">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">準備好讓官網開始幫你接單了嗎？</h2>
          <Button size="lg" className="h-12 px-8 text-base" asChild>
            <Link href="/register">
              開始 14 天免費試用 <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
