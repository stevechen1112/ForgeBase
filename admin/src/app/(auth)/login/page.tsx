"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, AlertCircle, Loader2, Shield } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { clearAuthStorage } from "@/lib/auth/storage";
import { clearPlatformAuthStorage, writePlatformAuthStorage } from "@/lib/auth/platform-storage";
import { authApi } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";

const FEATURES = [
  "產品、應用與文件集中維護",
  "多語外銷網站內容管理",
  "訪客來源與網站旅程觀察",
  "詢價收件、分派與接手管理",
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login({ email, password });
      if (res.user?.is_superuser) {
        clearAuthStorage();
        writePlatformAuthStorage(JSON.stringify(res));
        router.replace("/platform/overview");
        return;
      }
      if (!res.user?.tenant_id) {
        throw new Error("此帳號尚未綁定客戶網站，請聯繫 ForgeBase 管理員");
      }
      clearPlatformAuthStorage();
      login(res);
      router.replace("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "登入失敗，請確認帳號密碼";
      setError(msg.includes("401") || msg.includes("400") ? "帳號或密碼錯誤，請重新輸入" : msg);
    } finally {
      setLoading(false);
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
            FB
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight">ForgeBase</span>
            <span className="ml-2 rounded-md bg-white/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-white/60">
              Admin
            </span>
          </div>
        </div>

        {/* Hero text + stats + features */}
        <div className="relative space-y-8">
          <div className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[hsl(211,100%,70%)]">
              傳產外銷網站管理平台
            </p>
            <h2 className="text-4xl font-light leading-tight text-white">
              讓網站成為全天候的
              <br />
              <span className="font-bold text-[hsl(211,100%,70%)]">外銷詢價入口</span>
            </h2>
            <p className="text-base text-slate-400 leading-relaxed">
              ForgeBase 協助製造業維護多語內容、看懂訪客來源與旅程，並把網站詢價完整交給負責業務；不要求回填線下成交，也不承諾自動帶來訂單。
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
          <p className="text-xs text-slate-600">© 2026 ForgeBase. All rights reserved.</p>
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
              FB
            </div>
            <span className="text-lg font-bold text-slate-900">ForgeBase 管理後台</span>
          </div>

          <Card className="shadow-xl border-0">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-2xl font-bold tracking-tight">歡迎回來</CardTitle>
              <CardDescription>請輸入您的帳號資訊以登入管理後台</CardDescription>
            </CardHeader>

            <CardContent className="space-y-5">
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
                <p className="text-center text-sm text-muted-foreground">需要開通帳號？請聯繫 ForgeBase 管理員。</p>
              </div>
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
