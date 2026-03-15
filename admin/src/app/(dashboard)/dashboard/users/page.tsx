"use client";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield, User, Mail, Calendar, Key } from "lucide-react";

export default function UsersPage() {
  const { state } = useAuth();
  const user = state.status === "authenticated" ? state.user : null;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">使用者管理</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">管理管理員帳號、角色權限與存取設定</p>
      </div>

      {/* Current user card */}
      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <User className="h-4 w-4" />目前登入帳號
            </CardTitle>
            <CardDescription>您的帳號詳細資訊</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {user ? (
              <>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-lg">
                    {(user.email || "?")[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="font-medium">{user.full_name || user.email}</p>
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <Mail className="h-3 w-3" />{user.email}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <Shield className="h-4 w-4 text-primary" />
                  <span className="text-sm">角色：</span>
                  <Badge className={user.role === "admin" ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700"}>
                    {user.role === "admin" ? "系統管理員" : user.role}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">帳號 ID：<code className="text-xs font-mono bg-muted px-1 rounded">{user.id}</code></span>
                </div>
              </>
            ) : (
              <p className="text-muted-foreground text-sm">載入中…</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Key className="h-4 w-4" />角色權限說明
            </CardTitle>
            <CardDescription>系統目前支援的角色</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { role: "admin", label: "系統管理員", desc: "擁有所有功能的完整存取權，包含使用者管理與系統設定", color: "bg-red-100 text-red-700" },
              { role: "editor", label: "內容編輯", desc: "可建立和編輯所有內容，但無法修改系統設定和使用者", color: "bg-blue-100 text-blue-700" },
              { role: "sales", label: "業務人員", desc: "僅能查看和管理指派給自己的 RFQ 與客戶資料", color: "bg-green-100 text-green-700" },
              { role: "viewer", label: "唯讀查看", desc: "僅能查看內容與報表，不能做任何修改", color: "bg-gray-100 text-gray-700" },
            ].map(r => (
              <div key={r.role} className="flex items-start gap-3">
                <Badge className={`mt-0.5 shrink-0 ${r.color}`}>{r.label}</Badge>
                <p className="text-sm text-muted-foreground">{r.desc}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Info notice */}
      <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
        <div className="flex items-start gap-3">
          <Shield className="mt-0.5 h-5 w-5 text-blue-500 shrink-0" />
          <div>
            <p className="font-medium text-blue-900">使用者列表管理</p>
            <p className="mt-1 text-sm text-blue-700">
              目前系統的使用者帳號透過後端管理員 CLI 建立。多使用者管理介面（新增、停用、重設密碼）正在開發中，預計於 Phase 2 部署完成後開放。
            </p>
            <p className="mt-2 text-sm text-blue-700">
              如需新增帳號，請聯繫系統管理員或直接操作後端資料庫。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
