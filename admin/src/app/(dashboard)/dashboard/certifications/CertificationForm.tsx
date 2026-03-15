"use client";
import { useState } from "react";
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

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type Props = { initial?: Partial<Certification>; id?: string };

function slugifyValue(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120);
}

export default function CertificationForm({ initial, id }: Props) {
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
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-5">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle className="text-base">認證基本資訊</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>認證名稱 *</Label>
            <Input {...f("cert_name")} required maxLength={200} />
          </div>
          <div className="space-y-1.5">
            <Label>Slug *</Label>
            <Input className="font-mono" {...f("slug")} required maxLength={120} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>頒發機構</Label>
              <Input {...f("issuer")} maxLength={200} />
            </div>
            <div className="space-y-1.5">
              <Label>認證編號</Label>
              <Input className="font-mono" {...f("cert_number")} maxLength={100} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
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
            <Label>徽章圖片 URL</Label>
            <Input {...f("badge_image_url")} type="url" />
          </div>
          <div className="space-y-1.5">
            <Label>文件 URL</Label>
            <Input {...f("document_url")} type="url" />
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
