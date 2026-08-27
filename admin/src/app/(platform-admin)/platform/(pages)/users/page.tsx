"use client";

import { useEffect, useState, useCallback } from "react";
import { AlertCircle, Search, ShieldCheck, UserPlus } from "lucide-react";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type AdminUser } from "@/lib/api/platform-admin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function PlatformUsersPage() {
  const { state } = usePlatformAuth();
  const token =
    state.status === "authenticated" ? state.accessToken : undefined;
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    temporary_password: "",
  });

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    platformAdminApi
      .users(token, search ? { search, limit: 200 } : { limit: 200 })
      .then(setUsers)
      .catch((cause) =>
        setError(cause instanceof Error ? cause.message : "無法讀取用戶。"),
      )
      .finally(() => setLoading(false));
  }, [token, search]);

  useEffect(() => {
    load();
  }, [load]);

  async function createOperator() {
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      await platformAdminApi.createPlatformOperator(token, form);
      setForm({ email: "", full_name: "", temporary_password: "" });
      load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "建立平台帳號失敗。 ");
    } finally {
      setSaving(false);
    }
  }

  async function togglePlatformOperator(user: AdminUser) {
    if (!token) return;
    const action = user.is_active ? "停用" : "啟用";
    if (!window.confirm(`確定要${action}平台帳號「${user.email}」嗎？`)) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await platformAdminApi.updatePlatformOperator(
        token,
        user.id,
        { is_active: !user.is_active },
      );
      setUsers((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : `${action}平台帳號失敗。`,
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">平台用戶</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          建立或停用 ForgeBase 團隊帳號；下方同時提供跨租戶帳號的唯讀檢視。
        </p>
      </div>
      <section className="rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex items-start gap-2">
          <UserPlus className="mt-0.5 h-4 w-4 text-primary" />
          <div>
            <h2 className="font-semibold">新增平台操作員</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              建立後可進入系統方後台並管理所有租戶。請只給受信任的 ForgeBase
              團隊成員。
            </p>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <Input
            value={form.full_name}
            onChange={(event) =>
              setForm({ ...form, full_name: event.target.value })
            }
            placeholder="姓名"
          />
          <Input
            value={form.email}
            onChange={(event) =>
              setForm({ ...form, email: event.target.value })
            }
            placeholder="工作 Email"
            type="email"
          />
          <Input
            value={form.temporary_password}
            onChange={(event) =>
              setForm({ ...form, temporary_password: event.target.value })
            }
            placeholder="臨時密碼（至少 12 字元）"
            type="password"
          />
        </div>
        <div className="mt-4 flex justify-end">
          <Button
            size="sm"
            onClick={createOperator}
            disabled={
              saving ||
              form.full_name.trim().length < 2 ||
              !form.email.includes("@") ||
              form.temporary_password.length < 12
            }
          >
            {saving ? "建立中…" : "建立平台帳號"}
          </Button>
        </div>
      </section>
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="搜尋 Email / 姓名..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="pl-9"
        />
      </div>
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}
      {loading ? (
        <div className="space-y-2 animate-pulse">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="h-10 rounded-lg bg-muted" />
          ))}
        </div>
      ) : users.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          無符合條件的用戶
        </p>
      ) : (
      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div className="max-w-full overflow-x-auto">
        <table className="w-full min-w-[900px] text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-5 py-3">Email</th>
                <th className="px-5 py-3">姓名</th>
                <th className="px-5 py-3">歸屬</th>
                <th className="px-5 py-3">角色</th>
                <th className="px-5 py-3">狀態</th>
                <th className="px-5 py-3">最後登入</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map((user) => {
                const isPlatformOperator = user.is_superuser && !user.tenant_id;
                return (
                  <tr
                    key={user.id}
                    className="transition-colors hover:bg-muted/30"
                  >
                    <td className="px-5 py-2.5">
                      <span className="flex items-center gap-1.5 font-medium">
                        {user.email}
                        {user.is_superuser && (
                          <ShieldCheck className="h-3.5 w-3.5 text-red-500" />
                        )}
                      </span>
                    </td>
                    <td className="px-5 py-2.5 text-muted-foreground">
                      {user.full_name}
                    </td>
                    <td className="px-5 py-2.5">
                      {isPlatformOperator ? (
                        <span className="text-xs font-medium text-primary">
                          ForgeBase 平台
                        </span>
                      ) : user.tenant_name ? (
                        <span className="text-xs font-medium">
                          {user.tenant_name}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-5 py-2.5">
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                        {user.role}
                      </span>
                    </td>
                    <td className="px-5 py-2.5">
                      <span
                        className={`text-xs font-medium ${user.is_active ? "text-green-600" : "text-red-500"}`}
                      >
                        {user.is_active ? "活躍" : "停用"}
                      </span>
                    </td>
                    <td className="px-5 py-2.5 text-xs text-muted-foreground">
                      {user.last_login_at?.slice(0, 16).replace("T", " ") ??
                        "從未"}
                    </td>
                    <td className="px-5 py-2.5 text-right">
                      {isPlatformOperator && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={saving}
                          onClick={() => void togglePlatformOperator(user)}
                        >
                          {user.is_active ? "停用" : "啟用"}
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
        </table>
        </div>
        </div>
      )}
    </div>
  );
}
