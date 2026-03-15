"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { ctasApi, type CTA } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<CTA>; id?: string };

export default function CTAForm({ initial, id }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    cta_key: initial?.cta_key ?? "",
    cta_type: initial?.cta_type ?? "banner",
    headline: initial?.headline ?? "",
    subheadline: initial?.subheadline ?? "",
    button_label: initial?.button_label ?? "",
    button_action: initial?.button_action ?? "link",
    button_url: initial?.button_url ?? "",
    bg_color: initial?.bg_color ?? "",
    image_url: initial?.image_url ?? "",
    locale: initial?.locale ?? "en",
    status: initial?.status ?? "draft",
    sort_order: initial?.sort_order ?? 0,
    target_intent_stage: initial?.target_intent_stage ?? "any",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const f = (key: keyof typeof form) => ({
    value: String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value })),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await ctasApi.update(token, id, form); }
      else { await ctasApi.create(token, form); }
      router.push("/dashboard/ctas");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle className="text-base">CTA 設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>CTA Key *</Label>
              <Input className="font-mono" {...f("cta_key")} required maxLength={80} placeholder="e.g. hero_home" />
            </div>
            <div className="space-y-1.5">
              <Label>CTA 類型</Label>
              <select className={SELECT_CLS} {...f("cta_type")}>
                <option value="banner">Banner</option>
                <option value="popup">Popup</option>
                <option value="inline">Inline</option>
                <option value="sticky">Sticky Bar</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>標題</Label>
            <Input {...f("headline")} maxLength={200} />
          </div>
          <div className="space-y-1.5">
            <Label>副標題</Label>
            <Input {...f("subheadline")} maxLength={300} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>按鈕文字</Label>
              <Input {...f("button_label")} maxLength={80} />
            </div>
            <div className="space-y-1.5">
              <Label>按鈕動作</Label>
              <select className={SELECT_CLS} {...f("button_action")}>
                <option value="link">Link</option>
                <option value="modal">Modal</option>
                <option value="scroll">Scroll</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>按鈕目標 URL</Label>
            <Input {...f("button_url")} maxLength={500} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>背景顏色 (hex)</Label>
              <Input {...f("bg_color")} maxLength={20} placeholder="#1d4ed8" />
            </div>
            <div className="space-y-1.5">
              <Label>背景圖片 URL</Label>
              <Input {...f("image_url")} type="url" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
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
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>目標意圖階段</Label>
              <select className={SELECT_CLS} {...f("target_intent_stage")}>
                <option value="any">不限 (Any)</option>
                <option value="cold">Cold — 初次瀏覽</option>
                <option value="warm">Warm — 多次互動</option>
                <option value="hot">Hot — 高意圖</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>排序</Label>
              <Input type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: Number(e.target.value) }))} min={0} />
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
