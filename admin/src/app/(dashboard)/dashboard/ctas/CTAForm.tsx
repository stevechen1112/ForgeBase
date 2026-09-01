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
import { SUPPORTED_LOCALES } from "@/lib/i18n";

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
    status: initial?.status === "active" ? "published" : initial?.status ?? "draft",
    sort_order: initial?.sort_order ?? 0,
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
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle className="text-base">行動按鈕設定</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>按鈕代碼 *</Label>
              <Input className="font-mono" {...f("cta_key")} required maxLength={80} placeholder="例：home_rfq" />
            </div>
            <div className="space-y-1.5">
              <Label>按鈕類型</Label>
              <select className={SELECT_CLS} {...f("cta_type")}>
                <option value="banner">橫幅</option>
                <option value="popup">彈出視窗</option>
                <option value="inline">內嵌</option>
                <option value="sticky">固定底欄</option>
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
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>按鈕文字</Label>
              <Input {...f("button_label")} maxLength={80} />
            </div>
            <div className="space-y-1.5">
              <Label>按鈕動作</Label>
              <select className={SELECT_CLS} {...f("button_action")}>
                <option value="link">開啟連結</option>
                <option value="modal">開啟視窗</option>
                <option value="scroll">捲動至區塊</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>按鈕連結</Label>
            <Input {...f("button_url")} maxLength={500} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>背景顏色</Label>
              <Input {...f("bg_color")} maxLength={20} placeholder="#1d4ed8" />
            </div>
            <div className="space-y-1.5">
              <Label>背景圖片網址</Label>
              <Input {...f("image_url")} type="url" />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label>語言</Label>
              <select className={SELECT_CLS} {...f("locale")}>
                {SUPPORTED_LOCALES.map((locale) => (
                  <option key={locale.value} value={locale.value}>{locale.label}</option>
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
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>排序</Label>
              <Input type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: Number(e.target.value) }))} min={0} />
            </div>
          </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-3 pt-2">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "儲存中…" : "儲存"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.push("/dashboard/ctas")}>取消</Button>
      </div>
    </form>
  );
}
