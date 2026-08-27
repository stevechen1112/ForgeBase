"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw, Save, Search, Settings2, Trash2 } from "lucide-react";
import { platformAdminApi, type PlatformSiteProfile } from "@/lib/api/platform-admin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = { token: string; tenantId: string };
type LinkItem = { label: string; href: string };
type FooterSection = { heading: string; items: LinkItem[] };
type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
type LeafRow = { path: string; value: string; kind: "string" | "number" | "boolean" | "null" };

const EMPTY: PlatformSiteProfile = {
  brand_name: "", logo_mark: "", logo_url: "", favicon_url: "", theme_key: "cobalt", layout_key: "classic",
  contact_email: "", contact_phone: "", site_url: "", default_locale: "en",
  asset_base: "", demo_company_folder: "", header_nav_json: "", header_actions_json: "",
  footer_sections_json: "", footer_badges_json: "", social_links_json: "",
  footer_cta_title: "", footer_cta_description: "", footer_cta_label: "", footer_cta_href: "",
  asset_manifest_json: "", site_copy_json: "",
};

const JSON_FIELDS: Array<keyof PlatformSiteProfile> = [
  "header_nav_json", "header_actions_json", "footer_sections_json", "footer_badges_json",
  "social_links_json", "asset_manifest_json", "site_copy_json",
];

function normalize(value: PlatformSiteProfile): PlatformSiteProfile {
  return Object.fromEntries(Object.entries(EMPTY).map(([key, fallback]) => [key, value[key as keyof PlatformSiteProfile] ?? fallback])) as PlatformSiteProfile;
}

function invalidJsonField(profile: PlatformSiteProfile): string | null {
  for (const field of JSON_FIELDS) {
    const value = profile[field];
    if (!value || typeof value !== "string") continue;
    try { JSON.parse(value); } catch { return field; }
  }
  return null;
}

function parseJson<T>(raw: string | undefined, fallback: T): T {
  if (!raw?.trim()) return fallback;
  try { return JSON.parse(raw) as T; } catch { return fallback; }
}

function encode(value: unknown): string {
  return JSON.stringify(value);
}

function flattenLeaves(value: JsonValue, prefix = ""): LeafRow[] {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => flattenLeaves(item, `${prefix}[${index}]`));
  }
  if (value !== null && typeof value === "object") {
    return Object.entries(value).flatMap(([key, item]) => flattenLeaves(item, prefix ? `${prefix}.${key}` : key));
  }
  const kind: LeafRow["kind"] = value === null ? "null" : typeof value as LeafRow["kind"];
  return [{ path: prefix || "value", value: value === null ? "" : String(value), kind }];
}

function pathTokens(path: string): Array<string | number> {
  const tokens: Array<string | number> = [];
  path.replace(/([^.[\]]+)|\[(\d+)\]/g, (_match, key: string | undefined, index: string | undefined) => {
    if (index !== undefined) tokens.push(Number(index));
    else if (key) tokens.push(key);
    return "";
  });
  return tokens;
}

function castLeaf(value: string, kind: LeafRow["kind"]): JsonValue {
  if (kind === "number") return Number.isFinite(Number(value)) ? Number(value) : 0;
  if (kind === "boolean") return value === "true";
  if (kind === "null") return null;
  return value;
}

function updateAtPath(root: JsonValue, path: string, value: JsonValue): JsonValue {
  const clone = structuredClone(root);
  const tokens = pathTokens(path);
  if (!tokens.length) return value;
  let cursor = clone as JsonValue[] | { [key: string]: JsonValue };
  tokens.forEach((token, index) => {
    const last = index === tokens.length - 1;
    if (last) {
      if (Array.isArray(cursor) && typeof token === "number") cursor[token] = value;
      else if (!Array.isArray(cursor) && typeof token === "string") cursor[token] = value;
      return;
    }
    const next = tokens[index + 1];
    if (Array.isArray(cursor) && typeof token === "number") {
      if (cursor[token] === undefined) cursor[token] = typeof next === "number" ? [] : {};
      cursor = cursor[token] as JsonValue[] | { [key: string]: JsonValue };
    } else if (!Array.isArray(cursor) && typeof token === "string") {
      if (cursor[token] === undefined) cursor[token] = typeof next === "number" ? [] : {};
      cursor = cursor[token] as JsonValue[] | { [key: string]: JsonValue };
    }
  });
  return clone;
}

