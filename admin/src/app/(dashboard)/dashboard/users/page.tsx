"use client";
import { useAuth } from "@/lib/auth/store";
import { authApi, type TeamMember, type InviteRequest } from "@/lib/api/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Shield, UserPlus, Users, Mail, ToggleLeft, ToggleRight } from "lucide-react";
import { useEffect, useState, useCallback } from "react";

const ROLE_LABELS: Record<string, { label: string; color: string }> = {
  owner: { label: "帳號擁有者", color: "bg-purple-100 text-purple-700" },
  admin: { label: "系統管理員", color: "bg-red-100 text-red-700" },
  marketing_manager: { label: "行銷經理", color: "bg-blue-100 text-blue-700" },
  sales: { label: "業務人員", color: "bg-green-100 text-green-700" },
};

function roleBadge(role: string) {
  const r = ROLE_LABELS[role] || { label: role, color: "bg-gray-100 text-gray-700" };
  return <Badge className={r.color}>{r.label}</Badge>;
}

export default function UsersPage() {
  const { state } = useAuth();
  const user = state.status === "authenticated" ? state.user : null;
  const token = state.status === "authenticated" ? state.accessToken : "";
  const isAdminOrOwner = user?.role === "admin" || user?.role === "owner";

  const [team, setTeam] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Invite dialog state
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteForm, setInviteForm] = useState<InviteRequest>({
    email: "",
    full_name: "",
    password: "",
    role: "marketing_manager",
  });
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);

  const loadTeam = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await authApi.listTeam(token);
      setTeam(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入團隊成員失敗");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadTeam();
  }, [loadTeam]);

  const handleInvite = async () => {
    setInviteLoading(true);
    setInviteError(null);
    try {
      await authApi.inviteTeamMember(inviteForm, token);
      setInviteOpen(false);
      setInviteForm({ email: "", full_name: "", password: "", role: "marketing_manager" });
      await loadTeam();
    } catch (e) {
      setInviteError(e instanceof Error ? e.message : "邀請失敗");
    } finally {
      setInviteLoading(false);
    }
  };

  const handleToggleActive = async (member: TeamMember) => {
    try {
      await authApi.updateTeamMember(member.id, { is_active: !member.is_active }, token);
      await loadTeam();
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失敗");
    }
  };

  const handleRoleChange = async (member: TeamMember, newRole: string) => {
    try {
      await authApi.updateTeamMember(member.id, { role: newRole }, token);
      await loadTeam();
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新角色失敗");
    }
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">團隊成員管理</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">管理團隊帳號、角色權限與存取設定</p>
        </div>
        {isAdminOrOwner && (
          <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="mr-2 h-4 w-4" />
                邀請成員
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>邀請新成員</DialogTitle>
                <DialogDescription>新增團隊成員到你的帳戶</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="invite-email">電子郵件</Label>
                  <Input
                    id="invite-email"
                    type="email"
                    value={inviteForm.email}
                    onChange={(e) => setInviteForm((f) => ({ ...f, email: e.target.value }))}
                    placeholder="user@example.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="invite-name">姓名</Label>
                  <Input
                    id="invite-name"
                    value={inviteForm.full_name}
                    onChange={(e) => setInviteForm((f) => ({ ...f, full_name: e.target.value }))}
                    placeholder="王小明"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="invite-password">初始密碼</Label>
                  <Input
                    id="invite-password"
                    type="password"
                    value={inviteForm.password}
                    onChange={(e) => setInviteForm((f) => ({ ...f, password: e.target.value }))}
                    placeholder="至少 8 個字元"
                  />
                </div>
                <div className="space-y-2">
                  <Label>角色</Label>
                  <Select
                    value={inviteForm.role}
                    onValueChange={(v) => setInviteForm((f) => ({ ...f, role: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">系統管理員</SelectItem>
                      <SelectItem value="marketing_manager">行銷經理</SelectItem>
                      <SelectItem value="sales">業務人員</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {inviteError && <p className="text-sm text-destructive">{inviteError}</p>}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setInviteOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleInvite} disabled={inviteLoading || !inviteForm.email || !inviteForm.full_name || !inviteForm.password}>
                  {inviteLoading ? "送出中…" : "送出邀請"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Current user card */}
      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Shield className="h-4 w-4" />目前登入
            </CardTitle>
          </CardHeader>
          <CardContent>
            {user ? (
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-lg">
                  {(user.full_name || user.email)[0].toUpperCase()}
                </div>
                <div>
                  <p className="font-medium">{user.full_name || user.email}</p>
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                </div>
                <div className="ml-auto">{roleBadge(user.role)}</div>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">載入中…</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4" />團隊人數
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{team.length}</p>
            <p className="text-xs text-muted-foreground">
              活躍 {team.filter((m) => m.is_active).length} / 停用 {team.filter((m) => !m.is_active).length}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Mail className="h-4 w-4" />角色分佈
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(
                team.reduce((acc, m) => {
                  acc[m.role] = (acc[m.role] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>),
              ).map(([role, count]) => (
                <span key={role} className="text-sm">
                  {roleBadge(role)} <span className="text-muted-foreground">×{count}</span>
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Team table */}
      <Card>
        <CardHeader>
          <CardTitle>團隊成員列表</CardTitle>
          <CardDescription>所有帳號的詳細資訊與狀態管理</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="py-8 text-center text-muted-foreground">載入中…</p>
          ) : team.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">尚無團隊成員</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>成員</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead>建立日期</TableHead>
                  <TableHead>上次登入</TableHead>
                  {isAdminOrOwner && <TableHead className="text-right">操作</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {team.map((member) => (
                  <TableRow key={member.id} className={!member.is_active ? "opacity-50" : ""}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-sm">
                          {(member.full_name || member.email)[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-sm">{member.full_name}</p>
                          <p className="text-xs text-muted-foreground">{member.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {isAdminOrOwner && member.role !== "owner" && member.id !== user?.id ? (
                        <Select
                          value={member.role}
                          onValueChange={(v) => handleRoleChange(member, v)}
                        >
                          <SelectTrigger className="w-[140px] h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">系統管理員</SelectItem>
                            <SelectItem value="marketing_manager">行銷經理</SelectItem>
                            <SelectItem value="sales">業務人員</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        roleBadge(member.role)
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={member.is_active ? "default" : "secondary"}>
                        {member.is_active ? "活躍" : "已停用"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {member.created_at ? new Date(member.created_at).toLocaleDateString("zh-TW") : "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {member.last_login_at ? new Date(member.last_login_at).toLocaleDateString("zh-TW") : "從未登入"}
                    </TableCell>
                    {isAdminOrOwner && (
                      <TableCell className="text-right">
                        {member.role !== "owner" && member.id !== user?.id && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleActive(member)}
                            title={member.is_active ? "停用帳號" : "啟用帳號"}
                          >
                            {member.is_active ? (
                              <ToggleRight className="h-4 w-4 text-green-600" />
                            ) : (
                              <ToggleLeft className="h-4 w-4 text-muted-foreground" />
                            )}
                          </Button>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
