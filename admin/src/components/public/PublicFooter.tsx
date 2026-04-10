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
              專為外銷製造商設計的 RFQ Growth OS。
              <br />
              讓官網不只好看，還能幫你接單。
            </p>
          </div>

          {/* Link columns */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-8 text-sm">
            <div className="flex flex-col gap-3">
              <p className="font-semibold text-slate-800 mb-1">產品</p>
              <a href="#features" className="text-slate-400 hover:text-slate-600 transition-colors">
                核心功能
              </a>
              <a href="#pricing" className="text-slate-400 hover:text-slate-600 transition-colors">
                方案定價
              </a>
              <Link
                href="https://mitselect.com"
                target="_blank"
                rel="noreferrer"
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                Demo 網站
              </Link>
            </div>
            <div className="flex flex-col gap-3">
              <p className="font-semibold text-slate-800 mb-1">公司</p>
              <a href="mailto:steve@bace.ai" className="text-slate-400 hover:text-slate-600 transition-colors">
                聯絡我們
              </a>
              <span className="text-slate-400">八策數位 AI</span>
            </div>
            <div className="flex flex-col gap-3">
              <p className="font-semibold text-slate-800 mb-1">帳戶</p>
              <Link href="/login" className="text-slate-400 hover:text-slate-600 transition-colors">
                登入
              </Link>
              <Link href="/register" className="text-slate-400 hover:text-slate-600 transition-colors">
                免費試用
              </Link>
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div className="border-t border-slate-100 pt-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-slate-400">
            © 2026 ForgeBase by 八策數位 AI. All rights reserved.
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
