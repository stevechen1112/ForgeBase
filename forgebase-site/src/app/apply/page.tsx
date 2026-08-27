import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, Check, ShieldCheck } from "lucide-react";

import { ApplicationForm } from "./ApplicationForm";

export const metadata: Metadata = {
  title: "申請導入評估｜ForgeBase",
  description: "提供公司與網站現況，申請 ForgeBase 網站製作與買家成長系統的導入評估。",
  robots: { index: true, follow: true },
};

export default function ApplyPage() {
  return (
    <main className="application-page">
      <header className="site-header application-header">
        <Link href="/" className="wordmark" aria-label="ForgeBase 首頁"><span className="brand-mark" aria-hidden="true">FB</span><span className="wordmark-copy"><strong>ForgeBase</strong><small>MANUFACTURING WEB SYSTEM</small></span></Link>
        <Link href="/" className="login-link"><ArrowLeft size={15} />返回產品介紹</Link>
      </header>

      <section className="application-intro">
        <div className="section-shell application-intro-grid">
          <div>
            <span className="section-code">MANAGED DELIVERY / LIMITED PRODUCT TEST</span>
            <h1>先確認是否適合，<br />再決定要不要往下做。</h1>
            <p>ForgeBase 目前採由團隊協助製作與交付的方式，不是自行註冊後從空白開始建站。這份表單用來了解公司現況與需要，並不代表已接受專案。</p>
          </div>
          <aside>
            <h2>目前可以先確認的事</h2>
            <ul>
              <li><Check size={16} />現有產品與資料是否適合整理成 ForgeBase 網站</li>
              <li><Check size={16} />六套產業範本中是否有可延伸的方向</li>
              <li><Check size={16} />哪些內容可由客戶交付後自行維護</li>
              <li><Check size={16} />詢價收件與內部處理流程是否符合需要</li>
            </ul>
            <div><ShieldCheck size={18} /><p>不承諾固定時程、免費試用、既定價格或自動帶來流量與詢價。</p></div>
          </aside>
        </div>
      </section>

      <section className="application-body section-shell">
        <div className="application-context"><span>申請導入評估</span><h2>請提供目前真實狀況</h2><p>資料越具體，越容易判斷哪些需求已在產品範圍內、哪些需要另行評估。</p></div>
        <ApplicationForm />
      </section>
    </main>
  );
}
