"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { RefreshCw, Save, Upload } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { assetsApi } from "@/lib/api/content";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";

type LocaleKey = "en" | "zh-TW";
type StatRow = { value: string; label: string };
type TimelineRow = { year: string; event: string };
type NewsRow = { date: string; title: string; summary: string };

type TenantCopy = {
  locale: LocaleKey;
  copy: Record<string, unknown>;
  assets: Record<string, string>;
  hidden_blocks: Record<string, boolean>;
  logo_url?: string;
};

function getString(tree: Record<string, unknown>, path: string): string {
  const value = path.split(".").reduce<unknown>((current, key) => (
    current && typeof current === "object" ? (current as Record<string, unknown>)[key] : undefined
  ), tree);
  return typeof value === "string" ? value : "";
}

function setString(tree: Record<string, unknown>, path: string, value: string): Record<string, unknown> {
  const parts = path.split(".");
  const next = structuredClone(tree);
  let cursor: Record<string, unknown> = next;
  parts.slice(0, -1).forEach((part) => {
    const child = cursor[part];
    cursor[part] = child && typeof child === "object" && !Array.isArray(child) ? { ...child as Record<string, unknown> } : {};
    cursor = cursor[part] as Record<string, unknown>;
  });
  cursor[parts[parts.length - 1]] = value;
  return next;
}

function getList<T>(tree: Record<string, unknown>, path: string): T[] {
  const value = path.split(".").reduce<unknown>((current, key) => (
    current && typeof current === "object" ? (current as Record<string, unknown>)[key] : undefined
  ), tree);
  return Array.isArray(value) ? value as T[] : [];
}

function writeList(tree: Record<string, unknown>, path: string, value: unknown[]): Record<string, unknown> {
  const parts = path.split(".");
  const next = structuredClone(tree);
  let cursor: Record<string, unknown> = next;
  parts.slice(0, -1).forEach((part) => {
    const child = cursor[part];
    cursor[part] = child && typeof child === "object" && !Array.isArray(child) ? { ...child as Record<string, unknown> } : {};
    cursor = cursor[part] as Record<string, unknown>;
  });
  cursor[parts[parts.length - 1]] = value;
  return next;
}

const ASSET_FIELDS: Array<{ key: string; label: string }> = [
  { key: "homeHero", label: "首頁主視覺" },
  { key: "aboutHero", label: "關於我們主視覺" },
  { key: "productsHero", label: "產品列表主視覺" },
  { key: "qualityInspection", label: "產品頁檢驗圖" },
  { key: "customPackaging", label: "產品頁包裝圖" },
];

const HIDDEN_FIELDS: Array<{ key: string; label: string }> = [
  { key: "productInspection", label: "隱藏檢驗區塊" },
  { key: "productPackaging", label: "隱藏包裝區塊" },
  { key: "productReadiness", label: "隱藏交期／包裝準備區塊" },
  { key: "productSpecControl", label: "隱藏規格控管區塊" },
  { key: "productContext", label: "隱藏專案情境區塊" },
];

