"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { briefsApi, type PageBrief } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<PageBrief>; id?: string };

export default function BriefForm({ initial, id }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    target_page_type: initial?.target_page_type ?? "product",
    target_slug: initial?.target_slug ?? "",
    title_draft: initial?.title_draft ?? "",
    audience_persona: initial?.audience_persona ?? "",
    buyer_stage: initial?.buyer_stage ?? "awareness",
    primary_keyword: initial?.primary_keyword ?? "",
    secondary_keywords: initial?.secondary_keywords ?? "",
    tone: initial?.tone ?? "professional",
    word_count_target: initial?.word_count_target ?? 800,
    main_cta_key: initial?.main_cta_key ?? "",
    notes: initial?.notes ?? "",
    locale: initial?.locale ?? "en",
  });
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const f = (key: keyof typeof form) => ({
    value: String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await briefsApi.update(token, id, form); }
      else { await briefsApi.create(token, form); }
      router.push("/dashboard/briefs");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  const handleGenerate = async () => {
    if (!id) return;
    setGenerating(true); setError(null);
    try {
      const res = await fetch(`/api/v1/content/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ brief_id: id }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail ?? `HTTP ${res.status}`);
      }
      router.push("/dashboard/briefs");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "AI generation failed"); }
    finally { setGenerating(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">基本設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>目標頁面類型 *</Label>
              <select className={SELECT_CLS} {...f("target_page_type")}>
                <option value="product">Product</option>
                <option value="application">Application</option>
                <option value="category">Category</option>
                <option value="comparison">Comparison</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>目標 Slug</Label>
              <Input className="font-mono" {...f("target_slug")} maxLength={150} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>草稿標題</Label>
            <Input {...f("title_draft")} maxLength={200} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>目標受眾</Label>
              <Input {...f("audience_persona")} maxLength={200} placeholder="e.g. 採購工程師" />
            </div>
            <div className="space-y-1.5">
              <Label>買家歷程階段</Label>
              <select className={SELECT_CLS} {...f("buyer_stage")}>
                <option value="awareness">Awareness</option>
                <option value="consideration">Consideration</option>
                <option value="decision">Decision</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">SEO 關鍵字設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>主要關鍵字</Label>
            <Input {...f("primary_keyword")} maxLength={100} />
          </div>
          <div className="space-y-1.5">
            <Label>次要關鍵字 (逗號分隔)</Label>
            <Input {...f("secondary_keywords")} maxLength={500} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">內容規格</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <Label>文字風格</Label>
              <select className={SELECT_CLS} {...f("tone")}>
                <option value="professional">Professional</option>
                <option value="technical">Technical</option>
                <option value="friendly">Friendly</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>目標字數</Label>
              <Input type="number" value={form.word_count_target} onChange={(e) => setForm((f) => ({ ...f, word_count_target: Number(e.target.value) }))} min={100} max={5000} />
            </div>
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
          </div>
          <div className="space-y-1.5">
            <Label>主要 CTA Key</Label>
            <Input className="font-mono" {...f("main_cta_key")} maxLength={80} />
          </div>
          <div className="space-y-1.5">
            <Label>備註</Label>
            <Textarea {...f("notes")} rows={3} />
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3 pt-2">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "儲存中…" : "儲存"}
        </Button>
        {id && (
          <Button type="button" variant="secondary" onClick={handleGenerate} disabled={generating}>
            {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {generating ? "AI 生成中…" : "觸發 AI 生成"}
          </Button>
        )}
        <Button type="button" variant="outline" onClick={() => router.back()}>取消</Button>
      </div>
    </form>
  );
}
