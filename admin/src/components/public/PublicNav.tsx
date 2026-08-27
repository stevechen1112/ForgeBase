"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

export function PublicNav() {
  return (
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-slate-100">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[hsl(211,100%,50%)] flex items-center justify-center text-white font-bold text-sm shadow-sm">
            FB
          </div>
          <span className="font-bold text-lg tracking-tight">ForgeBase</span>
        </Link>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-8 text-sm text-slate-500">
          <a href="#features" className="hover:text-slate-900 transition-colors">
            功能
          </a>
          <a href="https://pcbrm.tw/apply" className="hover:text-slate-900 transition-colors">
            導入評估
          </a>
          <a
            href="/"
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-900 transition-colors"
          >
            Demo 網站
          </a>
        </div>

        {/* CTA */}
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/login">登入</Link>
          </Button>
          <Button size="sm" asChild>
            <a href="https://pcbrm.tw/apply">
              申請導入 <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </a>
          </Button>
        </div>
      </div>
    </nav>
  );
}
