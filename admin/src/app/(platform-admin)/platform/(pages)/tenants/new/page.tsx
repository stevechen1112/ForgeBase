"use client";

import { useEffect, useId, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type SiteTemplate, type TenantProvision } from "@/lib/api/platform-admin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PUBLIC_SITE_LOCALES } from "@/lib/i18n";

const initialForm: TenantProvision = {
  name: "", slug: "", owner_email: "", owner_full_name: "", temporary_password: "",
  template_key: "handtool-company", brand_name: "", logo_mark: "", contact_email: "", contact_phone: "",
  site_url: "https://", primary_domain: "", default_locale: "zh-TW", locales: ["zh-TW", "en"], theme_key: "cobalt", layout_key: "classic",
};

export default function NewTenantPage() {
  const router = useRouter();
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;
  const [templates, setTemplates] = useState<SiteTemplate[]>([]);
  const [form, setForm] = useState<TenantProvision>(initialForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (token) platformAdminApi.siteTemplates(token).then(setTemplates).catch((e) => setError(e.message)); }, [token]);
  const field = (name: keyof TenantProvision, value: string) => setForm((current) => ({ ...current, [name]: value }));
  const toggleLocale = (locale: string) => setForm((current) => ({
    ...current,
    locales: current.locales.includes(locale)
      ? current.locales.filter((item) => item !== locale)
      : [...current.locales, locale],
  }));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSaving(true); setError("");
    try {
      const result = await platformAdminApi.provisionTenant(token, form);
      router.push(`/platform/tenants/${result.tenant_id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "開通失敗");
    } finally { setSaving(false); }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <button type="button" onClick={() => router.push("/platform/tenants")} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />返回租戶</button>
      <div><h1 className="text-2xl font-bold">開通新租戶</h1><p className="mt-1 text-sm text-muted-foreground">一次建立租戶、負責人、品牌設定與網站交付單。</p></div>
      <form onSubmit={submit} className="space-y-6">
        {error && <div role="alert" aria-live="polite" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <section className="rounded-xl border bg-card p-5"><h2 className="font-semibold">公司與網站範本</h2><div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="公司名稱" value={form.name} onChange={(v) => field("name", v)} required />
          <Field label="租戶代碼（小寫英文與連字號）" value={form.slug} onChange={(v) => field("slug", v)} required />
          <SelectField label="網站範本" value={form.template_key} onChange={(v) => field("template_key", v)} options={templates.map((t) => ({ value: t.key, label: `${t.name}${t.publish_supported ? "（可串接發布）" : "（靜態展示）"}` }))} />
        </div></section>
        <section className="rounded-xl border bg-card p-5"><h2 className="font-semibold">第一位負責人</h2><div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="姓名" value={form.owner_full_name} onChange={(v) => field("owner_full_name", v)} required />
          <Field label="Email" type="email" value={form.owner_email} onChange={(v) => field("owner_email", v)} required />
          <Field label="臨時密碼（至少 12 字元）" type="password" value={form.temporary_password} onChange={(v) => field("temporary_password", v)} required />
        </div></section>
        <section className="rounded-xl border bg-card p-5"><h2 className="font-semibold">品牌與網域</h2><div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="品牌名稱" value={form.brand_name} onChange={(v) => field("brand_name", v)} required />
          <Field label="品牌縮寫" value={form.logo_mark} onChange={(v) => field("logo_mark", v)} required />
          <Field label="對外聯絡 Email" type="email" value={form.contact_email} onChange={(v) => field("contact_email", v)} required />
          <Field label="聯絡電話" value={form.contact_phone || ""} onChange={(v) => field("contact_phone", v)} />
          <Field label="完整網站網址" value={form.site_url} onChange={(v) => field("site_url", v)} required />
          <Field label="主要網域" value={form.primary_domain || ""} onChange={(v) => field("primary_domain", v)} placeholder="example.com" />
        </div><fieldset className="mt-4"><legend className="text-sm font-medium">公開網站語系</legend><p className="mt-1 text-xs text-muted-foreground">只勾選已完成內容檢查、準備對外發布的語系。</p><div className="mt-2 flex flex-wrap gap-4">{PUBLIC_SITE_LOCALES.map((locale) => <label key={locale.value} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.locales.includes(locale.value)} onChange={() => toggleLocale(locale.value)} />{locale.label}</label>)}</div></fieldset></section>
        <div className="flex justify-end"><Button type="submit" disabled={saving || form.locales.length === 0}>{saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{saving ? "開通中" : "建立租戶與交付單"}</Button></div>
      </form>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", required, placeholder }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean; placeholder?: string }) {
  const id = useId();
  return <div className="space-y-2"><Label htmlFor={id}>{label}</Label><Input id={id} type={type} value={value} onChange={(e) => onChange(e.target.value)} required={required} placeholder={placeholder} /></div>;
}

function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: { value: string; label: string }[] }) {
  const id = useId();
  return <div className="space-y-2"><Label htmlFor={id}>{label}</Label><select id={id} className="h-10 w-full rounded-md border bg-background px-3 text-sm" value={value} onChange={(e) => onChange(e.target.value)}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>;
}
