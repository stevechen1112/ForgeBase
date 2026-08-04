"use client";

import { type ChangeEvent, type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Plus, RefreshCw, Route, Search, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { redirectsApi, type RedirectRule } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type FormState = {
  from_path: string;
  to_path: string;
  status_code: 301 | 302;
  is_active: boolean;
  note: string;
};

const EMPTY_FORM: FormState = {
  from_path: "",
  to_path: "",
  status_code: 301,
  is_active: true,
  note: "",
};

function normalizePath(path: string) {
  if (!path) return "";
  return path.startsWith("/") ? path : `/${path}`;
}

export default function RedirectsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [items, setItems] = useState<RedirectRule[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await redirectsApi.list(token, false);
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "無法載入 舊網址轉址");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const lower = query.trim().toLowerCase();
    if (!lower) return items;
    return items.filter((item) =>
      [item.from_path, item.to_path, item.note].some((value) => value.toLowerCase().includes(lower)),
    );
  }, [items, query]);

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditingId(null);
  }

  function startEdit(item: RedirectRule) {
    setEditingId(item.id);
    setForm({
      from_path: item.from_path,
      to_path: item.to_path,
      status_code: item.status_code,
      is_active: item.is_active,
      note: item.note,
    });
    setSuccess(null);
    setError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const payload = {
        ...form,
        from_path: normalizePath(form.from_path.trim()),
        to_path: normalizePath(form.to_path.trim()),
        note: form.note.trim(),
      };
      if (payload.from_path === payload.to_path) {
        throw new Error("來源與目標路徑不能相同");
      }
      if (editingId) {
        await redirectsApi.update(token, editingId, payload);
        setSuccess("轉址規則已更新");
      } else {
        await redirectsApi.create(token, payload);
        setSuccess("轉址規則已建立");
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    setError(null);
    setSuccess(null);
    try {
      await redirectsApi.delete(token, id);
      if (editingId === id) resetForm();
      setSuccess("轉址規則已停用");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "停用失敗");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">舊網址轉址</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            產品或頁面網址改名後，把舊連結導到新頁，避免客戶點進去找不到。
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="border-green-200 bg-green-50 text-green-900">
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">{editingId ? "編輯轉址" : "新增轉址"}</CardTitle>
            <CardDescription>
              產品或頁面網址變更後，可在此建立舊網址至新網址的轉址規則。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label>來源路徑</Label>
                <Input
                  value={form.from_path}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setForm((prev) => ({ ...prev, from_path: e.target.value }))}
                  placeholder="/products/old-slug"
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label>目標路徑</Label>
                <Input
                  value={form.to_path}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setForm((prev) => ({ ...prev, to_path: e.target.value }))}
                  placeholder="/products/new-slug"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>轉址類型</Label>
                  <select
                    className={SELECT_CLS}
                    value={String(form.status_code)}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) => setForm((prev) => ({ ...prev, status_code: Number(e.target.value) as 301 | 302 }))}
                  >
                    <option value="301">永久轉址</option>
                    <option value="302">暫時轉址</option>
                  </select>
                </div>
                <div className="flex items-center justify-between rounded-lg border bg-muted/20 px-4 py-3">
                  <div>
                    <Label htmlFor="redirect-active">啟用</Label>
                    <p className="text-xs text-muted-foreground">停用後規則會保留歷史紀錄。</p>
                  </div>
                  <Switch
                    id="redirect-active"
                    checked={form.is_active}
                    onCheckedChange={(checked: boolean) => setForm((prev) => ({ ...prev, is_active: checked }))}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>備註</Label>
                <Textarea
                  value={form.note}
                  onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setForm((prev) => ({ ...prev, note: e.target.value }))}
                  rows={3}
                  placeholder="例：產品型號改版、分類重整、活動頁合併"
                />
              </div>
              <div className="rounded-md border border-dashed bg-muted/20 p-3 text-xs text-muted-foreground">
                建議：網址永久改名選「永久轉址」；短期活動頁才用「暫時轉址」。
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={saving}>
                  {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
                  {editingId ? "更新規則" : "新增規則"}
                </Button>
                {editingId && (
                  <Button type="button" variant="outline" onClick={resetForm}>
                    取消編輯
                  </Button>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-4">
            <div>
              <CardTitle className="text-base">目前規則</CardTitle>
              <CardDescription>共 {items.length} 筆，支援搜尋來源路徑、目標路徑與備註。</CardDescription>
            </div>
            <div className="relative w-full max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={query} onChange={(e: ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)} placeholder="搜尋轉址規則…" className="pl-9" />
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>來源</TableHead>
                  <TableHead>目標</TableHead>
                  <TableHead className="w-24">狀態</TableHead>
                  <TableHead className="w-24">是否啟用</TableHead>
                  <TableHead>備註</TableHead>
                  <TableHead className="w-32 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-16 text-center text-muted-foreground">
                      <div className="flex flex-col items-center gap-3">
                        <Route className="h-10 w-10 opacity-40" />
                        <div>
                          <p className="font-medium">尚無轉址規則</p>
                          <p className="text-sm">產品或頁面網址改名時，請在這裡把舊連結導到新頁。</p>
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-mono text-xs">{item.from_path}</TableCell>
                      <TableCell className="font-mono text-xs">{item.to_path}</TableCell>
                      <TableCell>
                        <Badge variant={item.status_code === 301 ? "default" : "secondary"}>{item.status_code}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={item.is_active ? "outline" : "secondary"} className={item.is_active ? "border-green-500 text-green-700" : "text-muted-foreground"}>
                          {item.is_active ? "啟用" : "停用"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{item.note || "-"}</TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => startEdit(item)}>
                            編輯
                          </Button>
                          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleDelete(item.id)} disabled={deletingId === item.id}>
                            {deletingId === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
