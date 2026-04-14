"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, AlertCircle, Loader2, ShieldAlert } from "lucide-react";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { authApi } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function PlatformLoginPage() {
  const router = useRouter();
  const { state, login } = usePlatformAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // If already authenticated as superuser, redirect via useEffect to avoid setState-in-render
  useEffect(() => {
    if (state.status === "authenticated" && state.user?.is_superuser) {
      router.replace("/platform/overview");
    }
  }, [state, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login({ email, password });
      if (!res.user?.is_superuser) {
        setError("此帳號不具備平台管理員權限");
        return;
      }
      login(res);
      router.replace("/platform/overview");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "登入失敗";
      setError(msg.includes("401") || msg.includes("400") ? "帳號或密碼錯誤" : msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(222,47%,11%)] p-4">
      {/* Decorative */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-red-500 opacity-[0.03]" />
        <div className="absolute -bottom-48 -left-48 h-[500px] w-[500px] rounded-full bg-red-500 opacity-[0.03]" />
      </div>

      <Card className="relative w-full max-w-md border-red-900/20 bg-[hsl(222,47%,14%)] text-white shadow-2xl">
        <CardHeader className="text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-red-500/10 ring-1 ring-red-500/20">
            <ShieldAlert className="h-7 w-7 text-red-400" />
          </div>
          <CardTitle className="text-xl">ForgeBase 平台管理</CardTitle>
          <CardDescription className="text-gray-400">
            僅限平台超級管理員登入
          </CardDescription>
        </CardHeader>

        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4 border-red-900/40 bg-red-950/40">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-gray-300">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="border-white/10 bg-white/5 text-white placeholder:text-gray-500 focus:border-red-500/50 focus:ring-red-500/20"
                placeholder="admin@forgebase.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-gray-300">
                密碼
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPw ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="border-white/10 bg-white/5 pr-10 text-white placeholder:text-gray-500 focus:border-red-500/50 focus:ring-red-500/20"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                  tabIndex={-1}
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
            >
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              登入平台管理
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-gray-500">
            此入口僅供 ForgeBase 平台管理員使用
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