function removeAtPath(root: JsonValue, path: string): JsonValue {
  const clone = structuredClone(root);
  const tokens = pathTokens(path);
  if (!tokens.length) return clone;
  let cursor = clone as JsonValue[] | { [key: string]: JsonValue };
  for (let index = 0; index < tokens.length - 1; index += 1) {
    const token = tokens[index];
    cursor = (Array.isArray(cursor) && typeof token === "number"
      ? cursor[token]
      : !Array.isArray(cursor) && typeof token === "string"
        ? cursor[token]
        : {}) as JsonValue[] | { [key: string]: JsonValue };
  }
  const last = tokens[tokens.length - 1];
  if (Array.isArray(cursor) && typeof last === "number") cursor.splice(last, 1);
  else if (!Array.isArray(cursor) && typeof last === "string") delete cursor[last];
  return clone;
}

export function PlatformSiteProfileEditor({ token, tenantId }: Props) {
  const [profile, setProfile] = useState<PlatformSiteProfile>(EMPTY);
  const [baseline, setBaseline] = useState<PlatformSiteProfile>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError(""); setMessage("");
    try {
      const result = normalize(await platformAdminApi.siteProfile(token, tenantId));
      setProfile(result); setBaseline(result);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "無法讀取網站進階設定"); }
    finally { setLoading(false); }
  }, [tenantId, token]);

  useEffect(() => { void load(); }, [load]);
  const dirty = useMemo(() => JSON.stringify(profile) !== JSON.stringify(baseline), [baseline, profile]);
  const field = (key: keyof PlatformSiteProfile, value: string) => setProfile((current) => ({ ...current, [key]: value }));

  async function save() {
    const invalid = invalidJsonField(profile);
    if (invalid) { setError(`${invalid} 的資料格式不正確，請先修正後再儲存。`); return; }
    setSaving(true); setError(""); setMessage("");
    try {
      const result = normalize(await platformAdminApi.updateSiteProfile(token, tenantId, profile));
      setProfile(result); setBaseline(result); setMessage("網站進階設定已更新，並留下平台操作紀錄。");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "儲存失敗"); }
    finally { setSaving(false); }
  }

  return (
    <section className="rounded-xl border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><div className="flex items-center gap-2"><Settings2 className="h-4 w-4 text-muted-foreground" /><h3 className="text-sm font-semibold">網站進階設定</h3></div><p className="mt-1 text-xs text-muted-foreground">僅供 ForgeBase 系統方調整網站殼層、導覽、多語與素材對應；租戶後台不會顯示這些技術欄位。</p></div>
        <div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => void load()} disabled={loading || saving}><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新讀取</Button><Button size="sm" onClick={() => void save()} disabled={loading || saving || !dirty}><Save className="h-4 w-4" />{saving ? "儲存中…" : "儲存進階設定"}</Button></div>
      </div>
      {error && <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
      {message && <p className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}

      {!loading && <div className="mt-5 space-y-4">
        <details className="rounded-lg border p-4">
          <summary className="cursor-pointer text-sm font-medium">網址、版型與資產路徑</summary>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Field label="完整網站網址" value={profile.site_url} onChange={(value) => field("site_url", value)} />
            <Field label="預設語系" value={profile.default_locale} onChange={(value) => field("default_locale", value)} />
            <Field label="Logo 圖片網址" value={profile.logo_url || ""} onChange={(value) => field("logo_url", value)} />
            <Field label="網站圖示網址" value={profile.favicon_url || ""} onChange={(value) => field("favicon_url", value)} />
            <Field label="主題代號" value={profile.theme_key} onChange={(value) => field("theme_key", value)} />
            <Field label="版型代號" value={profile.layout_key} onChange={(value) => field("layout_key", value)} />
            <Field label="資產基底路徑" value={profile.asset_base || ""} onChange={(value) => field("asset_base", value)} />
            <Field label="Demo 資產資料夾" value={profile.demo_company_folder || ""} onChange={(value) => field("demo_company_folder", value)} />
          </div>
        </details>

        <details className="rounded-lg border p-4">
          <summary className="cursor-pointer text-sm font-medium">頁首、頁尾與行動按鈕</summary>
          <div className="mt-4 space-y-6">
            <LinkListEditor title="頁首導覽" value={profile.header_nav_json} onChange={(value) => field("header_nav_json", value)} />
            <LinkListEditor title="頁首行動按鈕" value={profile.header_actions_json} onChange={(value) => field("header_actions_json", value)} />
            <FooterSectionsEditor value={profile.footer_sections_json} onChange={(value) => field("footer_sections_json", value)} />
            <StringListEditor title="頁尾標章" value={profile.footer_badges_json} onChange={(value) => field("footer_badges_json", value)} />
            <KeyValueEditor title="社群連結" value={profile.social_links_json} onChange={(value) => field("social_links_json", value)} pathLabel="平台／欄位" valueLabel="連結或文字" />
            <div className="grid gap-4 md:grid-cols-2"><Field label="頁尾行動區標題" value={profile.footer_cta_title || ""} onChange={(value) => field("footer_cta_title", value)} /><Field label="頁尾按鈕文案" value={profile.footer_cta_label || ""} onChange={(value) => field("footer_cta_label", value)} /><Field label="頁尾行動區說明" value={profile.footer_cta_description || ""} onChange={(value) => field("footer_cta_description", value)} /><Field label="頁尾按鈕連結" value={profile.footer_cta_href || ""} onChange={(value) => field("footer_cta_href", value)} /></div>
          </div>
        </details>

        <details className="rounded-lg border p-4">
          <summary className="cursor-pointer text-sm font-medium">圖片對應與網站多語文案</summary>
          <div className="mt-4 space-y-6">
            <KeyValueEditor title="圖片資產對應" value={profile.asset_manifest_json} onChange={(value) => field("asset_manifest_json", value)} pathLabel="圖片用途" valueLabel="圖片路徑" />
            <KeyValueEditor title="網站文案欄位" value={profile.site_copy_json} onChange={(value) => field("site_copy_json", value)} pathLabel="頁面／欄位" valueLabel="顯示內容" searchable />
          </div>
        </details>
      </div>}
    </section>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <div className="space-y-1.5"><Label>{label}</Label><Input value={value} onChange={(event) => onChange(event.target.value)} /></div>;
}

