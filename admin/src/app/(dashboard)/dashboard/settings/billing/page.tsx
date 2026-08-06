"use client";
import { useAuth } from "@/lib/auth/store";
import { subscriptionApi, type CurrentPlanResponse } from "@/lib/api/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { CreditCard, Package, Users, ArrowUpRight, AlertTriangle } from "lucide-react";
import { useEffect, useState, useCallback } from "react";

export default function BillingPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const isOwner = state.status === "authenticated" && state.user.role === "owner";

  const [planInfo, setPlanInfo] = useState<CurrentPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadPlan = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await subscriptionApi.getCurrent(token);
      setPlanInfo(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入方案資訊失敗");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadPlan();
  }, [loadPlan]);

  const handleUpgrade = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const result = await subscriptionApi.checkout("professional", token);
      // Redirect to PayPal approval page
      window.location.href = result.approve_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "建立結帳失敗");
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm("確定要取消訂閱嗎？取消後將降級為 Starter 方案。")) return;
    setActionLoading(true);
    setError(null);
    try {
      await subscriptionApi.cancel(token);
      await loadPlan();
    } catch (e) {
      setError(e instanceof Error ? e.message : "取消訂閱失敗");
    } finally {
      setActionLoading(false);
    }
  };

  const usageItems = planInfo
    ? [
        {
          label: "商品數量",
          icon: Package,
          current: planInfo.usage.products ?? 0,
          limit: planInfo.limits.max_products,
        },
        {
          label: "管理員帳號",
          icon: Users,
          current: planInfo.usage.admins ?? 0,
          limit: planInfo.limits.max_admins,
        },
      ]
    : [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">方案與帳單</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">管理你的訂閱方案與用量</p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-muted-foreground">載入中…</div>
      ) : planInfo ? (
        <div className="space-y-6">
          {/* Current plan */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                目前方案
              </CardTitle>
              <CardDescription>你的訂閱方案與計費資訊</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold">
                    {planInfo.display_name} — ${planInfo.plan === "starter" ? "149" : "699"}/月
                  </p>
                  <Badge variant="outline" className="mt-1">
                    {planInfo.plan === "professional" ? "專業版" : "入門版"}
                  </Badge>
                </div>
                {isOwner && (
                  <div className="flex gap-2">
                    {planInfo.plan === "starter" ? (
                      <Button onClick={handleUpgrade} disabled={actionLoading}>
                        <ArrowUpRight className="mr-2 h-4 w-4" />
                        {actionLoading ? "處理中…" : "升級到 Professional"}
                      </Button>
                    ) : (
                      <Button variant="outline" onClick={handleCancel} disabled={actionLoading}>
                        {actionLoading ? "處理中…" : "取消訂閱"}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Usage meters */}
          <Card>
            <CardHeader>
              <CardTitle>用量統計</CardTitle>
              <CardDescription>目前方案的資源使用狀況</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {usageItems.map((item) => {
                const percent = item.limit && item.limit > 0 ? Math.round((item.current / item.limit) * 100) : 0;
                const Icon = item.icon;
                const isNearLimit = percent >= 80;
                return (
                  <div key={item.label}>
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium">{item.label}</span>
                      </div>
                      <span className={`text-sm font-mono ${isNearLimit ? "text-orange-600 font-bold" : "text-muted-foreground"}`}>
                        {item.current} / {item.limit == null ? "∞" : item.limit}
                      </span>
                    </div>
                    {item.limit != null && item.limit > 0 && (
                      <Progress
                        value={percent}
                        className={`h-2 ${isNearLimit ? "[&>div]:bg-orange-500" : ""}`}
                      />
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Separator />

          {/* Plan comparison */}
          <Card>
            <CardHeader>
              <CardTitle>方案比較</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {[
                  {
                    name: "Starter",
                    price: "$149/月",
                    features: ["50 筆商品", "2 個管理員帳號", "基本分析報表", "SEO 重導向管理", "Email 支援"],
                    current: planInfo.plan === "starter",
                  },
                  {
                    name: "Professional",
                    price: "$699/月",
                    features: ["無限商品", "無限管理員帳號", "進階分析 + 意圖評分", "多語系官網（英／繁）", "整合串接 (GA4、GTM、HubSpot)", "優先技術支援"],
                    current: planInfo.plan === "professional",
                  },
                ].map((plan) => (
                  <div
                    key={plan.name}
                    className={`rounded-lg border p-4 ${plan.current ? "border-primary bg-primary/5" : "border-border"}`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-lg">{plan.name}</h3>
                      {plan.current && <Badge>目前方案</Badge>}
                    </div>
                    <p className="text-2xl font-bold mb-4">{plan.price}</p>
                    <ul className="space-y-2">
                      {plan.features.map((f) => (
                        <li key={f} className="text-sm text-muted-foreground flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                          {f}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="py-12 text-center text-muted-foreground">無法載入方案資訊</div>
      )}
    </div>
  );
}
