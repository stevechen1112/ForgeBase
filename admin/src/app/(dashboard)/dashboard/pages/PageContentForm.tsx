"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { pagesApi, type Page } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<Page>; id?: string };

export default function PageContentForm({ initial, id }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    page_type: initial?.page_type ?? "custom",
    slug: initial?.slug ?? "",
    title: initial?.title ?? "",
    subtitle: initial?.subtitle ?? "",
    body: initial?.body ?? "",
    hero_image_url: initial?.hero_image_url ?? "",
    seo_title: initial?.seo_title ?? "",
    seo_description: initial?.seo_description ?? "",
    og_image_url: initial?.og_image_url ?? "",
    canonical_url: initial?.canonical_url ?? "",
    locale: initial?.locale ?? "en",
    status: initial?.status ?? "draft",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTitleChange = (v: string) => {
    const autoSlug = v.toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
    setForm((f) => ({ ...f, title: v, ...(!id ? { slug: autoSlug } : {}) }));
  };

  const f = (key: keyof typeof form) => ({
    value: String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await pagesApi.update(token, id, form); }
      else { await pagesApi.create(token, form); }
      router.push("/dashboard/pages");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle className="text-base">頁面設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>頁面類型</Label>
              <select className={SELECT_CLS} {...f("page_type")}>
                <option value="custom">Custom</option>
                <option value="about">About</option>
                <option value="contact">Contact</option>
                <option value="landing">Landing</option>
                <option value="campaign">Campaign</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Slug *</Label>
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
            <Label>Hero 圖片 URL</Label>
            <Input {...f("hero_image_url")} type="url" />
          </div>
          <div className="space-y-1.5">
            <Label>頁面內容 (HTML / Markdown)</Label>
            <Textarea {...f("body")} rows={10} className="font-mono text-xs" />
          </div>
        </CardContent>
      </Card>

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
            <Input {...f("og_image_url")} type="url" />
          </div>
          <div className="space-y-1.5">
            <Label>Canonical URL</Label>
            <Input {...f("canonical_url")} type="url" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>語言</Label>
              <select className={SELECT_CLS} {...f("locale")}>
                <option value="en">English</option>
                <option value="zh-tw">繁體中文</option>
                <option value="zh-cn">简体中文</option>
                <option value="ja">日本語</option>
                <option value="ko">한국어</option>
                <option value="de">Deutsch</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>狀態</Label>
              <select className={SELECT_CLS} {...f("status")}>
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>
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