function LinkListEditor({ title, value, onChange }: { title: string; value?: string; onChange: (value: string) => void }) {
  const items = parseJson<LinkItem[]>(value, []);
  const update = (index: number, key: keyof LinkItem, next: string) => onChange(encode(items.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: next } : item)));
  return <section className="space-y-3"><div className="flex items-center justify-between"><h4 className="text-sm font-medium">{title}</h4><Button type="button" size="sm" variant="outline" onClick={() => onChange(encode([...items, { label: "", href: "" }]))}><Plus className="h-3.5 w-3.5" />新增</Button></div>{items.length === 0 ? <p className="rounded-md bg-muted/30 p-3 text-xs text-muted-foreground">尚未設定</p> : <div className="space-y-2">{items.map((item, index) => <div key={index} className="grid gap-2 rounded-md border p-3 md:grid-cols-[1fr_1.4fr_auto]"><Input aria-label={`${title} ${index + 1} 文案`} placeholder="顯示文案" value={item.label || ""} onChange={(event) => update(index, "label", event.target.value)} /><Input aria-label={`${title} ${index + 1} 連結`} placeholder="/products" value={item.href || ""} onChange={(event) => update(index, "href", event.target.value)} /><Button type="button" size="icon" variant="ghost" aria-label={`移除 ${title} ${index + 1}`} onClick={() => onChange(encode(items.filter((_item, itemIndex) => itemIndex !== index)))}><Trash2 className="h-4 w-4" /></Button></div>)}</div>}</section>;
}

function StringListEditor({ title, value, onChange }: { title: string; value?: string; onChange: (value: string) => void }) {
  const items = parseJson<string[]>(value, []);
  return <section className="space-y-3"><div className="flex items-center justify-between"><h4 className="text-sm font-medium">{title}</h4><Button type="button" size="sm" variant="outline" onClick={() => onChange(encode([...items, ""]))}><Plus className="h-3.5 w-3.5" />新增</Button></div><div className="grid gap-2 md:grid-cols-2">{items.map((item, index) => <div key={index} className="flex gap-2"><Input aria-label={`${title} ${index + 1}`} value={item} onChange={(event) => onChange(encode(items.map((current, itemIndex) => itemIndex === index ? event.target.value : current)))} /><Button type="button" size="icon" variant="ghost" aria-label={`移除 ${title} ${index + 1}`} onClick={() => onChange(encode(items.filter((_current, itemIndex) => itemIndex !== index)))}><Trash2 className="h-4 w-4" /></Button></div>)}</div></section>;
}

