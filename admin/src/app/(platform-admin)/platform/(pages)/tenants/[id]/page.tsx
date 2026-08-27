"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type AcceptanceStatus, type AdminUser, type DeliveryStage, type FeatureCatalog, type FeatureCatalogItem, type PlatformAuditItem, type SiteBuild, type SiteTemplate, type TenantDetail, type TenantUpdate } from "@/lib/api/platform-admin";
import {
  ArrowLeft, AlertCircle, Users, Package, ClipboardList, Eye,
  Settings2, CheckCircle2, XCircle, Globe2, ExternalLink, History, TriangleAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PlatformSiteProfileEditor } from "@/components/platform/PlatformSiteProfileEditor";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
const DELIVERY_STAGE_OPTIONS: { value: DeliveryStage; label: string; description: string }[] = [
  { value: "intake", label: "需求確認", description: "正在確認客戶、範本與交付範圍" },
  { value: "content", label: "內容準備", description: "蒐集與整理品牌、產品與素材" },
  { value: "build", label: "網站製作", description: "ForgeBase 團隊調整範本與串接資料" },
  { value: "qa", label: "內部驗收", description: "檢查內容、表單、語系與公開頁面" },
  { value: "client_review", label: "客戶確認", description: "等待客戶檢視、修正或同意交付" },
  { value: "launch_ready", label: "可上線", description: "技術與內容已就緒，等待上線安排" },
  { value: "live", label: "已交付／上線", description: "網站已交付，客戶可進後台維護內容" },
  { value: "on_hold", label: "暫停", description: "等待素材、決策或其他外部條件" },
];
const ACCEPTANCE_OPTIONS: { value: AcceptanceStatus; label: string }[] = [
  { value: "pending", label: "尚未提出確認" },
  { value: "requested", label: "已請客戶確認" },
  { value: "accepted", label: "客戶已確認" },
  { value: "waived", label: "不需客戶確認" },
];

const READINESS_LABELS: Record<string, string> = {
  active_owner: "有效 Owner 帳號",
  brand_name: "品牌名稱",
  contact_email: "聯絡信箱",
  site_url: "網站網址",
  primary_domain: "主要網域",
  domain_matches_site_url: "網域與網站網址一致",
  supported_locales: "支援語系",
  template_exists: "有效產業範本",
  cms_adapter_connected: "CMS 串接確認",
};

const AUDIT_LABELS: Record<string, string> = {
  "tenant.provisioned": "建立租戶",
  "tenant.updated": "更新租戶設定",
  "site_build.created": "建立網站交付單",
  "site_build.updated": "更新網站交付設定",
  "site_build.validated": "檢查上線條件",
  "site_build.publish_blocked": "發布被上線條件阻擋",
  "site_build.published": "標記網站發布",
};

