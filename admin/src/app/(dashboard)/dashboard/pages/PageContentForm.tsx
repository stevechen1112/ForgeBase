"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { pagesApi, redirectsApi, type Page } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { LocaleSwitcher } from "@/components/ui/LocaleSwitcher";
import { SUPPORTED_LOCALES, draftKey, takeDraft } from "@/lib/i18n";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<Page>; id?: string; aiDraft?: boolean };

export default function PageContentForm({ initial, id, aiDraft }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    page_type: initial?.page_type ?? "landing",
    slug: initial?.slug ?? "",
    title: initial?.title ?? "",
    subtitle: initial?.subtitle ?? "",
    body: initial?.body ?? "",
    hero_image_url: initial?.hero_image_url ?? "",
    seo_title: initial?.seo_title ?? "",
    seo_description: initial?.seo_description ?? "",
    og_image_url: initial?.og_image_url ?? "",
    canonical_url: initial?.canonical_url ?? "",
    structured_data: initial?.structured_data ?? "",
    locale: initial?.locale ?? "en",
    status: initial?.status ?? "draft",
    noindex: initial?.noindex ?? false,
  });
  const initialSlug = useRef(initial?.slug ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [redirectCreated, setRedirectCreated] = useState(false);
  const [localeVariants, setLocaleVariants] = useState<Page[]>([]);
  const [draftNotice, setDraftNotice] = useState(false);

  useEffect(() => {
    if (id || !aiDraft) return;
    const slug = initial?.slug ?? "";
    const locale = initial?.locale ?? "";
    if (!slug || !locale) return;
    const draft = takeDraft(draftKey("page", slug, locale));
    if (draft) {
      setForm((prev) => ({
        ...prev,
        title: draft.title ?? prev.title,
        subtitle: draft.subtitle ?? prev.subtitle,
        body: draft.body ?? prev.body,
        seo_title: draft.seo_title ?? prev.seo_title,
        seo_description: draft.seo_description ?? prev.seo_description,
      }));
      setDraftNotice(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!id || !form.slug) return;
    pagesApi.list(token, { slug: form.slug, page_size: 20 })
      .then((res) => setLocaleVariants(res.data.filter((p) => p.id !== id)))
      .catch(() => {/* non-critical */});
  }, [id, form.slug, token]);

  const handleTitleChange = (v: string) => {
    const autoSlug = v.toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
    setForm((f) => ({ ...f, title: v, ...(!id ? { slug: autoSlug } : {}) }));
  };

  const f = (key: keyof typeof form) => ({
    value: typeof form[key] === "boolean" ? String(form[key]) : String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) {
        await pagesApi.update(token, id, form);
        if (form.slug && initialSlug.current && form.slug !== initialSlug.current) {
          try {
            await redirectsApi.create(token, {
              from_path: `/${initialSlug.current}`,
              to_path: `/${form.slug}`,
              status_code: 301,
              is_active: true,
              note: `Auto: page slug ${initialSlug.current} → ${form.slug}`,
            });
            setRedirectCreated(true);
          } catch { /* non-critical */ }
        }
      } else { await pagesApi.create(token, form); }
      router.push("/dashboard/pages");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {redirectCreated && <Alert><AlertDescription>✓ 網址已更新，已自動建立永久轉址</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle className="text-base">頁面設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>頁面類型</Label>
              <select className={SELECT_CLS} {...f("page_type")}>
                <option value="home">首頁</option>
                <option value="about">關於我們</option>
                <option value="contact">聯絡我們</option>
                <option value="landing">活動頁</option>
                <option value="campaign">行銷活動</option>
                <option value="custom">自訂</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>網址路徑 *</Label>
              <Input className="font-mono" {...f("slug")} required maxLength={200} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>頁面標題 *</Label>
            <Input value={form.title} onChange={(e) => handleTitleChange(e.target.value)} required maxLength={200} />
          </div>
          <div className="space-y-1.5">
            <Label>副標題</Label>
            <Input {...f("subtitle")} maxLength={300} />
          </div>
          <div className="space-y-1.5">
            <Label>主圖網址</Label>
            <Input {...f("hero_image_url")} type="url" />
          </div>
          <div className="space-y-1.5">
            <Label>頁面內容</Label>
            <Textarea
              {...f("body")}
              rows={14}
              className="font-mono text-xs"
              placeholder={'[{"type":"hero","eyebrow":"Industrial Components","title":"Precision Parts for Mission-Critical Programs","description":"Support different manufacturing verticals without rewriting the frontend.","primaryCta":{"label":"Start RFQ","href":"/rfq"}},{"type":"feature-grid","title":"Why Buyers Work With Us","items":[{"title":"Engineering Review","description":"Quote and specification alignment for custom builds."},{"title":"Production Control","description":"Repeat-order consistency across revisions."}]},{"type":"contact-form","title":"Talk to Sales","description":"Use the built-in ForgeBase contact flow."}]'}
            />
            <p className="text-xs text-muted-foreground">建議以區塊內容編輯首頁、關於我們、聯絡我們與落地頁。若填入純 HTML，前台也會正常顯示。</p>
          </div>
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
          <div className="space-y-1.5">
            <Label>分享預覽圖網址</Label>
            <Input {...f("og_image_url")} type="url" />
          </div>
          <div className="space-y-1.5">
            <Label>標準網址</Label>
            <Input {...f("canonical_url")} type="url" />
          </div>
          <div className="space-y-1.5">
            <Label>結構化資料</Label>
            <Textarea
              value={form.structured_data}
              onChange={(e) => setForm((prev) => ({ ...prev, structured_data: e.target.value }))}
              rows={8}
              className="font-mono text-xs"
              placeholder='{"@context":"https://schema.org","@type":"WebPage"}'
            />
            <p className="text-xs text-muted-foreground">貼上結構化資料（JSON 格式），供搜尋引擎理解頁面內容。適用於活動頁、常見問題、文章或自訂頁面。</p>
          </div>
          <div className="flex items-start justify-between rounded-lg border bg-muted/20 px-4 py-3">
            <div className="space-y-1 pr-4">
              <Label htmlFor="page-noindex">不索引</Label>
              <p className="text-xs text-muted-foreground">開啟後，頁面會要求搜尋引擎不要索引。適合活動過期頁、測試頁與暫存內容。</p>
            </div>
            <Switch
              id="page-noindex"
              checked={form.noindex}
              onCheckedChange={(checked) => setForm((prev) => ({ ...prev, noindex: checked }))}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>語言</Label>
              <select className={SELECT_CLS} {...f("locale")}>
                {SUPPORTED_LOCALES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>狀態</Label>
              <select className={SELECT_CLS} {...f("status")}>
                <option value="draft">草稿</option>
                <option value="published">已上架</option>
                <option value="archived">已封存</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {id && (
        <LocaleSwitcher
          entityType="page"
          basePath="/dashboard/pages"
          id={id}
          slug={form.slug}
          currentLocale={form.locale}
          variants={localeVariants.map((v) => ({ id: v.id, locale: v.locale }))}
        />
      )}

      {draftNotice && (
        <Alert className="border-violet-200 bg-violet-50">
          <AlertDescription className="text-violet-800">
            此表單已由 AI 從英文版起草，請逐欄確認用詞後再儲存。
          </AlertDescription>
        </Alert>
      )}

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
