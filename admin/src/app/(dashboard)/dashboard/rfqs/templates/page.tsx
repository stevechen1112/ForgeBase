"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { apiClient } from "@/lib/api/client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { OpsConfigCard } from "@/components/settings/ops-config-card";

type Template = {
  id: string;
  name: string;
  product_line: string | null;
  country: string | null;
  locale: string;
  body: string;
  updated_at: string;
};

const EMPTY = { name: "", product_line: "", country: "", locale: "en", body: "" };

export default function ReplyTemplatesPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [templates, setTemplates] = useState<Template[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      setTemplates(await apiClient.get<Template[]>("/tracking/rfqs/templates", token));
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  function startEdit(t: Template) {
    setEditingId(t.id);
    setForm({
      name: t.name,
      product_line: t.product_line ?? "",
      country: t.country ?? "",
      locale: t.locale,
      body: t.body,
    });
    setMessage(null);
    setError(null);
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY);
  }

  async function handleSave() {
    if (!form.name.trim() || !form.body.trim()) {
      setError("名稱與內容為必填。");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    const payload = {
      name: form.name.trim(),
      body: form.body,
      product_line: form.product_line.trim() || null,
      country: form.country.trim().toUpperCase() || null,
      locale: form.locale,
    };
    try {
      if (editingId) {
        await apiClient.patch(`/tracking/rfqs/templates/${editingId}`, payload, token);
        setMessage("範本已更新。");
      } else {
        await apiClient.post("/tracking/rfqs/templates", payload, token);
        setMessage("範本已建立。");
      }
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("確定刪除此範本？")) return;
    setError(null);
    try {
      await apiClient.del(`/tracking/rfqs/templates/${id}`, token);
      if (editingId === id) resetForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "刪除失敗");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="icon">
          <Link href="/dashboard/rfqs">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">回覆範本</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            依產品線、國家、語系準備第一封回覆範本；開詢價單時會自動帶出合適範本。
          </p>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {message && (
        <Alert>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <OpsConfigCard />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{editingId ? "編輯範本" : "新增範本"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="tpl_name">名稱 *</Label>
              <Input
                id="tpl_name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="例：手工具標準首封回覆"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tpl_line">產品線</Label>
              <Input
                id="tpl_line"
                value={form.product_line}
                onChange={(e) => setForm((f) => ({ ...f, product_line: e.target.value }))}
                placeholder="通用可留白"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tpl_country">國家（ISO-2）</Label>
              <Input
                id="tpl_country"
                maxLength={2}
                value={form.country}
                onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))}
                placeholder="例：US"
              />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-1.5">
              <Label htmlFor="tpl_locale">語系</Label>
              <select
                id="tpl_locale"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.locale}
                onChange={(e) => setForm((f) => ({ ...f, locale: e.target.value }))}
              >
                <option value="en">en</option>
                <option value="zh-TW">zh-TW</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tpl_body">範本內容 *</Label>
            <Textarea
              id="tpl_body"
              rows={10}
              value={form.body}
              onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
              placeholder="Dear {buyer_name}, ..."
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => void handleSave()} disabled={saving || !token}>
              <Plus className="mr-2 h-4 w-4" />
              {editingId ? "儲存變更" : "建立範本"}
            </Button>
            {editingId && (
              <Button variant="outline" onClick={resetForm}>
                取消編輯
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {loading ? (
          <p className="text-sm text-muted-foreground">載入中…</p>
        ) : templates.length === 0 ? (
          <p className="text-sm text-muted-foreground">尚無範本。建立第一個範本後，RFQ 回覆輔助就能自動匹配。</p>
        ) : (
          templates.map((t) => (
            <Card key={t.id}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{t.name}</span>
                      <Badge variant="outline" className="text-xs">{t.locale}</Badge>
                      {t.product_line && <Badge variant="outline" className="text-xs">{t.product_line}</Badge>}
                      {t.country && <Badge variant="outline" className="text-xs">{t.country}</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      更新於 {new Date(t.updated_at).toLocaleString("zh-TW")}
                    </p>
                    <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm text-muted-foreground">{t.body}</p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button variant="ghost" size="icon" onClick={() => startEdit(t)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => void handleDelete(t.id)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
