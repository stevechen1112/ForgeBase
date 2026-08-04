"use client";

import { useCallback, useEffect, useState } from "react";
import { Save, RefreshCw } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { OpsConfigCard } from "@/components/settings/ops-config-card";

type SiteProfileForm = {
  brand_name: string;
  logo_mark: string;
  contact_email: string;
  contact_phone: string;
  site_url: string;
  default_locale: string;
  theme_key: string;
  layout_key: string;
  asset_base: string;
  demo_company_folder: string;
  header_nav_json: string;
  header_actions_json: string;
  footer_sections_json: string;
  footer_badges_json: string;
  social_links_json: string;
  footer_cta_title: string;
  footer_cta_description: string;
  footer_cta_label: string;
  footer_cta_href: string;
  asset_manifest_json: string;
};

const EMPTY_FORM: SiteProfileForm = {
  brand_name: "",
  logo_mark: "",
  contact_email: "",
  contact_phone: "",
  site_url: "",
  default_locale: "en",
  theme_key: "cobalt",
  layout_key: "classic",
  asset_base: "",
  demo_company_folder: "",
  header_nav_json: "",
  header_actions_json: "",
  footer_sections_json: "",
  footer_badges_json: "",
  social_links_json: "",
  footer_cta_title: "",
  footer_cta_description: "",
  footer_cta_label: "",
  footer_cta_href: "",
  asset_manifest_json: "",
};

function normalizeForm(payload: Partial<Record<keyof SiteProfileForm, string | null | undefined>>): SiteProfileForm {
  return {
    brand_name: payload.brand_name ?? "",
    logo_mark: payload.logo_mark ?? "",
    contact_email: payload.contact_email ?? "",
    contact_phone: payload.contact_phone ?? "",
    site_url: payload.site_url ?? "",
    default_locale: payload.default_locale ?? "en",
    theme_key: payload.theme_key ?? "cobalt",
    layout_key: payload.layout_key ?? "classic",
    asset_base: payload.asset_base ?? "",
    demo_company_folder: payload.demo_company_folder ?? "",
    header_nav_json: payload.header_nav_json ?? "",
    header_actions_json: payload.header_actions_json ?? "",
    footer_sections_json: payload.footer_sections_json ?? "",
    footer_badges_json: payload.footer_badges_json ?? "",
    social_links_json: payload.social_links_json ?? "",
    footer_cta_title: payload.footer_cta_title ?? "",
    footer_cta_description: payload.footer_cta_description ?? "",
    footer_cta_label: payload.footer_cta_label ?? "",
    footer_cta_href: payload.footer_cta_href ?? "",
    asset_manifest_json: payload.asset_manifest_json ?? "",
  };
}

function isValidJson(value: string): boolean {
  if (!value.trim()) {
    return true;
  }
  try {
    JSON.parse(value);
    return true;
  } catch {
    return false;
  }
}

const JSON_FIELD_LABELS: Record<string, string> = {
  header_nav_json: "Header 導覽",
  header_actions_json: "頁首行動按鈕",
  footer_sections_json: "Footer 區塊",
  footer_badges_json: "Footer 標章",
  social_links_json: "社群連結",
  asset_manifest_json: "圖片資產設定",
};

/** 即時格式提示：非空且格式錯誤時顯示紅字，正確時顯示綠勾 */
function JsonHint({ value }: { value: string }) {
  if (!value.trim()) return null;
  return isValidJson(value) ? (
    <p className="text-xs text-green-600">JSON 格式正確 ✓</p>
  ) : (
    <p className="text-xs text-red-600">JSON 格式有誤：請檢查括號、引號與逗號（可多行貼上後再檢查）</p>
  );
}

