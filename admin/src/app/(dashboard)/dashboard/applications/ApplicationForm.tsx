"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { applicationsApi, type Application } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RelationsPanel } from "@/components/ui/RelationsPanel";
import { LocaleSwitcher } from "@/components/ui/LocaleSwitcher";
import { SUPPORTED_LOCALES, draftKey, takeDraft } from "@/lib/i18n";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<Application>; id?: string; aiDraft?: boolean };

export default function ApplicationForm({ initial, id, aiDraft }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    application_name: initial?.application_name ?? "",
    slug: initial?.slug ?? "",
    industry: initial?.industry ?? "",
    description: initial?.description ?? "",
    challenge: initial?.challenge ?? "",
    solution: initial?.solution ?? "",
    hero_image_url: initial?.hero_image_url ?? "",
    og_image_url: initial?.og_image_url ?? "",
    seo_title: initial?.seo_title ?? "",
    seo_description: initial?.seo_description ?? "",
    status: initial?.status ?? "draft",
    locale: initial?.locale ?? "zh-tw",
    sort_order: initial?.sort_order ?? 0,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localeVariants, setLocaleVariants] = useState<Application[]>([]);
  const [draftNotice, setDraftNotice] = useState(false);

  // Legacy manual form-prefill compatibility for an already-opened create form.
  useEffect(() => {
    if (id || !aiDraft) return;
    const slug = initial?.slug ?? "";
    const locale = initial?.locale ?? "";
    if (!slug || !locale) return;
    const draft = takeDraft(draftKey("application", slug, locale));
    if (draft) {
      setForm((prev) => ({
        ...prev,
        application_name: draft.application_name ?? prev.application_name,
        industry: draft.industry ?? prev.industry,
        description: draft.description ?? prev.description,
        challenge: draft.challenge ?? prev.challenge,
        solution: draft.solution ?? prev.solution,
        seo_title: draft.seo_title ?? prev.seo_title,
        seo_description: draft.seo_description ?? prev.seo_description,
      }));
      setDraftNotice(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!id || !form.slug) return;
    applicationsApi.list(token, { slug: form.slug, page_size: 20 })
      .then((res) => setLocaleVariants(res.data.filter((a: Application) => a.id !== id)))
      .catch(() => {/* non-critical */});
  }, [id, form.slug, token]);

  const handleNameChange = (v: string) => {
    const autoSlug = v.toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
    setForm((f) => ({ ...f, application_name: v, ...(!id ? { slug: autoSlug } : {}) }));
  };

  const f = (key: keyof typeof form) => ({
    value: String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await applicationsApi.update(token, id, form); }
      else { await applicationsApi.create(token, form); }
      router.push("/dashboard/applications");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {id && (
        <LocaleSwitcher
          entityType="application"
          basePath="/dashboard/applications"
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
        <CardHeader><CardTitle className="text-base">應用場景資訊</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>應用場景名稱 *</Label>
              <Input value={form.application_name} onChange={(e) => handleNameChange(e.target.value)} required maxLength={120} />
            </div>
            <div className="space-y-1.5">
              <Label>產業 *</Label>
              <Input {...f("industry")} required maxLength={80} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>網址路徑 *</Label>
            <Input className="font-mono" {...f("slug")} required pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$" maxLength={100} />
          </div>
          <div className="space-y-1.5">
            <Label>描述</Label>
            <Textarea {...f("description")} rows={3} />
          </div>
          <div className="space-y-1.5">
            <Label>客戶痛點</Label>
            <Textarea {...f("challenge")} rows={3} />
          </div>
          <div className="space-y-1.5">
            <Label>解決方案</Label>
            <Textarea {...f("solution")} rows={3} />
          </div>
          <div className="space-y-1.5">
            <Label>主圖網址</Label>
            <Input {...f("hero_image_url")} type="url" />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label>排序</Label>
              <Input type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: Number(e.target.value) }))} min={0} />
            </div>
            <div className="space-y-1.5">
              <Label>狀態</Label>
              <select className={SELECT_CLS} {...f("status")}>
                <option value="draft">草稿</option>
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
            <Input {...f("og_image_url")} type="url" placeholder="https://.../application-og.jpg" />
            <p className="text-xs text-muted-foreground">若未填寫，前台會改用主圖網址。</p>
          </div>
        </CardContent>
      </Card>

      {id && (
        <RelationsPanel entityType="application" entityId={id} linkType="faqs" title="關聯常見問題" />
      )}

      <div className="flex gap-3 pt-2">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "儲存中…" : "儲存"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.push("/dashboard/applications")}>取消</Button>
      </div>
    </form>
  );
}
