"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import { platformAdminApi, type TenantDetail, type TenantUpdate } from "@/lib/api/platform-admin";
import {
  ArrowLeft, AlertCircle, Users, Package, ClipboardList, Eye,
  Settings2, CheckCircle2, XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PLAN_OPTIONS = ["starter", "professional", "enterprise"];

export default function TenantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;

  const [tenant, setTenant] = useState<TenantDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editPlan, setEditPlan] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !id) return;
    platformAdminApi
      .tenant(token, id)
      .then((t) => {
        setTenant(t);
        setEditPlan(t.plan);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, id]);

  async function save() {
    if (!token || !tenant || !editPlan) return;
    setSaving(true);
    try {
      const update: TenantUpdate = { plan: editPlan };
      await platformAdminApi.updateTenant(token, tenant.id, update);
      setTenant((prev) => prev ? { ...prev, plan: editPlan } : prev);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive() {
    if (!token || !tenant) return;
    setSaving(true);
    try {
      const update: TenantUpdate = { is_active: !tenant.is_active };
      await platformAdminApi.updateTenant(token, tenant.id, update);
      setTenant((prev) => prev ? { ...prev, is_active: !prev.is_active } : prev);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "更新失敗");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-6 w-48 rounded bg-muted" />
        <div className="h-32 rounded-xl bg-muted" />
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
        <AlertCircle className="h-4 w-4 shrink-0" />
        {error ?? "找不到租戶"}
      </div>
    );
  }

  const stats = [
    { icon: Users, label: "用戶", value: tenant.user_count },
    { icon: Package, label: "商品", value: tenant.product_count },
    { icon: ClipboardList, label: "RFQ", value: tenant.rfq_count },
    { icon: Eye, label: "訪客", value: tenant.visitor_count },
  ];

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        返回租戶列表
      </button>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{tenant.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Slug: {tenant.slug} · 建立: {tenant.created_at?.slice(0, 10)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleActive}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors"
          >
            {tenant.is_active ? (
              <><CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> 活躍中（點擊停用）</>
            ) : (
              <><XCircle className="h-3.5 w-3.5 text-red-400" /> 已停用（點擊啟用）</>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stats.map(({ icon: Icon, label, value }) => (
          <div key={label} className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <div className="mb-2 flex items-center gap-2 text-muted-foreground">
              <Icon className="h-4 w-4" />
              <span className="text-xs text-muted-foreground">{label}</span>
            </div>
            <p className="text-2xl font-bold tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      {/* Plan editor */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Settings2 className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">方案設定</h3>
        </div>
        <div className="flex items-center gap-3">
          <Select value={editPlan ?? tenant.plan} onValueChange={setEditPlan}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PLAN_OPTIONS.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={save}
            disabled={saving || editPlan === tenant.plan}
          >
            {saving ? "儲存中..." : "儲存"}
          </Button>
        </div>
        {(tenant.max_products !== undefined || tenant.max_admins !== undefined) && (
          <p className="mt-3 text-xs text-muted-foreground">
            商品上限: {tenant.max_products ?? "—"} · 管理員上限: {tenant.max_admins ?? "—"}
          </p>
        )}
      </div>

      {/* Users */}
      {tenant.users.length > 0 && (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          <div className="border-b border-border px-5 py-3">
            <h3 className="text-sm font-semibold">用戶列表 ({tenant.users.length})</h3>
          </div>
          <table className="w-full text-sm">
            <tbody className="divide-y divide-border">
              {tenant.users.map((u) => (
                <tr key={u.id} className="hover:bg-muted/30">
                  <td className="px-5 py-2.5 font-medium">{u.email}</td>
                  <td className="px-5 py-2.5 text-muted-foreground">{u.full_name}</td>
                  <td className="px-5 py-2.5">
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                      {u.role}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">
                    {u.is_active ? "活躍" : "停用"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Recent RFQs */}
      {tenant.recent_rfqs.length > 0 && (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          <div className="border-b border-border px-5 py-3">
            <h3 className="text-sm font-semibold">最近 RFQ</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-5 py-2">聯絡人</th>
                <th className="px-5 py-2">Email</th>
                <th className="px-5 py-2">狀態</th>
                <th className="px-5 py-2">提交時間</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tenant.recent_rfqs.map((r) => (
                <tr key={r.id} className="hover:bg-muted/30">
                  <td className="px-5 py-2.5 font-medium">{r.contact_name}</td>
                  <td className="px-5 py-2.5 text-muted-foreground">{r.contact_email}</td>
                  <td className="px-5 py-2.5">
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{r.status}</span>
                  </td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">
                    {r.submitted_at?.slice(0, 16).replace("T", " ") ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