export default function SiteProfileSettingsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [form, setForm] = useState<SiteProfileForm>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) {
      return;
    }
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`${API_BASE}/site-profile`, {
        headers: buildApiHeaders(token),
      });
      if (!response.ok) {
        throw new Error(`載入失敗 (${response.status})`);
      }
      const data = (await response.json()) as Partial<Record<keyof SiteProfileForm, string | null>>;
      setForm(normalizeForm(data));
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "載入網站設定失敗");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  function updateField<K extends keyof SiteProfileForm>(key: K, value: SiteProfileForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSave() {
    const jsonFields: Array<keyof SiteProfileForm> = [
      "header_nav_json",
      "header_actions_json",
      "footer_sections_json",
      "footer_badges_json",
      "social_links_json",
      "asset_manifest_json",
    ];

    const invalidField = jsonFields.find((field) => !isValidJson(form[field]));
    if (invalidField) {
      setError(`「${JSON_FIELD_LABELS[invalidField] ?? invalidField}」不是有效的 JSON 格式，請檢查括號、引號與逗號後再儲存。`);
      setSuccess(null);
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`${API_BASE}/site-profile`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify(form),
      });
      if (!response.ok) {
        throw new Error(`儲存失敗 (${response.status})`);
      }
      const data = (await response.json()) as Partial<Record<keyof SiteProfileForm, string | null>>;
      setForm(normalizeForm(data));
      setSuccess("網站設定已更新。前台將在下一次 request / revalidate 後讀到新設定。\n");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "儲存網站設定失敗");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">網站外觀設定</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            管理品牌名稱、頁首／頁尾選單，以及產品與應用頁的圖示設定。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || saving}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" onClick={() => void handleSave()} disabled={loading || saving || !token}>
            <Save className={`mr-2 h-4 w-4 ${saving ? "animate-pulse" : ""}`} />儲存設定
          </Button>
        </div>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {success ? (
        <Alert>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>基礎品牌</CardTitle>
          <CardDescription>這些欄位會直接影響前台品牌名稱、主題、聯絡資訊與資產基底路徑。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="brand_name">品牌名稱</Label>
            <Input id="brand_name" value={form.brand_name} onChange={(e) => updateField("brand_name", e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="logo_mark">Logo 縮寫</Label>
            <Input id="logo_mark" value={form.logo_mark} onChange={(e) => updateField("logo_mark", e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_email">聯絡 Email</Label>
            <Input id="contact_email" value={form.contact_email} onChange={(e) => updateField("contact_email", e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_phone">聯絡電話</Label>
            <Input id="contact_phone" value={form.contact_phone} onChange={(e) => updateField("contact_phone", e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="site_url">網站網址</Label>
            <Input id="site_url" value={form.site_url} onChange={(e) => updateField("site_url", e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="asset_base">資產基底路徑</Label>
            <Input id="asset_base" value={form.asset_base} onChange={(e) => updateField("asset_base", e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="default_locale">預設語系</Label>
            <select
              id="default_locale"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={form.default_locale}
              onChange={(e) => updateField("default_locale", e.target.value)}
            >
              <option value="en">en</option>
              <option value="zh-TW">zh-TW</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="theme_key">主題</Label>
            <select
              id="theme_key"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={form.theme_key}
              onChange={(e) => updateField("theme_key", e.target.value)}
            >
              <option value="cobalt">鈷藍</option>
              <option value="forest">森林綠</option>
              <option value="slate">灰藍</option>
              <option value="warm">暖色</option>
              <option value="industrial">工業風</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="layout_key">版型</Label>
            <select
              id="layout_key"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={form.layout_key}
              onChange={(e) => updateField("layout_key", e.target.value)}
            >
              <option value="classic">classic</option>
              <option value="industrial">industrial</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="demo_company_folder">Demo 資產資料夾</Label>
            <Input id="demo_company_folder" value={form.demo_company_folder} onChange={(e) => updateField("demo_company_folder", e.target.value)} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Header / Footer 結構</CardTitle>
          <CardDescription>
            以 JSON 定義導覽與頁尾。文字欄位使用多語物件格式 {'{"en":"English","zh-TW":"繁體中文"}'}；
            每個欄位下方都有範例，留白時前台會回退到系統預設資訊架構。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="space-y-2">
            <Label htmlFor="header_nav_json">Header 導覽 JSON</Label>
            <Textarea id="header_nav_json" rows={6} value={form.header_nav_json} onChange={(e) => updateField("header_nav_json", e.target.value)} placeholder='[{"href":"/products","label":{"en":"Products","zh-TW":"產品"}}]' />
            <JsonHint value={form.header_nav_json} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="header_actions_json">頁首行動按鈕（JSON）</Label>
            <Textarea id="header_actions_json" rows={5} value={form.header_actions_json} onChange={(e) => updateField("header_actions_json", e.target.value)} placeholder='[{"href":"/rfq","label":{"en":"Request Quote","zh-TW":"立即詢價"}}]' />
            <JsonHint value={form.header_actions_json} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="footer_sections_json">Footer 區塊 JSON</Label>
            <Textarea id="footer_sections_json" rows={8} value={form.footer_sections_json} onChange={(e) => updateField("footer_sections_json", e.target.value)} placeholder='[{"heading":{"en":"Products","zh-TW":"產品"},"items":[{"href":"/products","label":{"en":"Catalogue","zh-TW":"產品型錄"}}]}]' />
            <JsonHint value={form.footer_sections_json} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="footer_badges_json">Footer 標章 JSON</Label>
              <Textarea id="footer_badges_json" rows={5} value={form.footer_badges_json} onChange={(e) => updateField("footer_badges_json", e.target.value)} placeholder='[{"en":"ISO 9001","zh-TW":"ISO 9001"}]' />
              <JsonHint value={form.footer_badges_json} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="social_links_json">社群連結 JSON</Label>
              <Textarea id="social_links_json" rows={5} value={form.social_links_json} onChange={(e) => updateField("social_links_json", e.target.value)} placeholder='[{"href":"https://linkedin.com/company/example","label":{"en":"LinkedIn","zh-TW":"LinkedIn"}}]' />
              <JsonHint value={form.social_links_json} />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>頁尾行動按鈕與圖片資產</CardTitle>
          <CardDescription>圖片資產設定會覆蓋首頁主圖、產品分類、應用頁與產品圖片等預設素材。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="footer_cta_title">頁尾行動區標題</Label>
              <Input id="footer_cta_title" value={form.footer_cta_title} onChange={(e) => updateField("footer_cta_title", e.target.value)} placeholder='{"en":"Ready to start?","zh-TW":"準備開始了嗎？"}' />
            </div>
            <div className="space-y-2">
              <Label htmlFor="footer_cta_label">頁尾按鈕文案</Label>
              <Input id="footer_cta_label" value={form.footer_cta_label} onChange={(e) => updateField("footer_cta_label", e.target.value)} placeholder='{"en":"Talk to Sales","zh-TW":"聯絡業務"}' />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="footer_cta_description">頁尾行動區說明</Label>
              <Input id="footer_cta_description" value={form.footer_cta_description} onChange={(e) => updateField("footer_cta_description", e.target.value)} placeholder='{"en":"Get a tailored response within 1 business day.","zh-TW":"1 個工作天內取得回覆。"}' />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="footer_cta_href">頁尾按鈕連結</Label>
              <Input id="footer_cta_href" value={form.footer_cta_href} onChange={(e) => updateField("footer_cta_href", e.target.value)} placeholder="/contact" />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="asset_manifest_json">圖片資產設定（JSON）</Label>
            <Textarea id="asset_manifest_json" rows={12} value={form.asset_manifest_json} onChange={(e) => updateField("asset_manifest_json", e.target.value)} placeholder='{"homeHero":"/uploads/tenant-a/home-hero.jpg","categoryBySlug":{"precision-casting":"/uploads/tenant-a/categories/casting.jpg"},"applicationBySlug":{"medical-components":"/uploads/tenant-a/apps/medical.jpg"},"productByKey":{"MC-1001":"/uploads/tenant-a/products/mc-1001.jpg"}}' />
            <JsonHint value={form.asset_manifest_json} />
          </div>
        </CardContent>
      </Card>

      <OpsConfigCard />
    </div>
  );
}
