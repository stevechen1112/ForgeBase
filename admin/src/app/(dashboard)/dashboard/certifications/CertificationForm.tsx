"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { certificationsApi, type Certification } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { LocaleSwitcher } from "@/components/ui/LocaleSwitcher";
import { SUPPORTED_LOCALES, draftKey, takeDraft } from "@/lib/i18n";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<Certification>; id?: string; aiDraft?: boolean };

function slugifyValue(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120);
}

export default function CertificationForm({ initial, id, aiDraft }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    cert_name: initial?.cert_name ?? "",
    slug: initial?.slug ?? "",
    issuer: initial?.issuer ?? "",
    cert_number: initial?.cert_number ?? "",
    issued_at: initial?.issued_at ?? "",
    expires_at: initial?.expires_at ?? "",
    description: initial?.description ?? "",
    badge_image_url: initial?.badge_image_url ?? "",
    document_url: initial?.document_url ?? "",
    locale: initial?.locale ?? "zh-tw",
    status: initial?.status ?? "draft",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slugEdited, setSlugEdited] = useState(Boolean(initial?.slug));
  const [localeVariants, setLocaleVariants] = useState<Certification[]>([]);
  const [draftNotice, setDraftNotice] = useState(false);

  useEffect(() => {
    if (id || !aiDraft) return;
    const slug = initial?.slug ?? "";
    const locale = initial?.locale ?? "";
    if (!slug || !locale) return;
    const draft = takeDraft(draftKey("certification", slug, locale));
    if (draft) {
      setForm((prev) => ({
        ...prev,
        cert_name: draft.cert_name ?? prev.cert_name,
        description: draft.description ?? prev.description,
      }));
      setDraftNotice(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!id || !form.slug) return;
    certificationsApi.list(token, { slug: form.slug, page_size: 20 })
      .then((res) => setLocaleVariants(res.data.filter((c) => c.id !== id)))
      .catch(() => {/* non-critical */});
  }, [id, form.slug, token]);

  const f = (key: keyof typeof form) => ({
    value: String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const nextValue = e.target.value;
      setForm((prev) => {
        const next = { ...prev, [key]: nextValue };
        if (key === "cert_name" && !slugEdited) next.slug = slugifyValue(nextValue);
        if (key === "slug") { next.slug = slugifyValue(nextValue); setSlugEdited(true); }
        return next;
      });
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await certificationsApi.update(token, id, form); }
      else { await certificationsApi.create(token, form); }
      router.push("/dashboard/certifications");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {id && (
        <LocaleSwitcher
          entityType="certification"
          basePath="/dashboard/certifications"
          id={id}
          slug={form.slug}
          currentLocale={form.locale}
          currentStatus={form.status}
          currentUpdatedAt={initial?.updated_at}
          variants={localeVariants.map((v) => ({ id: v.id, locale: v.locale, status: v.status, updated_at: (v as { updated_at?: string }).updated_at }))}
        />
      )}

      {draftNotice && (
        <Alert className="border-violet-200 bg-violet-50">
          <AlertDescription className="text-violet-800">
            此為依來源語系產生的買方語系草稿，尚未出現在公開網站。請看過後再上架。
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">認證基本資訊</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>認證名稱 *</Label>
            <Input {...f("cert_name")} required maxLength={200} />
          </div>
          <div className="space-y-1.5">
            <Label>網址路徑 *</Label>
            <Input className="font-mono" {...f("slug")} required maxLength={120} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>頒發機構</Label>
              <Input {...f("issuer")} maxLength={200} />
            </div>
            <div className="space-y-1.5">
              <Label>認證編號</Label>
              <Input className="font-mono" {...f("cert_number")} maxLength={100} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>頒發日期</Label>
              <Input type="date" {...f("issued_at")} />
            </div>
            <div className="space-y-1.5">
              <Label>到期日期</Label>
              <Input type="date" {...f("expires_at")} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>描述</Label>
            <Textarea {...f("description")} rows={3} />
          </div>
          <div className="space-y-1.5">
            <Label>徽章圖片網址</Label>
            <Input {...f("badge_image_url")} type="url" />
          </div>
          <div className="space-y-1.5">
            <Label>文件網址</Label>
            <Input {...f("document_url")} type="url" />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
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

      <div className="flex gap-3 pt-2">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "儲存中…" : "儲存"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.push("/dashboard/certifications")}>取消</Button>
      </div>
    </form>
  );
}