export default function TenantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;

  const [tenant, setTenant] = useState<TenantDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [featureCatalog, setFeatureCatalog] = useState<FeatureCatalog | null>(null);
  const [editFeatureOverrides, setEditFeatureOverrides] = useState<Record<string, boolean>>({});
  const [siteBuild, setSiteBuild] = useState<SiteBuild | null>(null);
  const [templates, setTemplates] = useState<SiteTemplate[]>([]);
  const [auditLog, setAuditLog] = useState<PlatformAuditItem[]>([]);
  const [editTemplate, setEditTemplate] = useState("handtool-company");
  const [editDomain, setEditDomain] = useState("");
  const [editLocales, setEditLocales] = useState<string[]>(["en"]);
  const [confirmStatusChange, setConfirmStatusChange] = useState(false);
  const [platformUsers, setPlatformUsers] = useState<AdminUser[]>([]);
  const [editDeliveryStage, setEditDeliveryStage] = useState<DeliveryStage>("intake");
  const [editDeliveryOwnerId, setEditDeliveryOwnerId] = useState<string>("unassigned");
  const [editTargetLaunchAt, setEditTargetLaunchAt] = useState("");
  const [editHandoffAt, setEditHandoffAt] = useState("");
  const [editAcceptanceStatus, setEditAcceptanceStatus] = useState<AcceptanceStatus>("pending");
  const [editInternalNote, setEditInternalNote] = useState("");

  useEffect(() => {
    if (!token || !id) return;
    platformAdminApi.tenant(token, id)
      .then(async (tenantDetail) => {
        const [build, siteTemplates, audit, users, catalog] = await Promise.all([
          tenantDetail.site_build_status
            ? platformAdminApi.siteBuild(token, id)
            : Promise.resolve(null),
          platformAdminApi.siteTemplates(token),
          platformAdminApi.tenantAuditLog(token, id).catch(() => []),
          platformAdminApi.users(token, { limit: 200 }).catch(() => []),
          platformAdminApi.featureCatalog(token),
        ]);
        return [tenantDetail, build, siteTemplates, audit, users, catalog] as const;
      })
      .then(([t, build, siteTemplates, audit, users, catalog]) => {
        setTenant(t);
        setEditFeatureOverrides(t.feature_overrides || {});
        setFeatureCatalog(catalog);
        setSiteBuild(build);
        setTemplates(siteTemplates);
        setAuditLog(audit);
        setPlatformUsers(users.filter((user) => user.is_superuser && user.is_active));
        if (build) {
          setEditTemplate(build.template_key);
          setEditDomain(build.primary_domain || "");
          setEditLocales(build.locales.length ? build.locales : ["en"]);
          setEditDeliveryStage(build.delivery_stage);
          setEditDeliveryOwnerId(build.delivery_owner_id || "unassigned");
          setEditTargetLaunchAt(build.target_launch_at?.slice(0, 10) || "");
          setEditHandoffAt(build.handoff_at?.slice(0, 10) || "");
          setEditAcceptanceStatus(build.acceptance_status);
          setEditInternalNote(build.internal_note || "");
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, id]);

  async function toggleActive() {
    if (!token || !tenant) return;
    setSaving(true);
    try {
      const update: TenantUpdate = { is_active: !tenant.is_active };
      await platformAdminApi.updateTenant(token, tenant.id, update);
      setTenant((prev) => prev ? { ...prev, is_active: !prev.is_active } : prev);
      setConfirmStatusChange(false);
      setAuditLog(await platformAdminApi.tenantAuditLog(token, tenant.id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "更新失敗");
    } finally {
      setSaving(false);
    }
  }

  function effectiveFeature(item: FeatureCatalogItem) {
    return editFeatureOverrides[item.key] ?? item.default_enabled;
  }

  function toggleFeature(item: FeatureCatalogItem) {
    if (!item.configurable) return;
    const nextValue = !effectiveFeature(item);
    const defaultValue = item.default_enabled;
    setEditFeatureOverrides((current) => {
      const next = { ...current };
      if (nextValue === defaultValue) delete next[item.key];
      else next[item.key] = nextValue;
      return next;
    });
  }

  async function saveProductAccess() {
    if (!token || !tenant) return;
    setSaving(true); setError(null);
    try {
      await platformAdminApi.updateTenant(token, tenant.id, {
        feature_overrides: editFeatureOverrides,
      });
      const refreshed = await platformAdminApi.tenant(token, tenant.id);
      setTenant(refreshed);
      setEditFeatureOverrides(refreshed.feature_overrides || {});
      setAuditLog(await platformAdminApi.tenantAuditLog(token, tenant.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "功能權限儲存失敗");
    } finally { setSaving(false); }
  }

  async function saveSiteSettings() {
    if (!token || !tenant) return;
    setSaving(true); setError(null);
    try {
      const payload = { template_key: editTemplate, primary_domain: editDomain, locales: editLocales };
      const result = siteBuild
        ? await platformAdminApi.updateSiteBuild(token, tenant.id, payload)
        : await platformAdminApi.createSiteBuild(token, tenant.id, payload);
      setSiteBuild(result);
      setAuditLog(await platformAdminApi.tenantAuditLog(token, tenant.id));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "網站交付設定儲存失敗"); }
    finally { setSaving(false); }
  }

  function toggleLocale(locale: string) {
    setEditLocales((current) => current.includes(locale)
      ? current.filter((item) => item !== locale)
      : [...current, locale]);
  }

  async function runSiteAction(action: "validate" | "publish") {
    if (!token || !tenant) return;
    setSaving(true); setError(null);
    try {
      const result = action === "validate"
        ? await platformAdminApi.validateSiteBuild(token, tenant.id)
        : await platformAdminApi.publishSiteBuild(token, tenant.id);
      setSiteBuild(result);
      setAuditLog(await platformAdminApi.tenantAuditLog(token, tenant.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "網站交付檢查失敗");
      setAuditLog(await platformAdminApi.tenantAuditLog(token, tenant.id).catch(() => auditLog));
    } finally { setSaving(false); }
  }

  async function markAdapterVerified() {
    if (!token || !tenant || !siteBuild) return;
    setSaving(true); setError(null);
    try {
      setSiteBuild(await platformAdminApi.updateSiteBuild(token, tenant.id, { cms_connected: !siteBuild.cms_connected }));
      setAuditLog(await platformAdminApi.tenantAuditLog(token, tenant.id));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "更新串接狀態失敗"); }
    finally { setSaving(false); }
  }

  async function saveDeliveryWorkOrder() {
    if (!token || !tenant || !siteBuild) return;
    setSaving(true); setError(null);
    try {
      const result = await platformAdminApi.updateSiteBuild(token, tenant.id, {
        delivery_stage: editDeliveryStage,
        delivery_owner_id: editDeliveryOwnerId === "unassigned" ? null : editDeliveryOwnerId,
        target_launch_at: editTargetLaunchAt ? new Date(`${editTargetLaunchAt}T12:00:00`).toISOString() : null,
        handoff_at: editHandoffAt ? new Date(`${editHandoffAt}T12:00:00`).toISOString() : null,
        acceptance_status: editAcceptanceStatus,
        internal_note: editInternalNote.trim() || null,
      });
      setSiteBuild(result);
      setEditDeliveryStage(result.delivery_stage);
      setEditDeliveryOwnerId(result.delivery_owner_id || "unassigned");
      setEditTargetLaunchAt(result.target_launch_at?.slice(0, 10) || "");
      setEditHandoffAt(result.handoff_at?.slice(0, 10) || "");
      setEditAcceptanceStatus(result.acceptance_status);
      setEditInternalNote(result.internal_note || "");
      setAuditLog(await platformAdminApi.tenantAuditLog(token, tenant.id));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "交付工作單儲存失敗"); }
    finally { setSaving(false); }
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-6 w-48 rounded bg-muted" />
        <div className="h-32 rounded-xl bg-muted" />
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
        <AlertCircle className="h-4 w-4 shrink-0" />
        {error ?? "找不到租戶"}
      </div>
    );
  }

  const stats = [
    { icon: Users, label: "用戶", value: tenant.user_count },
    { icon: Package, label: "商品", value: tenant.product_count },
    { icon: ClipboardList, label: "RFQ（30 天／總計）", value: `${tenant.rfq_count_30d}／${tenant.rfq_count}` },
    { icon: Eye, label: "訪客", value: tenant.visitor_count },
  ];
  const selectedTemplate = templates.find((template) => template.key === editTemplate);
  const siteSettingsChanged = !siteBuild
    || editTemplate !== siteBuild.template_key
    || editDomain.trim().toLowerCase() !== (siteBuild.primary_domain || "")
    || [...editLocales].sort().join(",") !== [...siteBuild.locales].sort().join(",");
  const deliveryWorkOrderChanged = !!siteBuild && (
    editDeliveryStage !== siteBuild.delivery_stage
    || editDeliveryOwnerId !== (siteBuild.delivery_owner_id || "unassigned")
    || editTargetLaunchAt !== (siteBuild.target_launch_at?.slice(0, 10) || "")
    || editHandoffAt !== (siteBuild.handoff_at?.slice(0, 10) || "")
    || editAcceptanceStatus !== siteBuild.acceptance_status
    || editInternalNote !== (siteBuild.internal_note || "")
  );
  const productAccessChanged = JSON.stringify(editFeatureOverrides) !== JSON.stringify(tenant.feature_overrides || {});
  const catalogGroups = featureCatalog
    ? Array.from(new Set(featureCatalog.features.map((feature) => feature.group)))
    : [];

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.push("/platform/tenants")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        返回租戶列表
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{tenant.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Slug: {tenant.slug} · 建立: {tenant.created_at?.slice(0, 10)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setConfirmStatusChange(true)}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors"
          >
            {tenant.is_active ? (
              <><CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> 活躍中（點擊停用）</>
            ) : (
              <><XCircle className="h-3.5 w-3.5 text-red-400" /> 已停用（點擊啟用）</>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {confirmStatusChange && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <div className="flex items-start gap-2"><TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" /><p><strong>{tenant.is_active ? "確認停用租戶？" : "確認重新啟用租戶？"}</strong><br />{tenant.is_active ? "停用後，該租戶使用者與公開網站資料存取會立即被封鎖。" : "重新啟用後，該租戶帳號與公開資料存取會恢復。"}</p></div>
          <div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => setConfirmStatusChange(false)}>取消</Button><Button variant={tenant.is_active ? "destructive" : "default"} size="sm" disabled={saving} onClick={toggleActive}>{saving ? "處理中..." : tenant.is_active ? "確認停用" : "確認啟用"}</Button></div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stats.map(({ icon: Icon, label, value }) => (
          <div key={label} className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <div className="mb-2 flex items-center gap-2 text-muted-foreground">
              <Icon className="h-4 w-4" />
              <span className="text-xs text-muted-foreground">{label}</span>
            </div>
            <p className="text-2xl font-bold tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      {/* Single-product capability governance */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">功能治理</h3>
            </div>
            <p className="mt-1 max-w-3xl text-xs text-muted-foreground">
              核心能力預設開啟；試行、外部供應商與退場觀察能力依就緒狀態個別控管。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {editFeatureOverrides && Object.keys(editFeatureOverrides).length > 0 && (
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
                自訂 {Object.keys(editFeatureOverrides).length} 項
              </span>
            )}
            <Button size="sm" disabled={saving || !productAccessChanged} onClick={saveProductAccess}>
              {saving ? "儲存中..." : "儲存功能權限"}
            </Button>
          </div>
        </div>

        {featureCatalog ? (
          <div className="mt-6 space-y-5 border-t border-border pt-5">
            {catalogGroups.map((group) => (
              <div key={group}>
                <p className="mb-2 text-xs font-semibold text-foreground">{group}</p>
                <div className="grid gap-2 lg:grid-cols-2">
                  {featureCatalog.features.filter((feature) => feature.group === group).map((feature) => {
                    const enabled = effectiveFeature(feature);
                    return (
                      <button
                        key={feature.key}
                        type="button"
                        disabled={!feature.configurable}
                        onClick={() => toggleFeature(feature)}
                        className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-colors ${!feature.configurable ? "cursor-not-allowed border-dashed bg-muted/30 opacity-70" : enabled ? "border-emerald-300 bg-emerald-50/50" : "border-border hover:bg-muted/40"}`}
                      >
                        <span className={`mt-0.5 flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition-colors ${enabled ? "justify-end bg-emerald-600" : "justify-start bg-muted-foreground/30"}`}>
                          <span className="h-4 w-4 rounded-full bg-white shadow-sm" />
                        </span>
                        <span className="min-w-0">
                          <span className="flex flex-wrap items-center gap-2 text-sm font-medium">
                            {feature.label}
                            {!feature.configurable && <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{feature.status === "core_required" ? "核心固定開啟" : "尚不可開通"}</span>}
                          </span>
                          <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground">{feature.description}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        ) : <p className="mt-5 text-xs text-muted-foreground">讀取功能清單中…</p>}
      </div>

      {token && <PlatformSiteProfileEditor token={token} tenantId={tenant.id} />}

      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2"><Globe2 className="h-4 w-4 text-muted-foreground" /><h3 className="text-sm font-semibold">網站交付</h3></div>
            <p className="mt-1 text-xs text-muted-foreground">設定範本、正式網域與語系；完成 CMS 串接後才能通過發布檢查。</p>
          </div>
          {siteBuild && <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${siteBuild.status === "published" ? "bg-emerald-100 text-emerald-700" : siteBuild.status === "blocked" ? "bg-amber-100 text-amber-800" : "bg-muted text-muted-foreground"}`}>{siteBuild.status}</span>}
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="space-y-1.5 text-xs font-medium">產業範本
            <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-normal" value={editTemplate} onChange={(e) => setEditTemplate(e.target.value)}>
              {templates.map((template) => <option key={template.key} value={template.key}>{template.name} · {template.cms_connected ? "可串 CMS" : "靜態展示"}</option>)}
            </select>
          </label>
          <label className="space-y-1.5 text-xs font-medium">主要網域
            <Input value={editDomain} onChange={(e) => setEditDomain(e.target.value)} placeholder="customer.example.com" className="font-normal" />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-4 text-sm">
          <span className="text-xs font-medium">公開語系</span>
          {["en", "zh-TW"].map((locale) => <label key={locale} className="flex items-center gap-2"><input type="checkbox" checked={editLocales.includes(locale)} onChange={() => toggleLocale(locale)} />{locale}</label>)}
          <Button size="sm" variant="outline" disabled={saving || !siteSettingsChanged || editLocales.length === 0} onClick={saveSiteSettings}>{siteBuild ? "儲存交付設定" : "建立交付單"}</Button>
          {selectedTemplate?.demo_url && <a className="inline-flex items-center gap-1 text-sm text-primary hover:underline" href={selectedTemplate.demo_url} target="_blank" rel="noreferrer">查看範本 <ExternalLink className="h-3.5 w-3.5" /></a>}
        </div>

        {siteBuild && (
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <p className="text-xs text-muted-foreground">{siteBuild.cms_connected ? "CMS 串接已由平台人員確認" : selectedTemplate?.publish_supported ? "尚未確認 CMS 串接" : "此範本只有靜態 Demo，不能發布"}</p>
            <div className="flex flex-wrap gap-2">
              {selectedTemplate?.publish_supported && <Button variant="outline" size="sm" onClick={markAdapterVerified} disabled={saving}>{siteBuild.cms_connected ? "取消串接確認" : "確認 CMS 串接完成"}</Button>}
              <Button variant="outline" size="sm" onClick={() => runSiteAction("validate")} disabled={saving}>檢查上線條件</Button>
              <Button size="sm" onClick={() => runSiteAction("publish")} disabled={saving || !siteBuild.cms_connected || siteSettingsChanged}>標記發布</Button>
            </div>
          </div>
        )}
        {siteBuild?.readiness?.checks && <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(siteBuild.readiness.checks).map(([name, passed]) => <div key={name} className={`rounded border px-3 py-2 text-xs ${passed ? "border-green-200 bg-green-50 text-green-700" : "border-amber-200 bg-amber-50 text-amber-800"}`}>{passed ? "通過" : "待補"} · {READINESS_LABELS[name] || name}</div>)}</div>}
        {siteBuild?.last_error && <p className="mt-3 text-xs text-amber-800">待補項目：{siteBuild.last_error.split(", ").map((item) => READINESS_LABELS[item] || item).join("、")}</p>}
      </div>

      {siteBuild && (
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">交付工作單</h3>
              <p className="mt-1 text-xs text-muted-foreground">這是 ForgeBase 團隊內部的交付追蹤；不會顯示給客戶，也不會自動對外發信。</p>
            </div>
            <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium">{DELIVERY_STAGE_OPTIONS.find((item) => item.value === editDeliveryStage)?.label}</span>
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <label className="space-y-1.5 text-xs font-medium">交付階段
              <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-normal" value={editDeliveryStage} onChange={(event) => setEditDeliveryStage(event.target.value as DeliveryStage)}>
                {DELIVERY_STAGE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="space-y-1.5 text-xs font-medium">負責同仁
              <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-normal" value={editDeliveryOwnerId} onChange={(event) => setEditDeliveryOwnerId(event.target.value)}>
                <option value="unassigned">尚未指派</option>
                {platformUsers.map((user) => <option key={user.id} value={user.id}>{user.full_name || user.email}</option>)}
              </select>
            </label>
            <label className="space-y-1.5 text-xs font-medium">預計上線日
              <Input type="date" value={editTargetLaunchAt} onChange={(event) => setEditTargetLaunchAt(event.target.value)} className="font-normal" />
            </label>
            <label className="space-y-1.5 text-xs font-medium">客戶確認
              <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-normal" value={editAcceptanceStatus} onChange={(event) => setEditAcceptanceStatus(event.target.value as AcceptanceStatus)}>
                {ACCEPTANCE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="space-y-1.5 text-xs font-medium">交付／上線完成日
              <Input type="date" value={editHandoffAt} onChange={(event) => setEditHandoffAt(event.target.value)} className="font-normal" />
            </label>
            <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">{DELIVERY_STAGE_OPTIONS.find((item) => item.value === editDeliveryStage)?.description}</div>
          </div>
          <label className="mt-4 block space-y-1.5 text-xs font-medium">內部備註
            <Textarea value={editInternalNote} onChange={(event) => setEditInternalNote(event.target.value)} rows={4} maxLength={4000} placeholder="例如：待客戶提供型錄、Logo 或確認網域；僅供團隊內部查看。" className="font-normal" />
          </label>
          <div className="mt-4 flex justify-end"><Button size="sm" onClick={saveDeliveryWorkOrder} disabled={saving || !deliveryWorkOrderChanged}>{saving ? "儲存中..." : "儲存交付工作單"}</Button></div>
        </div>
      )}

      {/* Users */}
      {tenant.users.length > 0 && (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          <div className="border-b border-border px-5 py-3">
            <h3 className="text-sm font-semibold">用戶列表 ({tenant.users.length})</h3>
          </div>
          <div className="max-w-full overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <tbody className="divide-y divide-border">
              {tenant.users.map((u) => (
                <tr key={u.id} className="hover:bg-muted/30">
                  <td className="px-5 py-2.5 font-medium">{u.email}</td>
                  <td className="px-5 py-2.5 text-muted-foreground">{u.full_name}</td>
                  <td className="px-5 py-2.5">
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                      {u.role}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">
                    {u.is_active ? "活躍" : "停用"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {/* Recent RFQs */}
      {tenant.recent_rfqs.length > 0 && (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          <div className="border-b border-border px-5 py-3">
            <h3 className="text-sm font-semibold">最近 RFQ</h3>
          </div>
          <div className="max-w-full overflow-x-auto">
          <table className="w-full min-w-[680px] text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-left text-xs font-medium uppercase text-muted-foreground">
                <th className="px-5 py-2">聯絡人</th>
                <th className="px-5 py-2">Email</th>
                <th className="px-5 py-2">狀態</th>
                <th className="px-5 py-2">提交時間</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tenant.recent_rfqs.map((r) => (
                <tr key={r.id} className="hover:bg-muted/30">
                  <td className="px-5 py-2.5 font-medium">{r.contact_name}</td>
                  <td className="px-5 py-2.5 text-muted-foreground">{r.contact_email}</td>
                  <td className="px-5 py-2.5">
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{r.status}</span>
                  </td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">
                    {r.submitted_at?.slice(0, 16).replace("T", " ") ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        <div className="flex items-center gap-2 border-b border-border px-5 py-3"><History className="h-4 w-4 text-muted-foreground" /><h3 className="text-sm font-semibold">平台操作紀錄</h3></div>
        {auditLog.length === 0 ? <p className="p-5 text-sm text-muted-foreground">尚無平台操作紀錄；本功能會從本次更新後開始留下紀錄。</p> : (
          <div className="divide-y divide-border">
            {auditLog.map((item) => (
              <div key={item.id} className="flex flex-wrap items-start justify-between gap-3 px-5 py-3">
                <div><p className="text-sm font-medium">{AUDIT_LABELS[item.action] || item.action}</p><p className="mt-0.5 text-xs text-muted-foreground">{item.actor_email} · {Object.keys(item.changes).join("、") || "無欄位異動"}</p></div>
                <time className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("zh-TW")}</time>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
