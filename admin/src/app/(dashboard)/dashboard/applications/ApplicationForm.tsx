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

type Props = { initial?: Partial<Application>; id?: string };

export default function ApplicationForm({ initial, id }: Props) {
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
    seo_title: initial?.seo_title ?? "",
    seo_description: initial?.seo_description ?? "",
    status: initial?.status ?? "draft",
    locale: initial?.locale ?? "en",
    sort_order: initial?.sort_order ?? 0,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localeVariants, setLocaleVariants] = useState<Application[]>([]);

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
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle className="text-base">應用場景資訊</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
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
            <Label>Slug *</Label>
            <Input className="font-mono" {...f("slug")} required pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$" maxLength={100} />
          </div>
          <div className="space-y-1.5">
            <Label>描述</Label>
            <Textarea {...f("description")} rows={3} />
          </div>
          <div className="space-y-1.5">
            <Label>挑戰 (Challenge)</Label>
            <Textarea {...f("challenge")} rows={3} />
          </div>
          <div className="space-y-1.5">
            <Label>解決方案 (Solution)</Label>
            <Textarea {...f("solution")} rows={3} />
          </div>
          <div className="space-y-1.5">
            <Label>Hero Image URL</Label>
            <Input {...f("hero_image_url")} type="url" />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <Label>排序</Label>
              <Input type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: Number(e.target.value) }))} min={0} />
            </div>
            <div className="space-y-1.5">
              <Label>狀態</Label>
              <select className={SELECT_CLS} {...f("status")}>
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
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
                <a key={v.id} href={`/dashboard/applications/${v.id}/edit`}>
                  <Badge variant="outline" className="border-green-500 text-green-700 hover:bg-green-50 cursor-pointer">
                    {SUPPORTED_LOCALES.find((l) => l.value === v.locale)?.label ?? v.locale} ✓
                  </Badge>
                </a>
              ))}
              {SUPPORTED_LOCALES.filter(
                (l) => l.value !== form.locale && !localeVariants.some((v) => v.locale === l.value)
              ).map((l) => (
                <a key={l.value} href={`/dashboard/applications/new?slug=${encodeURIComponent(form.slug)}&locale=${l.value}`}>
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
