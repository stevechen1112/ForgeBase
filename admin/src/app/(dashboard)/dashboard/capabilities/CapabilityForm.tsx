"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { capabilitiesApi, type Capability } from "@/lib/api/content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<Capability>; id?: string };

function slugifyValue(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 100);
}

export default function CapabilityForm({ initial, id }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [form, setForm] = useState({
    capability_name: initial?.capability_name ?? "",
    slug: initial?.slug ?? "",
    short_description: initial?.short_description ?? "",
    detail: initial?.detail ?? "",
    metrics: initial?.metrics ?? "",
    category_tag: initial?.category_tag ?? "",
    icon_url: initial?.icon_url ?? "",
    image_url: initial?.image_url ?? "",
    sort_order: initial?.sort_order ?? 0,
    locale: initial?.locale ?? "en",
    status: initial?.status ?? "draft",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slugEdited, setSlugEdited] = useState(Boolean(initial?.slug));

  const f = (key: keyof typeof form) => ({
    value: String(form[key]),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const nextValue = e.target.value;
      setForm((prev) => {
        const next = { ...prev, [key]: nextValue };
        if (key === "capability_name" && !slugEdited) next.slug = slugifyValue(nextValue);
        if (key === "slug") { next.slug = slugifyValue(nextValue); setSlugEdited(true); }
        return next;
      });
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      if (id) { await capabilitiesApi.update(token, id, form); }
      else { await capabilitiesApi.create(token, form); }
      router.push("/dashboard/capabilities");
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "儲存失敗"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle className="text-base">廠能資訊</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>廠能名稱 *</Label>
            <Input {...f("capability_name")} required maxLength={150} />
          </div>
          <div className="space-y-1.5">
            <Label>網址路徑 *</Label>
            <Input className="font-mono" {...f("slug")} required maxLength={100} />
          </div>
          <div className="space-y-1.5">
            <Label>簡短描述</Label>
            <Textarea {...f("short_description")} rows={2} maxLength={300} />
          </div>
          <div className="space-y-1.5">
            <Label>詳細說明</Label>
            <Textarea {...f("detail")} rows={6} />
          </div>
          <div className="space-y-1.5">
            <Label>指標數據（例如：精度 ±0.01mm）</Label>
            <Input {...f("metrics")} maxLength={500} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>分類標籤</Label>
              <Input {...f("category_tag")} maxLength={80} />
            </div>
            <div className="space-y-1.5">
              <Label>排序</Label>
              <Input type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: Number(e.target.value) }))} min={0} />
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
            <div className="space-y-1.5 col-span-2">
              <Label>狀態</Label>
              <select className={SELECT_CLS} {...f("status")}>
                <option value="draft">草稿</option>
                <option value="published">已上架</option>
                <option value="archived">已封存</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>圖示網址</Label>
            <Input {...f("icon_url")} type="url" />
          </div>
          <div className="space-y-1.5">
            <Label>圖片網址</Label>
            <Input {...f("image_url")} type="url" />
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
