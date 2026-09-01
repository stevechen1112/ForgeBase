"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { comparisonsApi, type ComparisonTopic } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { LocaleSwitcher } from "@/components/ui/LocaleSwitcher";
import { SUPPORTED_LOCALES, draftKey, takeDraft } from "@/lib/i18n";
import { ComparisonDimensionsEditor } from "@/components/content/ComparisonDimensionsEditor";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<ComparisonTopic>; id?: string; aiDraft?: boolean };

export default function ComparisonForm({ initial, id, aiDraft }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    topic_title: initial?.topic_title ?? "",
    slug: initial?.slug ?? "",
    summary: initial?.summary ?? "",
    dimensions: initial?.dimensions ?? "",
    conclusion: initial?.conclusion ?? "",
    seo_title: initial?.seo_title ?? "",
    seo_description: initial?.seo_description ?? "",
    status: initial?.status ?? "draft",
    locale: initial?.locale ?? "zh-tw",
    sort_order: initial?.sort_order ?? 0,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localeVariants, setLocaleVariants] = useState<ComparisonTopic[]>([]);
  const [draftNotice, setDraftNotice] = useState(false);

  useEffect(() => {
    if (id || !aiDraft) return;
    const slug = initial?.slug ?? "";
    const locale = initial?.locale ?? "";
    if (!slug || !locale) return;
    const draft = takeDraft(draftKey("comparison", slug, locale));
    if (draft) {
      setForm((prev) => ({
        ...prev,
        topic_title: draft.topic_title ?? prev.topic_title,
        summary: draft.summary ?? prev.summary,
        conclusion: draft.conclusion ?? prev.conclusion,
      }));
      setDraftNotice(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!id || !form.slug) return;
    comparisonsApi.list(token, { slug: form.slug, page_size: 20 })
      .then((res) => setLocaleVariants(res.data.filter((c) => c.id !== id)))
      .catch(() => {/* non-critical */});
  }, [id, form.slug, token]);

  const handleTitleChange = (v: string) => {
    const autoSlug = v.toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
    setForm((f) => ({ ...f, topic_title: v, ...(!id ? { slug: autoSlug } : {}) }));
  };

  const f = (key: keyof typeof form) => ({
    value: String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await comparisonsApi.update(token, id, form); }
      else { await comparisonsApi.create(token, form); }
      router.push("/dashboard/comparisons");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {id && (
        <LocaleSwitcher
          entityType="comparison"
          basePath="/dashboard/comparisons"
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
            <Label>比較主題 *</Label>
            <Input value={form.topic_title} onChange={(e) => handleTitleChange(e.target.value)} required maxLength={200} />
          </div>
          <div className="space-y-1.5">
            <Label>網址路徑 *</Label>
            <Input className="font-mono" {...f("slug")} required maxLength={200} />
          </div>
          <div className="space-y-1.5">
            <Label>摘要</Label>
            <Textarea {...f("summary")} rows={3} maxLength={500} />
          </div>
          <div className="space-y-1.5">
            <Label>比較項目</Label>
            <ComparisonDimensionsEditor value={form.dimensions} onChange={(dimensions) => setForm((current) => ({ ...current, dimensions }))} />
          </div>
          <div className="space-y-1.5">
            <Label>結論</Label>
            <Textarea {...f("conclusion")} rows={3} />
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
        </CardContent>
      </Card>

      <div className="flex gap-3 pt-2">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "儲存中…" : "儲存"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.push("/dashboard/comparisons")}>取消</Button>
      </div>
    </form>
  );
}
