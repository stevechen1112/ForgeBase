import Link from "next/link";
import { Shield } from "lucide-react";

export function PublicFooter() {
  return (
    <footer className="border-t border-slate-100 py-10">
      <div className="max-w-6xl mx-auto px-6">
        {/* Top row */}
        <div className="flex flex-col md:flex-row items-start justify-between gap-10 mb-10">
          {/* Brand */}
          <div className="max-w-xs">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-6 h-6 rounded bg-[hsl(211,100%,50%)] flex items-center justify-center text-white font-bold text-xs">
                FB
              </div>
              <span className="font-semibold text-slate-800">ForgeBase</span>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">
              外銷製造業網站、產品介紹與詢價管理工具。
              <br />
              目前採由團隊協助製作、交付後維護的方式。
            </p>
          </div>

          {/* Link columns */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-8 text-sm">
            <div className="flex flex-col gap-3">
              <p className="font-semibold text-slate-800 mb-1">產品</p>
              <a href="#features" className="text-slate-400 hover:text-slate-600 transition-colors">
                核心功能
              </a>
              <a href="https://pcbrm.tw/apply" className="text-slate-400 hover:text-slate-600 transition-colors">
                申請導入評估
              </a>
              <a
                href="/"
                target="_blank"
                rel="noreferrer"
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                Demo 網站
              </a>
            </div>
            <div className="flex flex-col gap-3">
              <p className="font-semibold text-slate-800 mb-1">說明</p>
              <a href="https://pcbrm.tw/privacy" className="text-slate-400 hover:text-slate-600 transition-colors">資料使用說明</a>
              <a href="https://pcbrm.tw/terms" className="text-slate-400 hover:text-slate-600 transition-colors">產品測試說明</a>
            </div>
            <div className="flex flex-col gap-3">
              <p className="font-semibold text-slate-800 mb-1">帳戶</p>
              <Link href="/login" className="text-slate-400 hover:text-slate-600 transition-colors">
                登入
              </Link>
              <a href="https://pcbrm.tw/apply" className="text-slate-400 hover:text-slate-600 transition-colors">
                申請導入
              </a>
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div className="border-t border-slate-100 pt-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-slate-400">
            © 2026 ForgeBase. All rights reserved.
          </p>
          <div className="flex items-center gap-1.5 text-sm text-slate-400">
            <Shield className="h-3 w-3" />
            <span>SSL 加密</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
