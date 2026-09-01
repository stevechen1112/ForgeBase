"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { categoriesApi, type ProductCategory } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { LocaleSwitcher } from "@/components/ui/LocaleSwitcher";
import { SUPPORTED_LOCALES, draftKey, takeDraft } from "@/lib/i18n";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<ProductCategory>; id?: string; aiDraft?: boolean };

export default function CategoryForm({ initial, id, aiDraft }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    category_name: initial?.category_name ?? "",
    slug: initial?.slug ?? "",
    description: initial?.description ?? "",
    sort_order: initial?.sort_order ?? 0,
    seo_title: initial?.seo_title ?? "",
    seo_description: initial?.seo_description ?? "",
    og_image_url: initial?.og_image_url ?? "",
    status: initial?.status ?? "draft",
    locale: initial?.locale ?? "zh-tw",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localeVariants, setLocaleVariants] = useState<ProductCategory[]>([]);
  const [draftNotice, setDraftNotice] = useState(false);

  useEffect(() => {
    if (id || !aiDraft) return;
    const slug = initial?.slug ?? "";
    const locale = initial?.locale ?? "";
    if (!slug || !locale) return;
    const draft = takeDraft(draftKey("category", slug, locale));
    if (draft) {
      setForm((prev) => ({
        ...prev,
        category_name: draft.category_name ?? prev.category_name,
        description: draft.description ?? prev.description,
        seo_title: draft.seo_title ?? prev.seo_title,
        seo_description: draft.seo_description ?? prev.seo_description,
      }));
      setDraftNotice(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!id || !form.slug) return;
    categoriesApi.list(token, { slug: form.slug, locale: "all", page_size: 20 })
      .then((res) => setLocaleVariants(res.data.filter((c) => c.id !== id)))
      .catch(() => {/* non-critical */});
  }, [id, form.slug, token]);

  const handleNameChange = (v: string) => {
    const autoSlug = v.toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
    setForm((f) => ({ ...f, category_name: v, ...(!id ? { slug: autoSlug } : {}) }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await categoriesApi.update(token, id, form); }
      else { await categoriesApi.create(token, form); }
      router.push("/dashboard/categories");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {id && (
        <LocaleSwitcher
          entityType="category"
          basePath="/dashboard/categories"
          id={id}
          slug={form.slug}
          currentLocale={form.locale}
          currentStatus={form.status}
          currentUpdatedAt={initial?.updated_at}
          variants={localeVariants.map((v) => ({ id: v.id, locale: v.locale, status: v.status, updated_at: v.updated_at }))}
        />
      )}

      {draftNotice && (
        <Alert className="border-violet-200 bg-violet-50">
          <AlertDescription className="text-violet-800">
            此為依來源語言產生的客戶語言草稿，尚未出現在公開網站。請看過後再上架。
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">基本資訊</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>分類名稱 *</Label>
            <Input value={form.category_name} onChange={(e) => handleNameChange(e.target.value)} required maxLength={60} />
          </div>
          <div className="space-y-1.5">
            <Label>網址路徑 *</Label>
            <Input className="font-mono" value={form.slug} onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))} pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$" required maxLength={60} />
          </div>
          <div className="space-y-1.5">
            <Label>描述</Label>
            <Textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={3} />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label>排序</Label>
              <Input type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: Number(e.target.value) }))} min={0} />
            </div>
            <div className="space-y-1.5">
              <Label>狀態</Label>
              <select className={SELECT_CLS} value={form.status} onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}>
                <option value="draft">草稿</option>
                <option value="published">已上架</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>語言</Label>
              <select className={SELECT_CLS} value={form.locale} onChange={(e) => setForm((f) => ({ ...f, locale: e.target.value }))}>
                {SUPPORTED_LOCALES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">搜尋標題設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>搜尋標題（最多 70 字）</Label>
            <Input value={form.seo_title} onChange={(e) => setForm((f) => ({ ...f, seo_title: e.target.value }))} maxLength={70} />
          </div>
          <div className="space-y-1.5">
            <Label>搜尋說明（最多 160 字）</Label>
            <Textarea value={form.seo_description} onChange={(e) => setForm((f) => ({ ...f, seo_description: e.target.value }))} rows={2} maxLength={160} />
          </div>
          <div className="space-y-1.5">
            <Label>分享預覽圖網址</Label>
            <Input value={form.og_image_url} onChange={(e) => setForm((f) => ({ ...f, og_image_url: e.target.value }))} type="url" placeholder="https://.../category-og.jpg" />
            <p className="text-xs text-muted-foreground">分類頁社群分享圖，建議與封面圖分開配置。</p>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-3 pt-2">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "儲存中…" : "儲存"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.push("/dashboard/categories")}>取消</Button>
      </div>
    </form>
  );
}
