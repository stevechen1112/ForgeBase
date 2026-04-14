"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { platformAdminApi, type AdminUser } from "@/lib/api/platform-admin";
import { Search, AlertCircle, ShieldCheck } from "lucide-react";
import { Input } from "@/components/ui/input";

export default function PlatformUsersPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    platformAdminApi
      .users(token, search ? { search } : undefined)
      .then(setUsers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, search]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">平台用戶</h1>
        <p className="mt-1 text-sm text-muted-foreground">跨所有租戶的用戶列表</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="搜尋 Email / 姓名..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
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
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-10 rounded-lg bg-muted" />
          ))}
        </div>
      ) : users.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">無符合條件的用戶</p>
      ) : (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-5 py-3">Email</th>
                <th className="px-5 py-3">姓名</th>
                <th className="px-5 py-3">租戶</th>
                <th className="px-5 py-3">角色</th>
                <th className="px-5 py-3">狀態</th>
                <th className="px-5 py-3">最後登入</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-5 py-2.5">
                    <span className="flex items-center gap-1.5 font-medium">
                      {u.email}
                      {u.is_superuser && (
                        <ShieldCheck className="h-3.5 w-3.5 text-red-500" title="Superuser" />
                      )}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-muted-foreground">{u.full_name}</td>
                  <td className="px-5 py-2.5">
                    {u.tenant_name ? (
                      <span className="text-xs font-medium">{u.tenant_name}</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-5 py-2.5">
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                      {u.role}
                    </span>
                  </td>
                  <td className="px-5 py-2.5">
                    <span className={`text-xs font-medium ${u.is_active ? "text-green-600" : "text-red-500"}`}>
                      {u.is_active ? "活躍" : "停用"}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">
                    {u.last_login_at?.slice(0, 16).replace("T", " ") ?? "從未"}
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
