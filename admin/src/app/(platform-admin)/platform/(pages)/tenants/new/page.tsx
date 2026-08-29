"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, TriangleAlert } from "lucide-react";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type SiteTemplate, type TenantProvision, type TenantProvisionPreflight } from "@/lib/api/platform-admin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PUBLIC_SITE_LOCALES } from "@/lib/i18n";

const initialForm: TenantProvision = {
  name: "", slug: "", owner_email: "", owner_full_name: "", temporary_password: "",
  template_key: "handtool-company", brand_name: "", logo_mark: "", contact_email: "", contact_phone: "",
  primary_domain: "", default_locale: "zh-TW", locales: ["zh-TW", "en"], theme_key: "cobalt", layout_key: "classic",
};

const PREFLIGHT_LABELS: Record<string, string> = {
  tenant_slug_available: "租戶代碼未被使用",
  forgebase_subdomain_valid: "可建立免費 ForgeBase 子網域",
  forgebase_subdomain_available: "免費子網域尚未被使用",
  owner_email_available: "負責人 Email 未被使用",
  template_publishable: "範本具備正式 CMS 串接能力",
  https_site_url: "網站網址使用 HTTPS",
  site_url_has_no_credentials: "網站網址不含帳密",
  site_url_has_no_query_or_fragment: "網站網址不含查詢參數或片段",
  site_url_uses_standard_port: "網站網址使用標準 HTTPS 連接埠",
  primary_domain_valid: "免費網址／選填自有網域格式有效",
  primary_domain_available: "免費網址／選填自有網域未被使用",
  domain_matches_site_url: "預檢網址與網域一致",
  locale_set_supported: "公開語系集合有效",
  default_locale_enabled: "預設語系已包含在公開語系",
};

export default function NewTenantPage() {
  const router = useRouter();
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;
  const [templates, setTemplates] = useState<SiteTemplate[]>([]);
  const [form, setForm] = useState<TenantProvision>(initialForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [preflight, setPreflight] = useState<TenantProvisionPreflight | null>(null);
  const idempotencyKeyRef = useRef("");
  const managedHostname = form.slug
    ? `${form.slug.trim().toLowerCase()}.forgebase.com`
    : "your-company.forgebase.com";

  useEffect(() => { if (token) platformAdminApi.siteTemplates(token).then(setTemplates).catch((e) => setError(e.message)); }, [token]);
  const invalidatePreflight = () => {
    setPreflight(null);
    idempotencyKeyRef.current = "";
  };
  const field = (name: keyof TenantProvision, value: string) => {
    invalidatePreflight();
    setForm((current) => ({ ...current, [name]: value }));
  };
  const toggleLocale = (locale: string) => {
    invalidatePreflight();
    setForm((current) => {
      const locales = current.locales.includes(locale)
        ? current.locales.filter((item) => item !== locale)
        : [...current.locales, locale];
      return {
        ...current,
        locales,
        default_locale: locales.includes(current.default_locale)
          ? current.default_locale
          : (locales[0] || current.default_locale),
      };
    });
  };

  async function checkPreflight() {
    if (!token) return null;
    setChecking(true); setError("");
    try {
      const result = await platformAdminApi.preflightTenant(token, form);
      setPreflight(result);
      return result;
    } catch (cause) {
      setPreflight(null);
      setError(cause instanceof Error ? cause.message : "交付規格檢查失敗");
      return null;
    } finally { setChecking(false); }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSaving(true); setError("");
    try {
      const checked = await platformAdminApi.preflightTenant(token, form);
      setPreflight(checked);
      if (!checked.ready) {
        setError("交付規格仍有阻擋項目，請先修正後再建立。");
        return;
      }
      if (!idempotencyKeyRef.current) idempotencyKeyRef.current = crypto.randomUUID();
      const result = await platformAdminApi.provisionTenant(token, form, idempotencyKeyRef.current);
      router.push(`/platform/tenants/${result.tenant_id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "開通失敗");
    } finally { setSaving(false); }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
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
        <section className="rounded-xl border bg-card p-5"><h2 className="font-semibold">品牌與初始網址</h2><p className="mt-1 text-xs text-muted-foreground">租戶建立後會立即取得免費子網域。自有網域只會先建立 DNS 驗證工作，不會在未驗證前取代免費網址。</p><div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="品牌名稱" value={form.brand_name} onChange={(v) => field("brand_name", v)} required />
          <Field label="品牌縮寫" value={form.logo_mark} onChange={(v) => field("logo_mark", v)} required />
          <Field label="對外聯絡 Email" type="email" value={form.contact_email} onChange={(v) => field("contact_email", v)} required />
          <Field label="聯絡電話" value={form.contact_phone || ""} onChange={(v) => field("contact_phone", v)} />
          <div className="space-y-2"><Label>免費 ForgeBase 網址</Label><div className="flex h-10 items-center rounded-md border border-blue-200 bg-blue-50 px-3 font-mono text-sm text-blue-950">https://{managedHostname}</div><p className="text-xs text-muted-foreground">由 ForgeBase 管理 DNS 與 TLS，可直接作為租戶正式網址。</p></div>
          <Field label="租戶自有網域（選填）" value={form.primary_domain || ""} onChange={(v) => field("primary_domain", v)} placeholder="www.customer.com" />
        </div><fieldset className="mt-4"><legend className="text-sm font-medium">公開網站語系</legend><p className="mt-1 text-xs text-muted-foreground">只勾選已完成內容檢查、準備對外發布的語系。</p><div className="mt-2 flex flex-wrap gap-4">{PUBLIC_SITE_LOCALES.map((locale) => <label key={locale.value} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.locales.includes(locale.value)} onChange={() => toggleLocale(locale.value)} />{locale.label}</label>)}</div><div className="mt-4 max-w-xs"><SelectField label="預設語系" value={form.default_locale} onChange={(v) => field("default_locale", v)} options={PUBLIC_SITE_LOCALES.filter((locale) => form.locales.includes(locale.value)).map((locale) => ({ value: locale.value, label: locale.label }))} /></div></fieldset></section>
        <section className="rounded-xl border bg-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">交付規格預檢</h2><p className="mt-1 text-xs text-muted-foreground">只驗證，不建立任何租戶或帳號；正式建立時會再次檢查。</p></div><Button type="button" variant="outline" onClick={() => void checkPreflight()} disabled={checking || saving}>{checking && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}檢查交付規格</Button></div>
          {preflight && <div className="mt-4 grid gap-2 sm:grid-cols-2">{Object.entries(preflight.checks).map(([key, passed]) => <div key={key} className={`flex items-center gap-2 rounded border px-3 py-2 text-xs ${passed ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-900"}`}>{passed ? <ShieldCheck className="h-4 w-4 shrink-0" /> : <TriangleAlert className="h-4 w-4 shrink-0" />}{PREFLIGHT_LABELS[key] || key}</div>)}</div>}
        </section>
        <div className="flex justify-end"><Button type="submit" disabled={saving || checking || form.locales.length === 0}>{saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{saving ? "開通中" : "建立租戶與交付單"}</Button></div>
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
