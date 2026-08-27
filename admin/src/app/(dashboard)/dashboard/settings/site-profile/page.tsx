"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, RefreshCw, Save, Upload } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { assetsApi } from "@/lib/api/content";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type SiteProfile = {
  brand_name: string;
  logo_mark: string;
  logo_url: string;
  contact_email: string;
  contact_phone: string;
  site_url: string;
  default_locale: string;
};

const EMPTY_PROFILE: SiteProfile = {
  brand_name: "",
  logo_mark: "",
  logo_url: "",
  contact_email: "",
  contact_phone: "",
  site_url: "",
  default_locale: "zh-TW",
};

function normalizeProfile(payload: Partial<SiteProfile>): SiteProfile {
  return {
    brand_name: payload.brand_name ?? "",
    logo_mark: payload.logo_mark ?? "",
    logo_url: payload.logo_url ?? "",
    contact_email: payload.contact_email ?? "",
    contact_phone: payload.contact_phone ?? "",
    site_url: payload.site_url ?? "",
    default_locale: payload.default_locale ?? "zh-TW",
  };
}

export default function SiteProfileSettingsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [profile, setProfile] = useState<SiteProfile>(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError(null); setSuccess(null);
    try {
      const response = await fetch(`${API_BASE}/site-profile`, { headers: buildApiHeaders(token) });
      if (!response.ok) throw new Error(`載入失敗 (${response.status})`);
      setProfile(normalizeProfile(await response.json()));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "載入公司與網站資料失敗");
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function save() {
    setSaving(true); setError(null); setSuccess(null);
    try {
      const response = await fetch(`${API_BASE}/site-profile`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({
          brand_name: profile.brand_name,
          logo_mark: profile.logo_mark,
          logo_url: profile.logo_url || null,
          contact_email: profile.contact_email,
          contact_phone: profile.contact_phone || null,
          default_locale: profile.default_locale,
        }),
      });
      if (!response.ok) throw new Error(`儲存失敗 (${response.status})`);
      setProfile(normalizeProfile(await response.json()));
      setSuccess("公司與網站基本資料已更新。");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "儲存失敗");
    } finally { setSaving(false); }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold tracking-tight">公司與網站資料</h1><p className="mt-0.5 text-sm text-muted-foreground">維護客戶在網站上看到的品牌與聯絡資訊；版型、網域及技術整合由 ForgeBase 團隊管理。</p></div>
        <div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || saving}><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button><Button size="sm" onClick={() => void save()} disabled={loading || saving || !token}><Save className="h-4 w-4" />{saving ? "儲存中…" : "儲存資料"}</Button></div>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {success && <Alert><AlertDescription>{success}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle>公司基本資料</CardTitle><CardDescription>品牌名稱與聯絡方式會顯示於網站頁首、頁尾或聯絡區域。</CardDescription></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2"><Label htmlFor="brand_name">品牌名稱</Label><Input id="brand_name" value={profile.brand_name} onChange={(event) => setProfile((current) => ({ ...current, brand_name: event.target.value }))} maxLength={120} /></div>
          <div className="space-y-2"><Label htmlFor="logo_mark">品牌縮寫</Label><Input id="logo_mark" value={profile.logo_mark} onChange={(event) => setProfile((current) => ({ ...current, logo_mark: event.target.value }))} maxLength={10} /></div>
          <div className="space-y-2 md:col-span-2">
            <Label>Logo 圖片</Label>
            {profile.logo_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={profile.logo_url} alt={profile.brand_name || "Logo"} className="mb-2 h-16 w-auto rounded-md border bg-muted/30 object-contain p-1" />
            )}
            <div className="flex flex-wrap items-center gap-3">
              <Input value={profile.logo_url} onChange={(event) => setProfile((current) => ({ ...current, logo_url: event.target.value }))} placeholder="上傳後自動填入，或貼上圖片網址" />
              <label className={`inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border px-3 text-sm ${uploadingLogo ? "pointer-events-none opacity-50" : ""}`}>
                <Upload className="h-4 w-4" />{uploadingLogo ? "上傳中…" : "上傳 Logo"}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  className="hidden"
                  disabled={uploadingLogo}
                  onChange={async (event) => {
                    const file = event.target.files?.[0];
                    event.target.value = "";
                    if (!file || !token) return;
                    setUploadingLogo(true); setError(null);
                    try {
                      const form = new FormData();
                      form.append("file", file);
                      const asset = await assetsApi.upload(token, form);
                      setProfile((current) => ({ ...current, logo_url: asset.public_url }));
                    } catch (cause) {
                      setError(cause instanceof Error ? cause.message : "Logo 上傳失敗");
                    } finally {
                      setUploadingLogo(false);
                    }
                  }}
                />
              </label>
            </div>
            <p className="text-xs text-muted-foreground">有 Logo 圖時，前台頁首會顯示圖片；沒有圖則繼續顯示縮寫。</p>
          </div>
          <div className="space-y-2"><Label htmlFor="contact_email">聯絡 Email</Label><Input id="contact_email" type="email" value={profile.contact_email} onChange={(event) => setProfile((current) => ({ ...current, contact_email: event.target.value }))} /></div>
          <div className="space-y-2"><Label htmlFor="contact_phone">聯絡電話</Label><Input id="contact_phone" value={profile.contact_phone} onChange={(event) => setProfile((current) => ({ ...current, contact_phone: event.target.value }))} /></div>
          <div className="space-y-2">
            <Label htmlFor="default_locale">內容來源語系</Label>
            <select
              id="default_locale"
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              value={profile.default_locale === "zh-tw" ? "zh-TW" : profile.default_locale}
              onChange={(event) => setProfile((current) => ({ ...current, default_locale: event.target.value }))}
            >
              <option value="zh-TW">繁體中文（日常維護正本）</option>
              <option value="en">English</option>
            </select>
            <p className="text-xs text-muted-foreground">改了只影響之後的複製與起草，不會重跑全站已上架內容。</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>目前網站</CardTitle><CardDescription>正式網址與公開語系由 ForgeBase 交付流程管理。如需修改，請使用「網站修改與支援」。</CardDescription></CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-sm font-medium">{profile.site_url || "尚未設定正式網址"}</p></div>
          {profile.site_url && <Button asChild variant="outline"><a href={profile.site_url} target="_blank" rel="noreferrer"><ExternalLink className="h-4 w-4" />查看公開網站</a></Button>}
        </CardContent>
      </Card>
    </div>
  );
}
