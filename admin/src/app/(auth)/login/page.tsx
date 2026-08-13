"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, AlertCircle, Loader2, Shield, Zap } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { authApi, type TokenResponse } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";

const FEATURES = [
  "全方位產品目錄管理",
  "多語系詢報價系統",
  "即時業績分析儀表板",
  "客戶關係管理整合",
];

/** Demo-only UI flag. Turn off / remove before public launch. */
const DEMO_QUICK_LOGIN = process.env.NEXT_PUBLIC_DEMO_QUICK_LOGIN === "1";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login({ email, password });
      login(res);
      router.replace("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "登入失敗，請確認帳號密碼";
      setError(msg.includes("401") || msg.includes("400") ? "帳號或密碼錯誤，請重新輸入" : msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleDemoQuickPass() {
    setError("");
    setDemoLoading(true);
    try {
      // basePath=/backend → route is /backend/api/demo-login
      const res = await fetch("/backend/api/demo-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "快速通關失敗，請改用帳密登入"
        );
      }
      login(body as TokenResponse);
      router.replace("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "快速通關失敗";
      setError(msg);
    } finally {
      setDemoLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* ─── Left branding panel ─── */}
      <div className="hidden lg:flex lg:w-[55%] flex-col justify-between bg-[hsl(222,47%,11%)] p-12 text-white relative overflow-hidden">
        {/* Decorative rings */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-[hsl(211,100%,50%)] opacity-5" />
          <div className="absolute -bottom-48 -left-24 h-[500px] w-[500px] rounded-full bg-[hsl(211,100%,50%)] opacity-5" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[700px] w-[700px] rounded-full border border-white/5" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full border border-white/5" />
        </div>

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[hsl(211,100%,50%)] text-sm font-bold shadow-lg">
            NF
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight">NorthForge</span>
            <span className="ml-2 rounded-md bg-white/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-white/60">
              Admin
            </span>
          </div>
        </div>

        {/* Hero text + stats + features */}
        <div className="relative space-y-8">
          <div className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[hsl(211,100%,70%)]">
              製造商全球化管理平台
            </p>
            <h2 className="text-4xl font-light leading-tight text-white">
              將製造專業轉化為
              <br />
              <span className="font-bold text-[hsl(211,100%,70%)]">全球市場成長</span>
            </h2>
            <p className="text-base text-slate-400 leading-relaxed">
              NorthForge 提供完整的 B2B 電商管理工具，讓您的製造業專業知識觸達全球買家。
            </p>
          </div>

          {/* Features */}
          <div className="space-y-2.5">
            {FEATURES.map((feat) => (
              <div key={feat} className="flex items-center gap-3">
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-[hsl(211,100%,50%)]/20">
                  <div className="h-1.5 w-1.5 rounded-full bg-[hsl(211,100%,60%)]" />
                </div>
                <span className="text-sm text-slate-300">{feat}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="relative flex items-center justify-between">
          <p className="text-xs text-slate-600">© 2026 NorthForge. All rights reserved.</p>
          <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <Shield className="h-3 w-3" />
            <span>安全登入</span>
          </div>
        </div>
      </div>

      {/* ─── Right form panel ─── */}
      <div className="flex flex-1 items-center justify-center bg-slate-50 px-6 py-12">
        <div className="w-full max-w-[420px]">
          {/* Mobile logo */}
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[hsl(211,100%,50%)] text-xs font-bold text-white">
              NF
            </div>
            <span className="text-lg font-bold text-slate-900">NorthForge Admin</span>
          </div>

          <Card className="shadow-xl border-0">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-2xl font-bold tracking-tight">歡迎回來</CardTitle>
              <CardDescription>請輸入您的帳號資訊以登入管理後台</CardDescription>
            </CardHeader>

            <CardContent className="space-y-5">
              {DEMO_QUICK_LOGIN && (
                <div className="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <div className="flex items-start gap-2">
                    <Zap className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-amber-900">Demo 快速通關</p>
                      <p className="text-xs text-amber-800/80 leading-relaxed">
                        僅供內部演示使用，一鍵進入後台，免記帳密。對外上線前請關閉此開關。
                      </p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    className="w-full h-11 text-base bg-amber-600 hover:bg-amber-700 text-white"
                    disabled={demoLoading || loading}
                    onClick={handleDemoQuickPass}
                  >
                    {demoLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        進入中…
                      </>
                    ) : (
                      <>
                        <Zap className="mr-2 h-4 w-4" />
                        一鍵進入 Demo 後台
                      </>
                    )}
                  </Button>
                  <Separator />
                  <p className="text-center text-xs text-muted-foreground">或使用帳密登入</p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email */}
                <div className="space-y-2">
                  <Label htmlFor="login-email">電子郵件</Label>
                  <Input
                    id="login-email"
                    type="email"
                    required
                    autoComplete="email"
                    autoFocus
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@forgebase.com"
                    className={error ? "border-destructive focus-visible:ring-destructive" : ""}
                  />
                </div>

                {/* Password */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="login-password">密碼</Label>
                    <button
                      type="button"
                      onClick={() => setShowPw((p) => !p)}
                      className="text-xs text-primary hover:underline underline-offset-2"
                    >
                      {showPw ? "隱藏密碼" : "顯示密碼"}
                    </button>
                  </div>
                  <div className="relative">
                    <Input
                      id="login-password"
                      type={showPw ? "text" : "password"}
                      required
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className={`pr-10 ${error ? "border-destructive focus-visible:ring-destructive" : ""}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw((p) => !p)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      tabIndex={-1}
                      aria-label={showPw ? "隱藏密碼" : "顯示密碼"}
                    >
                      {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* Submit */}
                <Button type="submit" className="w-full h-11 text-base" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      驗證中…
                    </>
                  ) : "登入管理後台"}
                </Button>
              </form>

              <Separator />

              <div className="space-y-3">
                <div className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
                  <Shield className="h-3.5 w-3.5" />
                  <span>僅限授權人員存取。如需協助請聯繫系統管理員。</span>
                </div>
                <p className="text-center text-sm text-muted-foreground">
                  還沒有帳號？{" "}
                  <Link
                    href="/register"
                    className="text-primary font-medium hover:underline underline-offset-2"
                  >
                    立即免費試用 →
                  </Link>
                </p>
              </div>
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
