"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Upload } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { assetsApi, categoriesApi, productsApi, redirectsApi, type Product, type ProductCategory } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RelationsPanel } from "@/components/ui/RelationsPanel";
import { LocaleSwitcher } from "@/components/ui/LocaleSwitcher";
import { SpecRowsEditor } from "@/components/ui/SpecRowsEditor";
import { ProductGalleryEditor } from "@/components/content/ProductGalleryEditor";
import { SUPPORTED_LOCALES, draftKey, takeDraft } from "@/lib/i18n";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<Product>; id?: string; aiDraft?: boolean };

export default function ProductForm({ initial, id, aiDraft }: Props) {
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
    image_url: (initial as Product | undefined)?.image_url ?? "",
    og_image_url: initial?.og_image_url ?? "",
    image_alt: initial?.image_alt ?? "",
    status: initial?.status ?? "draft",
    locale: initial?.locale ?? "zh-tw",
    display_priority: String(initial?.display_priority ?? 0),
    publish_at: initial?.published_at
      ? new Date(initial.published_at as string).toISOString().slice(0, 16)
      : "",
  });
  const initialSlug = useRef(initial?.slug ?? "");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [redirectCreated, setRedirectCreated] = useState(false);
  const [categorySlug, setCategorySlug] = useState<string | null>(null);
  const [localeVariants, setLocaleVariants] = useState<Product[]>([]);
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [draftNotice, setDraftNotice] = useState(false);

  // Legacy manual form-prefill compatibility for an already-opened create form.
  useEffect(() => {
    if (id || !aiDraft) return;
    const slug = initial?.slug ?? "";
    const locale = initial?.locale ?? "";
    if (!slug || !locale) return;
    const draft = takeDraft(draftKey("product", slug, locale));
    if (draft) {
      setForm((prev) => ({
        ...prev,
        product_name: draft.product_name ?? prev.product_name,
        short_description: draft.short_description ?? prev.short_description,
        full_description: draft.full_description ?? prev.full_description,
        specifications: draft.specifications ?? prev.specifications,
        seo_title: draft.seo_title ?? prev.seo_title,
        seo_description: draft.seo_description ?? prev.seo_description,
        image_alt: draft.image_alt ?? prev.image_alt,
      }));
      setDraftNotice(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  useEffect(() => {
    if (!token) return;
    setCategoriesLoading(true);
    categoriesApi.list(token, { page_size: 100, locale: form.locale })
      .then((res) => setCategories(res.data.filter((category) => category.status !== "archived")))
      .catch(() => setCategories([]))
      .finally(() => setCategoriesLoading(false));
  }, [token, form.locale]);

  const handleNameChange = (v: string) => {
    const autoSlug = v.toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
    setForm((f) => ({ ...f, product_name: v, ...(!id ? { slug: autoSlug } : {}) }));
  };

  const f = (key: keyof typeof form) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleImageUpload = async (file: File) => {
    setUploading(true); setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (id) fd.append("product_id", id);
      if (form.image_alt) fd.append("alt_text", form.image_alt);
      const asset = await assetsApi.upload(token, fd);
      const nextImage = asset.public_url;
      const nextOg = form.og_image_url || nextImage;
      setForm((prev) => ({
        ...prev,
        image_url: nextImage,
        og_image_url: prev.og_image_url || nextImage,
      }));
      // 編輯模式：上傳後立刻寫入商品，避免只改表單卻未按儲存
      if (id) {
        await productsApi.update(token, id, {
          image_url: nextImage,
          og_image_url: nextOg,
          image_alt: form.image_alt || undefined,
        });
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "圖片上傳失敗");
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.status === "scheduled" && !form.publish_at) {
      setError("請選擇預約上架時間"); return;
    }
    setSaving(true); setError(null);
    try {
      const { publish_at, display_priority, ...rest } = form;
      const payload: Record<string, unknown> = {
        ...rest,
        display_priority: Number.parseInt(display_priority, 10) || 0,
      };
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
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {redirectCreated && <Alert><AlertDescription>✓ 網址已更新，已自動建立永久轉址</AlertDescription></Alert>}

      {id && (
        <LocaleSwitcher
          entityType="product"
          basePath="/dashboard/products"
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
            此為依來源語言產生的客戶語言草稿，尚未出現在公開網站。請看過品名與說明後再上架。型號、規格數字與圖片已對齊，不會被翻譯改掉。
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">產品資訊</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
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
            <Label>網址路徑 *</Label>
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
            <Label>規格說明</Label>
            <SpecRowsEditor
              value={form.specifications}
              onChange={(json) => setForm((prev) => ({ ...prev, specifications: json }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="product-category">商品分類 *</Label>
            <select
              id="product-category"
              className={SELECT_CLS}
              {...f("category_id")}
              required
              disabled={categoriesLoading}
            >
              <option value="">
                {categoriesLoading ? "載入分類中…" : "請選擇商品分類"}
              </option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.category_name}
                </option>
              ))}
            </select>
            {!categoriesLoading && categories.length === 0 && (
              <p className="text-xs text-amber-700">
                尚無可用分類，請先至「商品分類」新增分類。
              </p>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>狀態</Label>
              <select className={SELECT_CLS} {...f("status")}>
                <option value="draft">草稿</option>
                <option value="scheduled">預約上架</option>
                <option value="published">已上架</option>
                <option value="archived">已封存</option>
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
            <div className="space-y-1.5">
              <Label>列表排序</Label>
              <Input type="number" {...f("display_priority")} min={0} max={9999} />
              <p className="text-xs text-muted-foreground">數字越大越前面。與「主推」可並用。</p>
            </div>
          </div>

          {form.status === "scheduled" && (
            <div className="space-y-1.5 rounded-md border border-amber-200 bg-amber-50/60 p-3">
              <Label className="text-amber-800">預約上架時間 *</Label>
              <Input
                type="datetime-local"
                value={form.publish_at}
                onChange={(e) => setForm((prev) => ({ ...prev, publish_at: e.target.value }))}
                min={new Date().toISOString().slice(0, 16)}
                required
                className="bg-white"
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">商品主圖</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {form.image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={form.image_url} alt={form.image_alt || form.product_name} className="h-40 w-auto rounded-md border object-contain bg-muted/30" />
          )}
          <div className="space-y-1.5">
            <Label>主圖網址</Label>
            <Input {...f("image_url")} type="url" placeholder="上傳後自動填入，也可手動貼上" />
          </div>
          <div className="flex items-center gap-3">
            <label
              className={`inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border border-input bg-background px-3 text-sm shadow-sm hover:bg-accent ${uploading ? "pointer-events-none opacity-50" : ""}`}
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {uploading ? "上傳中…" : "上傳圖片"}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                className="hidden"
                disabled={uploading}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void handleImageUpload(file);
                  e.target.value = "";
                }}
              />
            </label>
            <p className="text-xs text-muted-foreground">
              {id ? "上傳後會自動寫入此商品主圖" : "新增商品請先儲存後再開啟編輯上傳，或先貼網址再儲存"}
            </p>
          </div>
          <div className="space-y-1.5">
            <Label>主圖替代文字</Label>
            <Input {...f("image_alt")} maxLength={200} />
          </div>
          <div className="space-y-1.5">
            <Label>分享預覽圖網址（可選）</Label>
            <Input {...f("og_image_url")} type="url" placeholder="空白則沿用主圖" />
          </div>
          {id ? (
            <ProductGalleryEditor
              token={token}
              productId={id}
              mainImageUrl={form.image_url}
              onMainImageChange={(url) => setForm((prev) => ({ ...prev, image_url: url, og_image_url: prev.og_image_url || url }))}
            />
          ) : (
            <p className="text-xs text-muted-foreground">儲存商品後即可上傳多張圖庫圖片。</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">搜尋標題設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>搜尋標題</Label>
            <Input {...f("seo_title")} maxLength={70} />
          </div>
          <div className="space-y-1.5">
            <Label>搜尋說明</Label>
            <Textarea {...f("seo_description")} rows={2} maxLength={160} />
          </div>
        </CardContent>
      </Card>

      {id && (
        <div className="space-y-4">
          <RelationsPanel entityType="product" entityId={id} linkType="applications" title="關聯應用場景" />
          <RelationsPanel entityType="product" entityId={id} linkType="certifications" title="關聯認證" />
          <RelationsPanel entityType="product" entityId={id} linkType="faqs" title="關聯常見問題" />
        </div>
      )}

      <div className="flex gap-3 pt-2">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "儲存中…" : "儲存"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.push("/dashboard/products")}>取消</Button>
      </div>
    </form>
  );
}