function FooterSectionsEditor({ value, onChange }: { value?: string; onChange: (value: string) => void }) {
  const sections = parseJson<FooterSection[]>(value, []);
  const commit = (next: FooterSection[]) => onChange(encode(next));
  return <section className="space-y-3"><div className="flex items-center justify-between"><h4 className="text-sm font-medium">頁尾導覽區塊</h4><Button type="button" size="sm" variant="outline" onClick={() => commit([...sections, { heading: "", items: [] }])}><Plus className="h-3.5 w-3.5" />新增區塊</Button></div>{sections.map((section, sectionIndex) => <div key={sectionIndex} className="space-y-3 rounded-md border p-3"><div className="flex gap-2"><Input aria-label={`頁尾區塊 ${sectionIndex + 1} 標題`} placeholder="區塊標題" value={section.heading || ""} onChange={(event) => commit(sections.map((current, index) => index === sectionIndex ? { ...current, heading: event.target.value } : current))} /><Button type="button" size="icon" variant="ghost" aria-label={`移除頁尾區塊 ${sectionIndex + 1}`} onClick={() => commit(sections.filter((_section, index) => index !== sectionIndex))}><Trash2 className="h-4 w-4" /></Button></div>{section.items.map((item, itemIndex) => <div key={itemIndex} className="grid gap-2 pl-4 md:grid-cols-[1fr_1.4fr_auto]"><Input aria-label={`頁尾區塊 ${sectionIndex + 1} 項目 ${itemIndex + 1} 文案`} placeholder="顯示文案" value={item.label || ""} onChange={(event) => commit(sections.map((current, index) => index === sectionIndex ? { ...current, items: current.items.map((link, linkIndex) => linkIndex === itemIndex ? { ...link, label: event.target.value } : link) } : current))} /><Input aria-label={`頁尾區塊 ${sectionIndex + 1} 項目 ${itemIndex + 1} 連結`} placeholder="/products" value={item.href || ""} onChange={(event) => commit(sections.map((current, index) => index === sectionIndex ? { ...current, items: current.items.map((link, linkIndex) => linkIndex === itemIndex ? { ...link, href: event.target.value } : link) } : current))} /><Button type="button" size="icon" variant="ghost" aria-label={`移除頁尾項目 ${itemIndex + 1}`} onClick={() => commit(sections.map((current, index) => index === sectionIndex ? { ...current, items: current.items.filter((_link, linkIndex) => linkIndex !== itemIndex) } : current))}><Trash2 className="h-4 w-4" /></Button></div>)}<Button type="button" size="sm" variant="ghost" onClick={() => commit(sections.map((current, index) => index === sectionIndex ? { ...current, items: [...current.items, { label: "", href: "" }] } : current))}><Plus className="h-3.5 w-3.5" />新增連結</Button></div>)}</section>;
}

function KeyValueEditor({ title, value, onChange, pathLabel, valueLabel, searchable = false }: { title: string; value?: string; onChange: (value: string) => void; pathLabel: string; valueLabel: string; searchable?: boolean }) {
  const root = parseJson<JsonValue>(value, {});
  const rows = flattenLeaves(root);
  const [query, setQuery] = useState("");
  const [newPath, setNewPath] = useState("");
  const [newValue, setNewValue] = useState("");
  const visibleRows = query.trim() ? rows.filter((row) => `${row.path} ${row.value}`.toLowerCase().includes(query.toLowerCase())) : rows;
  const commitLeaf = (row: LeafRow, next: string) => onChange(encode(updateAtPath(root, row.path, castLeaf(next, row.kind))));
  const addLeaf = () => {
    const path = newPath.trim();
    if (!path) return;
    onChange(encode(updateAtPath(root, path, newValue)));
    setNewPath(""); setNewValue("");
  };
  return <section className="space-y-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><h4 className="text-sm font-medium">{title}</h4><p className="text-xs text-muted-foreground">共 {rows.length} 個可編輯欄位</p></div>{searchable && <div className="relative"><Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" /><Input className="h-9 w-64 pl-8" placeholder="搜尋頁面、欄位或文字" value={query} onChange={(event) => setQuery(event.target.value)} /></div>}</div><div className="max-h-[34rem] space-y-2 overflow-y-auto rounded-md border p-3">{visibleRows.length === 0 ? <p className="py-6 text-center text-xs text-muted-foreground">沒有符合的欄位</p> : visibleRows.map((row) => <div key={row.path} className="grid gap-2 md:grid-cols-[minmax(180px,0.8fr)_minmax(240px,1.5fr)_auto]"><div className="rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground break-all" title={pathLabel}>{row.path}</div>{row.kind === "boolean" ? <select aria-label={`${title} ${row.path}`} className="h-9 rounded-md border bg-background px-3 text-sm" value={row.value} onChange={(event) => commitLeaf(row, event.target.value)}><option value="true">是</option><option value="false">否</option></select> : <Input aria-label={`${title} ${row.path}`} title={valueLabel} value={row.value} onChange={(event) => commitLeaf(row, event.target.value)} />}<Button type="button" size="icon" variant="ghost" aria-label={`移除 ${row.path}`} onClick={() => onChange(encode(removeAtPath(root, row.path)))}><Trash2 className="h-4 w-4" /></Button></div>)}</div><div className="grid gap-2 rounded-md border border-dashed p-3 md:grid-cols-[minmax(180px,0.8fr)_minmax(240px,1.5fr)_auto]"><Input aria-label={`${title} 新增欄位路徑`} placeholder={pathLabel} value={newPath} onChange={(event) => setNewPath(event.target.value)} /><Input aria-label={`${title} 新增欄位內容`} placeholder={valueLabel} value={newValue} onChange={(event) => setNewValue(event.target.value)} /><Button type="button" size="icon" variant="outline" aria-label={`新增 ${title} 欄位`} onClick={addLeaf} disabled={!newPath.trim()}><Plus className="h-4 w-4" /></Button></div></section>;
}
