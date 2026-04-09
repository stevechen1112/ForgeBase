"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { categoriesApi, productsApi, redirectsApi, type Product } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

const SUPPORTED_LOCALES = [
  { value: "en", label: "English" },
  { value: "zh-tw", label: "繁體中文" },
  { value: "zh-cn", label: "简体中文" },
  { value: "ja", label: "日本語" },
  { value: "ko", label: "한국어" },
  { value: "de", label: "Deutsch" },
];

type Props = { initial?: Partial<Product>; id?: string };

export default function ProductForm({ initial, id }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    product_name: initial?.product_name ?? "",
    slug: initial?.slug ?? "",
    model_number: initial?.model_number ?? "",
    short_description: initial?.short_description ?? "",
    full_description: initial?.full_description ?? "",
    specifications: initial?.specifications ?? "",
    category_id: initial?.category_id ?? "",
    seo_title: initial?.seo_title ?? "",
    seo_description: initial?.seo_description ?? "",
    og_image_url: initial?.og_image_url ?? "",
    image_alt: initial?.image_alt ?? "",
    status: initial?.status ?? "draft",
    locale: initial?.locale ?? "en",
    publish_at: initial?.published_at
      ? new Date(initial.published_at as string).toISOString().slice(0, 16)
      : "",
  });
  const initialSlug = useRef(initial?.slug ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [redirectCreated, setRedirectCreated] = useState(false);
  const [categorySlug, setCategorySlug] = useState<string | null>(null);
  const [localeVariants, setLocaleVariants] = useState<Product[]>([]);

  useEffect(() => {
    if (!id || !form.slug) return;
    productsApi.list(token, { slug: form.slug, page_size: 20 })
      .then((res) => setLocaleVariants(res.data.filter((p: Product) => p.id !== id)))
      .catch(() => {/* non-critical */});
  }, [id, form.slug, token]);

  useEffect(() => {
    if (!token || !form.category_id) {
      setCategorySlug(null);
      return;
    }
    categoriesApi.get(token, form.category_id)
      .then((res) => setCategorySlug(res.data.slug))
      .catch(() => setCategorySlug(null));
  }, [form.category_id, token]);

  const handleNameChange = (v: string) => {
    const autoSlug = v.toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
    setForm((f) => ({ ...f, product_name: v, ...(!id ? { slug: autoSlug } : {}) }));
  };

  const f = (key: keyof typeof form) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.status === "scheduled" && !form.publish_at) {
      setError("請選擇預約上架時間"); return;
    }
    setSaving(true); setError(null);
    try {
      const { publish_at, ...rest } = form;
      const payload: Record<string, unknown> = { ...rest };
      if (form.status === "scheduled" && publish_at) {
        payload.published_at = new Date(publish_at).toISOString();
      }
      if (id) {
        await productsApi.update(token, id, payload);
        if (form.slug && initialSlug.current && form.slug !== initialSlug.current && categorySlug) {
          try {
            await redirectsApi.create(token, {
              from_path: `/products/${categorySlug}/${initialSlug.current}`,
              to_path: `/products/${categorySlug}/${form.slug}`,
              status_code: 301,
              is_active: true,
              note: `Auto: product slug ${initialSlug.current} → ${form.slug}`,
            });
            setRedirectCreated(true);
          } catch { /* non-critical */ }
        }
      } else { await productsApi.create(token, payload); }
      router.push("/dashboard/products");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {redirectCreated && <Alert><AlertDescription>✓ Slug 已更新，已自動建立 301 Redirect 規則</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle className="text-base">產品資訊</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>商品名稱 *</Label>
              <Input value={form.product_name} onChange={(e) => handleNameChange(e.target.value)} required maxLength={120} />
            </div>
            <div className="space-y-1.5">
              <Label>型號 *</Label>
              <Input {...f("model_number")} required maxLength={60} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Slug *</Label>
            <Input className="font-mono" {...f("slug")} required pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$" maxLength={100} />
          </div>
          <div className="space-y-1.5">
            <Label>短描述 *</Label>
            <Textarea {...f("short_description")} rows={2} required maxLength={300} />
          </div>
          <div className="space-y-1.5">
            <Label>完整描述</Label>
            <Textarea {...f("full_description")} rows={5} />
          </div>
          <div className="space-y-1.5">
            <Label>規格 (JSON / Markdown)</Label>
            <Textarea {...f("specifications")} rows={4} className="font-mono text-xs" />
          </div>
          <div className="space-y-1.5">
            <Label>分類 ID</Label>
            <Input className="font-mono text-xs" {...f("category_id")} placeholder="UUID" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>狀態</Label>
              <select className={SELECT_CLS} {...f("status")}>
                <option value="draft">草稿 (Draft)</option>
                <option value="scheduled">⏰ 預約上架 (Scheduled)</option>
                <option value="published">已上架 (Published)</option>
                <option value="archived">已封存 (Archived)</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>語言</Label>
              <select className={SELECT_CLS} {...f("locale")}>
                {SUPPORTED_LOCALES.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
              </select>
            </div>
          </div>

          {form.status === "scheduled" && (
            <div className="space-y-1.5 rounded-md border border-amber-200 bg-amber-50/60 p-3">
              <Label className="text-amber-800">⏰ 預約上架時間 *</Label>
              <Input
                type="datetime-local"
                value={form.publish_at}
                onChange={(e) => setForm((prev) => ({ ...prev, publish_at: e.target.value }))}
                min={new Date().toISOString().slice(0, 16)}
                required
                className="bg-white"
              />
              <p className="text-xs text-amber-700">到達指定時間後，請手動將狀態切換為「已上架」或聯繫技術團隊啟用自動排程。</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Locale Variants Panel – edit mode only */}
      {id && (
        <Card className="border-blue-200 bg-blue-50/30">
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm text-blue-800">語言版本管理</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="flex flex-wrap gap-2">
              <Badge className="bg-blue-700 text-white hover:bg-blue-800">
                {SUPPORTED_LOCALES.find((l) => l.value === form.locale)?.label ?? form.locale} ● 目前版本
              </Badge>
              {localeVariants.map((v) => (
                <a key={v.id} href={`/dashboard/products/${v.id}/edit`}>
                  <Badge variant="outline" className="border-green-500 text-green-700 hover:bg-green-50 cursor-pointer">
                    {SUPPORTED_LOCALES.find((l) => l.value === v.locale)?.label ?? v.locale} ✓
                  </Badge>
                </a>
              ))}
              {SUPPORTED_LOCALES.filter(
                (l) => l.value !== form.locale && !localeVariants.some((v) => v.locale === l.value)
              ).map((l) => (
                <a key={l.value} href={`/dashboard/products/new?slug=${encodeURIComponent(form.slug)}&locale=${l.value}`}>
                  <Badge variant="outline" className="border-dashed text-muted-foreground hover:border-blue-400 hover:text-blue-600 cursor-pointer">
                    + {l.label}
                  </Badge>
                </a>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">SEO 設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>SEO Title</Label>
            <Input {...f("seo_title")} maxLength={70} />
          </div>
          <div className="space-y-1.5">
            <Label>SEO Description</Label>
            <Textarea {...f("seo_description")} rows={2} maxLength={160} />
          </div>
          <div className="space-y-1.5">
            <Label>OG Image URL</Label>
            <Input {...f("og_image_url")} type="url" placeholder="https://.../product-og.jpg" />
            <p className="text-xs text-muted-foreground">建議使用 1200 x 630 的分享圖，供 Open Graph / Twitter Card 使用。</p>
          </div>
          <div className="space-y-1.5">
            <Label>主圖 Alt 文字</Label>
            <Input {...f("image_alt")} maxLength={200} placeholder="例：VDE insulated screwdriver set for industrial maintenance" />
            <p className="text-xs text-muted-foreground">這段文字會用於圖片 SEO、無障礙與結構化資料 ImageObject 描述。</p>
          </div>
        </CardContent>
      </Card>


      <div className="flex gap-3 pt-2">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "儲存中…" : "儲存"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.back()}>取消</Button>
      </div>
    </form>
  );
}
