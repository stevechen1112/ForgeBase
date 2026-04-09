"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Eye, EyeOff, AlertCircle, Loader2, Globe, TrendingUp, Rocket,
} from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { authApi } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";

const HIGHLIGHTS = [
  { value: "30 分鐘", label: "完成建站上線", icon: Rocket },
  { value: "AI 驅動", label: "自動生成產品內容", icon: TrendingUp },
  { value: "全球觸達", label: "多語言買家意圖可視", icon: Globe },
];

function RegisterPageInner() {
  const router = useRouter();
  const { state, login } = useAuth();
  const searchParams = useSearchParams();

  const [plan, setPlan] = useState(searchParams.get("plan") ?? "starter");
  const [companyName, setCompanyName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (state.status === "authenticated") router.replace("/dashboard");
  }, [state.status, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!companyName.trim() || !fullName.trim() || !email.trim() || !password) {
      setError("請填寫所有欄位");
      return;
    }
    if (password.length < 8) {
      setError("密碼至少需要 8 個字元");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await authApi.register({ company_name: companyName, full_name: fullName, email, password, plan });
      login({ access_token: res.access_token, refresh_token: res.refresh_token, token_type: res.token_type, user: res.user });
      router.replace("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "建立帳號失敗，請稍後再試";
      if (msg.includes("409") || msg.toLowerCase().includes("already")) {
        setError("此電子郵件已被使用，請直接登入或使用其他信箱");
      } else {
        setError(msg);
      }
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
              Platform
            </span>
          </div>
        </div>

        {/* Hero text + highlights */}
        <div className="relative space-y-8">
          <div className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[hsl(211,100%,70%)]">
              14 天免費，不需信用卡
            </p>
            <h2 className="text-4xl font-light leading-tight text-white">
              建立你的
              <br />
              <span className="font-bold text-[hsl(211,100%,70%)]">AI 外銷官網</span>
            </h2>
            <p className="text-base text-slate-400 leading-relaxed">
              ForgeBase 讓外銷製造商在 30 分鐘內完成建站，
              AI 自動生成內容，意圖評分識別優質買家。
            </p>
          </div>

          {/* Highlights */}
          <div className="grid grid-cols-3 gap-4">
            {HIGHLIGHTS.map(({ value, label, icon: Icon }) => (
              <div key={label} className="rounded-2xl bg-white/5 border border-white/10 p-5 backdrop-blur-sm">
                <Icon className="h-5 w-5 text-[hsl(211,100%,60%)] mb-3" />
                <p className="text-2xl font-bold text-white">{value}</p>
                <p className="mt-1 text-xs text-slate-400">{label}</p>
              </div>
            ))}
          </div>

          {/* What you get */}
          <div className="space-y-2.5">
            {[
              "B2B 官網 + 多語言支援",
              "AI 意圖評分引擎",
              "RFQ 詢價管理系統",
              "行銷漏斗儀表板",
            ].map((feat) => (
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
        <div className="relative">
          <p className="text-xs text-slate-600">© 2026 ForgeBase. 外銷製造商官網成長系統</p>
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
            <span className="text-lg font-bold text-slate-900">ForgeBase</span>
          </div>

          <Card className="shadow-xl border-0">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-2xl font-bold tracking-tight">建立帳號</CardTitle>
              <CardDescription>填寫資料開始 14 天免費試用</CardDescription>
            </CardHeader>

            <CardContent className="space-y-5">
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Company name */}
                <div className="space-y-2">
                  <Label htmlFor="reg-company">公司名稱</Label>
                  <Input
                    id="reg-company"
                    type="text"
                    required
                    autoFocus
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="例：台灣精密工業有限公司"
                  />
                </div>

                {/* Full name */}
                <div className="space-y-2">
                  <Label htmlFor="reg-name">姓名</Label>
                  <Input
                    id="reg-name"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="例：王大明"
                  />
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <Label htmlFor="reg-email">電子郵件</Label>
                  <Input
                    id="reg-email"
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                  />
                </div>

                {/* Password */}
                <div className="space-y-2">
                  <Label htmlFor="reg-password">密碼</Label>
                  <div className="relative">
                    <Input
                      id="reg-password"
                      type={showPw ? "text" : "password"}
                      required
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="至少 8 個字元"
                      className="pr-10"
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

                {/* Plan selector */}
                <div className="space-y-2">
                  <Label>選擇方案</Label>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { value: "starter", label: "Starter", price: "$149/月" },
                      { value: "professional", label: "Professional", price: "$699/月" },
                    ].map((p) => (
                      <button
                        key={p.value}
                        type="button"
                        onClick={() => setPlan(p.value)}
                        className={`rounded-lg border-2 p-3 text-left transition-all ${
                          plan === p.value
                            ? "border-[hsl(211,100%,50%)] bg-[hsl(211,100%,97%)]"
                            : "border-slate-200 hover:border-slate-300 bg-white"
                        }`}
                      >
                        <div className="text-sm font-semibold text-slate-900">{p.label}</div>
                        <div className="text-xs text-slate-500 mt-0.5">{p.price}</div>
                      </button>
                    ))}
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
                      建立中…
                    </>
                  ) : "開始免費試用"}
                </Button>
              </form>

              <Separator />

              <p className="text-center text-sm text-muted-foreground">
                已有帳號？{" "}
                <Link
                  href="/login"
                  className="text-primary font-medium hover:underline underline-offset-2"
                >
                  登入管理後台
                </Link>
              </p>
            </CardContent>
          </Card>

          {/* Trust badges */}
          <div className="mt-6 flex items-center justify-center gap-6">
            {["免費試用 14 天", "無需信用卡", "隨時可取消"].map((badge) => (
              <div key={badge} className="flex items-center gap-1.5 text-xs text-slate-400">
                <div className="h-1 w-1 rounded-full bg-green-500" />
                {badge}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterPageInner />
    </Suspense>
  );
}
