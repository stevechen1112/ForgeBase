import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Check, LockKeyhole, ShieldCheck } from "lucide-react";

export const metadata: Metadata = {
  title: "邀請制帳號開通｜ForgeBase",
  description: "ForgeBase 目前由團隊完成導入與交付後，再為客戶開通管理帳號。",
};

export default function RegisterPage() {
  return (
    <main className="flex min-h-screen bg-slate-50">
      <section className="hidden w-[52%] flex-col justify-between bg-[hsl(222,47%,11%)] p-12 text-white lg:flex">
        <div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[hsl(211,100%,50%)] text-sm font-bold">FB</div><div><strong className="text-xl">ForgeBase</strong><span className="ml-2 rounded bg-white/10 px-2 py-1 text-[10px] uppercase tracking-wider text-white/60">Managed Delivery</span></div></div>
        <div className="max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-[.2em] text-blue-300">Controlled onboarding</p>
          <h1 className="mt-4 text-4xl font-light leading-tight">網站完成導入與確認後，<br /><span className="font-bold text-blue-300">再開通管理帳號。</span></h1>
          <p className="mt-5 leading-relaxed text-slate-400">ForgeBase 目前不是自行註冊後從空白開始建站。團隊會先了解需求、選擇範本、調整網站並完成串接，再依交付範圍建立租戶與使用者權限。</p>
          <ul className="mt-8 space-y-3 text-sm text-slate-300">{["不會自動建立租戶或啟動試用", "價格、時程與實際範圍需另行確認", "交付後可維護被授權的產品與網站內容"].map((item) => <li key={item} className="flex items-start gap-3"><Check className="mt-0.5 h-4 w-4 text-blue-300" />{item}</li>)}</ul>
        </div>
        <p className="text-xs text-slate-600">© 2026 ForgeBase · Product test</p>
      </section>
      <section className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><LockKeyhole className="h-6 w-6" /></div>
          <p className="mt-6 text-xs font-semibold uppercase tracking-[.18em] text-blue-600">Invitation only</p>
          <h2 className="mt-2 text-2xl font-bold text-slate-900">目前不開放自行註冊</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">如果想評估 ForgeBase 是否適合公司目前的網站與詢價流程，請先送出導入評估申請。送出後不代表已受理、開始試用或承諾交付。</p>
          <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-900"><ShieldCheck className="mb-2 h-5 w-5" />既有客戶或測試人員，請使用 ForgeBase 團隊提供的帳號直接登入。</div>
          <div className="mt-7 grid gap-3"><a href="https://pcbrm.tw/apply" className="inline-flex h-11 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90">申請導入評估 <ArrowRight className="ml-2 h-4 w-4" /></a><Link href="/login" className="inline-flex h-11 items-center justify-center rounded-md border px-4 text-sm font-medium hover:bg-slate-50">已有帳號，前往登入</Link></div>
        </div>
      </section>
    </main>
  );
}