export default function SiteCopySettingsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [locale, setLocale] = useState<LocaleKey>("en");
  const [copy, setCopy] = useState<Record<string, unknown>>({});
  const [assets, setAssets] = useState<Record<string, string>>({});
  const [hidden, setHidden] = useState<Record<string, boolean>>({});
  const [logoUrl, setLogoUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async (nextLocale = locale) => {
    if (!token) return;
    setLoading(true); setError(null); setSuccess(null);
    try {
      const response = await fetch(`${API_BASE}/site-profile/tenant-copy?locale=${encodeURIComponent(nextLocale)}`, {
        headers: buildApiHeaders(token),
      });
      if (!response.ok) throw new Error(`載入失敗 (${response.status})`);
      const payload = await response.json() as TenantCopy;
      setCopy(payload.copy || {});
      setAssets(payload.assets || {});
      setHidden(payload.hidden_blocks || {});
      setLogoUrl(payload.logo_url || "");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "載入網站文案失敗");
    } finally {
      setLoading(false);
    }
  }, [locale, token]);

  useEffect(() => { void load(locale); }, [load, locale]);

  async function save() {
    setSaving(true); setError(null); setSuccess(null);
    try {
      const response = await fetch(`${API_BASE}/site-profile/tenant-copy`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ locale, copy, assets, hidden_blocks: hidden, logo_url: logoUrl }),
      });
      if (!response.ok) throw new Error(`儲存失敗 (${response.status})`);
      const payload = await response.json() as TenantCopy;
      setCopy(payload.copy || {});
      setAssets(payload.assets || {});
      setHidden(payload.hidden_blocks || {});
      setLogoUrl(payload.logo_url || "");
      setSuccess("網站文案已更新。空白欄位會繼續使用系統預設。");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  const labeled = (label: string, path: string, rows = 1, maxLength = 400) => (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {rows > 1 ? (
        <Textarea rows={rows} maxLength={maxLength} value={getString(copy, path)} onChange={(event) => setCopy(setString(copy, path, event.target.value))} />
      ) : (
        <Input maxLength={maxLength} value={getString(copy, path)} onChange={(event) => setCopy(setString(copy, path, event.target.value))} />
      )}
    </div>
  );

  async function uploadAsset(key: string, file: File) {
    setUploading(key); setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const asset = await assetsApi.upload(token, form);
      if (key === "logo") {
        setLogoUrl(asset.public_url);
        return;
      }
      setAssets((current) => ({ ...current, [key]: asset.public_url }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "圖片上傳失敗");
    } finally {
      setUploading(null);
    }
  }

  const stats = getList<StatRow>(copy, "home.stats");
  const aboutStats = getList<StatRow>(copy, "about.stats");
  const story = getList<string>(copy, "about.storyParagraphs");
  const timeline = getList<TimelineRow>(copy, "about.timeline");
  const news = getList<NewsRow>(copy, "newsPage.items");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">網站文案與圖片</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">修改首頁、關於我們、產品信任區塊與新聞的文字圖片。不能重組版面或增刪選單網址。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select className="h-9 rounded-md border px-3 text-sm" value={locale} onChange={(event) => setLocale(event.target.value as LocaleKey)}>
            <option value="en">English</option>
            <option value="zh-TW">繁體中文</option>
          </select>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || saving}><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button>
          <Button size="sm" onClick={() => void save()} disabled={loading || saving || !token}><Save className="h-4 w-4" />{saving ? "儲存中…" : "儲存文案"}</Button>
        </div>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {success && <Alert><AlertDescription>{success}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle>Logo</CardTitle><CardDescription>有圖片時頁首與頁尾顯示 Logo；空白則繼續顯示品牌縮寫。</CardDescription></CardHeader>
        <CardContent className="space-y-3">
          {logoUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={logoUrl} alt="Logo" className="h-16 w-auto rounded-md border bg-muted/30 object-contain p-1" />
          )}
          <Input value={logoUrl} onChange={(event) => setLogoUrl(event.target.value)} placeholder="上傳後自動填入，或貼上圖片網址" />
          <label className="inline-flex h-8 cursor-pointer items-center gap-2 text-xs">
            <Upload className="h-3.5 w-3.5" />{uploading === "logo" ? "上傳中…" : "上傳 Logo"}
            <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" className="hidden" onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) void uploadAsset("logo", file);
            }} />
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>選單顯示名稱</CardTitle><CardDescription>只改訪客看到的名稱，不會增刪頁面或改網址。</CardDescription></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {labeled("產品", "header.nav.products", 1, 40)}
          {labeled("應用", "header.nav.applications", 1, 40)}
          {labeled("認證", "header.nav.certifications", 1, 40)}
          {labeled("關於我們", "header.nav.about", 1, 40)}
          {labeled("聯絡", "header.nav.contact", 1, 40)}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>全站圖片</CardTitle><CardDescription>這些圖套用在首頁、關於我們與產品詳情的固定區塊。</CardDescription></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {ASSET_FIELDS.map((item) => (
            <div key={item.key} className="space-y-2">
              <Label>{item.label}</Label>
              {assets[item.key] && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={assets[item.key]} alt={item.label} className="h-24 w-full rounded-md border object-cover" />
              )}
              <Input value={assets[item.key] || ""} onChange={(event) => setAssets((current) => ({ ...current, [item.key]: event.target.value }))} placeholder="圖片網址" />
              <label className="inline-flex h-8 cursor-pointer items-center gap-2 text-xs">
                <Upload className="h-3.5 w-3.5" />{uploading === item.key ? "上傳中…" : "上傳"}
                <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.target.value = "";
                  if (file) void uploadAsset(item.key, file);
                }} />
              </label>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>首頁文案</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {labeled("主視覺小標", "home.hero.eyebrow")}
            {labeled("主標題第一行", "home.hero.titleLine1")}
            {labeled("主標題第二行", "home.hero.titleLine2")}
            {labeled("主視覺說明", "home.hero.description", 3, 600)}
            {labeled("精選標題", "home.featured.title")}
            {labeled("精選說明", "home.featured.description", 3)}
            {labeled("為什麼選我們 標題", "home.why.title")}
            {labeled("為什麼選我們 說明", "home.why.description", 3)}
            {labeled("結尾 CTA 標題", "home.finalCta.title")}
            {labeled("結尾 CTA 說明", "home.finalCta.description", 3)}
          </div>
          <RepeatEditor
            title="首頁數字列"
            rows={stats}
            onChange={(rows) => setCopy(writeList(copy, "home.stats", rows))}
            empty={{ value: "", label: "" }}
            render={(row, update) => (
              <div className="grid gap-2 md:grid-cols-2">
                <Input value={row.value} maxLength={40} placeholder="數字" onChange={(event) => update({ ...row, value: event.target.value })} />
                <Input value={row.label} maxLength={80} placeholder="說明" onChange={(event) => update({ ...row, label: event.target.value })} />
              </div>
            )}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>關於我們</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {labeled("標題", "about.heroTitle")}
          {labeled("說明", "about.heroDescription", 3, 600)}
          {labeled("故事標題", "about.storyTitle")}
          {labeled("結尾標題", "about.ctaTitle")}
          {labeled("結尾說明", "about.ctaDescription", 3)}
          <RepeatEditor
            title="公司數字"
            rows={aboutStats}
            onChange={(rows) => setCopy(writeList(copy, "about.stats", rows))}
            empty={{ value: "", label: "" }}
            render={(row, update) => (
              <div className="grid gap-2 md:grid-cols-2">
                <Input value={row.value} maxLength={40} onChange={(event) => update({ ...row, value: event.target.value })} />
                <Input value={row.label} maxLength={80} onChange={(event) => update({ ...row, label: event.target.value })} />
              </div>
            )}
          />
          <RepeatEditor
            title="公司故事段落"
            rows={story}
            onChange={(rows) => setCopy(writeList(copy, "about.storyParagraphs", rows))}
            empty=""
            render={(row, update) => <Textarea rows={3} value={row} onChange={(event) => update(event.target.value)} />}
          />
          <RepeatEditor
            title="沿革"
            rows={timeline}
            onChange={(rows) => setCopy(writeList(copy, "about.timeline", rows))}
            empty={{ year: "", event: "" }}
            render={(row, update) => (
              <div className="grid gap-2 md:grid-cols-[120px_1fr]">
                <Input value={row.year} maxLength={20} placeholder="年份" onChange={(event) => update({ ...row, year: event.target.value })} />
                <Input value={row.event} maxLength={300} placeholder="事件" onChange={(event) => update({ ...row, event: event.target.value })} />
              </div>
            )}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>產品頁信任區塊</CardTitle><CardDescription>可改文字，或整塊隱藏。不能搬動位置。</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          {labeled("導讀", "productDetail.introBox", 3)}
          <div className="grid gap-4 md:grid-cols-2">
            {labeled("檢驗標題", "productDetail.inspectionTitle")}
            {labeled("檢驗說明", "productDetail.inspectionDescription", 3)}
            {labeled("包裝標題", "productDetail.packagingTitle")}
            {labeled("包裝說明", "productDetail.packagingDescription", 3)}
            {labeled("準備度標題", "productDetail.readinessTitle")}
            {labeled("準備度說明", "productDetail.readinessDescription", 3)}
            {labeled("規格控管標題", "productDetail.specControlTitle")}
            {labeled("規格控管說明", "productDetail.specControlDescription", 3)}
            {labeled("情境標題", "productDetail.contextTitle")}
            {labeled("情境說明", "productDetail.contextDescription", 3)}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {HIDDEN_FIELDS.map((item) => (
              <label key={item.key} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                {item.label}
                <Switch checked={Boolean(hidden[item.key])} onCheckedChange={(checked) => setHidden((current) => ({ ...current, [item.key]: checked }))} />
              </label>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>新聞</CardTitle>
          <CardDescription>儲存後會取代該語系的範本新聞。若要拿掉範本新聞，請先覆蓋為空列表再儲存。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {labeled("新聞頁標題", "newsPage.title")}
          {labeled("新聞頁說明", "newsPage.description", 3)}
          <div className="flex justify-end">
            <Button type="button" size="sm" variant="outline" onClick={() => setCopy(writeList(copy, "newsPage.items", []))}>覆蓋為尚無消息</Button>
          </div>
          <RepeatEditor
            title="新聞列表"
            rows={news}
            onChange={(rows) => setCopy(writeList(copy, "newsPage.items", rows))}
            empty={{ date: "", title: "", summary: "" }}
            render={(row, update) => (
              <div className="grid gap-2">
                <Input value={row.date} maxLength={20} placeholder="日期" onChange={(event) => update({ ...row, date: event.target.value })} />
                <Input value={row.title} maxLength={160} placeholder="標題" onChange={(event) => update({ ...row, title: event.target.value })} />
                <Textarea rows={2} value={row.summary} maxLength={400} placeholder="摘要" onChange={(event) => update({ ...row, summary: event.target.value })} />
              </div>
            )}
          />
        </CardContent>
      </Card>
    </div>
  );
}

function RepeatEditor<T>({
  title,
  rows,
  empty,
  onChange,
  render,
}: {
  title: string;
  rows: T[];
  empty: T;
  onChange: (rows: T[]) => void;
  render: (row: T, update: (next: T) => void) => ReactNode;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>{title}</Label>
        <Button type="button" size="sm" variant="outline" onClick={() => onChange([...rows, empty])}>新增一列</Button>
      </div>
      {rows.length === 0 && <p className="text-xs text-muted-foreground">尚未自訂。儲存空列表可覆蓋範本文案。</p>}
      {rows.map((row, index) => (
        <div key={index} className="rounded-md border p-3">
          {render(row, (next) => onChange(rows.map((item, current) => current === index ? next : item)))}
          <Button type="button" size="sm" variant="ghost" className="mt-2 text-destructive" onClick={() => onChange(rows.filter((_, current) => current !== index))}>刪除</Button>
        </div>
      ))}
    </div>
  );
}
