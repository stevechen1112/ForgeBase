"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { faqsApi, type FAQItem } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AiDraftButton } from "@/components/ui/AiDraftButton";
import { SUPPORTED_LOCALES, draftKey, takeDraft } from "@/lib/i18n";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<FAQItem>; id?: string; aiDraft?: boolean };

export default function FAQForm({ initial, id, aiDraft }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    question: initial?.question ?? "",
    answer: initial?.answer ?? "",
    category_tag: initial?.category_tag ?? "",
    locale: initial?.locale ?? "en",
    sort_order: initial?.sort_order ?? 0,
    status: initial?.status ?? "draft",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftNotice, setDraftNotice] = useState(false);

  useEffect(() => {
    if (id || !aiDraft) return;
    const group = (initial as { draft_group?: string } | undefined)?.draft_group ?? initial?.category_tag ?? "";
    const locale = initial?.locale ?? "";
    if (!group || !locale) return;
    const draft = takeDraft(draftKey("faq", group, locale));
    if (draft) {
      setForm((prev) => ({
        ...prev,
        question: draft.question ?? prev.question,
        answer: draft.answer ?? prev.answer,
      }));
      setDraftNotice(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const f = (key: keyof typeof form) => ({
    value: String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await faqsApi.update(token, id, form); }
      else { await faqsApi.create(token, form); }
      router.push("/dashboard/faqs");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && (
        <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
      )}

      {draftNotice && (
        <Alert className="border-violet-200 bg-violet-50">
          <AlertDescription className="text-violet-800">
            此表單已由 AI 從英文版起草，請逐欄確認用詞後再儲存。
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">問題內容</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>問題 *</Label>
            <Input {...f("question")} required maxLength={500} />
          </div>
          <div className="space-y-1.5">
            <Label>答案 *</Label>
            <Textarea {...f("answer")} rows={6} required />
          </div>
          <div className="space-y-1.5">
            <Label>分類標籤</Label>
            <Input {...f("category_tag")} maxLength={60} />
          </div>
          <div className="grid grid-cols-3 gap-4">
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
          {id && form.locale === "en" && (
            <div className="border-t pt-3">
              <AiDraftButton
                entityType="faq"
                id={id}
                draftGroup={form.category_tag || id}
                targetLocale="zh-tw"
                newHref="/dashboard/faqs/new"
                extraQuery={{ category_tag: form.category_tag, draft_group: form.category_tag || id }}
              />
              <p className="mt-1.5 text-xs text-muted-foreground">
                AI 會將此問答翻譯成繁體中文草稿並開啟新增表單，確認後才會儲存。
              </p>
            </div>
          )}
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

