"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  Copy,
  ExternalLink,
  Globe2,
  Loader2,
  Plus,
  RefreshCw,
  Route,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";

import {
  platformAdminApi,
  type TenantDomain,
} from "@/lib/api/platform-admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = {
  token: string;
  tenantId: string;
  onChanged?: () => Promise<void> | void;
};

const STATUS_LABELS: Record<TenantDomain["status"], string> = {
  pending: "等待 DNS 設定",
  verifying: "DNS 尚未完成",
  verified: "已驗證，可啟用",
  active: "運作中",
  failed: "驗證失敗",
  suspended: "已停用",
};

function statusVariant(status: TenantDomain["status"]) {
  if (status === "active" || status === "verified") return "success" as const;
  if (status === "failed" || status === "suspended") return "destructive" as const;
  return "warning" as const;
}

function domainProgress(domain: TenantDomain) {
  const dnsReady = Boolean(domain.dns_verified_at);
  const active = domain.status === "active";
  return [
    { label: "加入網域", done: true },
    { label: "DNS 驗證", done: dnsReady },
    { label: "正式啟用", done: active },
  ];
}

export function TenantDomainManager({ token, tenantId, onChanged }: Props) {
  const [domains, setDomains] = useState<TenantDomain[]>([]);
  const [hostname, setHostname] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [copied, setCopied] = useState("");
  const [suspendTarget, setSuspendTarget] = useState<TenantDomain | null>(null);
  const [managedLabel, setManagedLabel] = useState("");
  const [renameManagedOpen, setRenameManagedOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDomains(await platformAdminApi.tenantDomains(token, tenantId));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取租戶網域");
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => {
    void load();
  }, [load]);

  const canonical = useMemo(
    () => domains.find((domain) => domain.is_canonical && domain.status === "active"),
    [domains],
  );
  const managed = domains.find((domain) => domain.domain_type === "forgebase_subdomain");

  useEffect(() => {
    if (managed && !renameManagedOpen) {
      setManagedLabel(managed.hostname.split(".")[0] ?? "");
    }
  }, [managed, renameManagedOpen]);

  async function afterMutation(successMessage: string) {
    await load();
    try {
      await onChanged?.();
    } catch {
      // The domain mutation already succeeded; a secondary panel refresh must
      // not misreport that high-impact operation as failed.
    }
    setMessage(successMessage);
  }

  async function register() {
    const normalized = hostname.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/$/, "");
    if (!normalized) return;
    setBusy("register");
    setError("");
    setMessage("");
    try {
      await platformAdminApi.registerTenantDomain(token, tenantId, normalized);
      setHostname("");
      await afterMutation("自有網域已加入。請依下方指示設定 DNS，原免費網域仍會正常運作。");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "加入自有網域失敗");
    } finally {
      setBusy(null);
    }
  }

  async function renameManaged() {
    if (!managed) return;
    const label = managedLabel.trim().toLowerCase();
    if (!label) return;
    setBusy("rename-managed");
    setError("");
    setMessage("");
    try {
      const result = await platformAdminApi.renameManagedTenantDomain(token, tenantId, label);
      setManagedLabel(result.hostname.split(".")[0] ?? label);
      setRenameManagedOpen(false);
      await afterMutation(
        `免費網址已變更為 ${result.hostname}；租戶代碼與既有資料關聯不受影響。`,
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "變更免費網址失敗");
    } finally {
      setBusy(null);
    }
  }

  async function verify(domain: TenantDomain) {
    setBusy(`verify:${domain.id}`);
    setError("");
    setMessage("");
    try {
      const result = await platformAdminApi.verifyTenantDomain(token, tenantId, domain.id);
      await afterMutation(
        result.status === "verified" || result.status === "active"
          ? "DNS 所有權與流量指向均已驗證。"
          : "DNS 尚未完整生效；請依缺少項目修正後再檢查。",
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "DNS 驗證失敗");
    } finally {
      setBusy(null);
    }
  }

  async function activate(domain: TenantDomain) {
    setBusy(`activate:${domain.id}`);
    setError("");
    setMessage("");
    try {
      await platformAdminApi.activateTenantDomain(token, tenantId, domain.id);
      await afterMutation(
        `${domain.hostname} 已成為正式網域；${managed?.hostname ?? "免費網域"} 會永久轉址至新網址。`,
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "啟用自有網域失敗");
    } finally {
      setBusy(null);
    }
  }

  async function suspend() {
    if (!suspendTarget) return;
    const domain = suspendTarget;
    setBusy(`suspend:${domain.id}`);
    setError("");
    setMessage("");
    try {
      await platformAdminApi.suspendTenantDomain(token, tenantId, domain.id);
      setSuspendTarget(null);
      await afterMutation(
        `${domain.hostname} 已停用，正式網址已安全回復為 ${managed?.hostname ?? "ForgeBase 免費網域"}。`,
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "停用自有網域失敗");
    } finally {
      setBusy(null);
    }
  }

  async function copyValue(key: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(key);
      window.setTimeout(() => setCopied((current) => current === key ? "" : current), 1600);
    } catch {
      setError("無法存取剪貼簿，請手動選取並複製記錄值。");
    }
  }

  return (
    <section id="tenant-domains" className="scroll-mt-16 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Globe2 className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold">網域與正式網址</h2>
          </div>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted-foreground">
            每個租戶永遠保有一個免費 ForgeBase 子網域。自有網域必須完成真實 DNS 驗證後才能切換，切換失敗不會影響原站。
          </p>
        </div>
        <Button type="button" size="sm" variant="outline" onClick={() => void load()} disabled={loading || Boolean(busy)}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          重新整理
        </Button>
      </div>

      {canonical && (
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-emerald-700">目前正式網址</p>
            <p className="mt-1 font-mono text-sm font-semibold text-emerald-950">https://{canonical.hostname}</p>
          </div>
          <Button asChild size="sm" variant="outline" className="border-emerald-300 bg-white">
            <a href={`https://${canonical.hostname}`} target="_blank" rel="noreferrer">
              開啟網站 <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </Button>
        </div>
      )}

      {error && <p role="alert" aria-live="assertive" className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
      {message && <p role="status" aria-live="polite" className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}

      <div className="mt-5 space-y-3">
        {loading ? (
          <div className="flex items-center gap-2 rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> 讀取網域狀態中…
          </div>
        ) : domains.map((domain) => {
          const custom = domain.domain_type === "custom";
          const canActivate = custom && (domain.status === "verified" || (domain.status === "active" && !domain.is_canonical));
          const canVerify = custom && domain.status !== "verified";
          const progress = domainProgress(domain);
          return (
            <article key={domain.id} className={`rounded-lg border p-4 ${domain.is_canonical ? "border-primary/40 bg-primary/[0.03]" : "border-border"}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="break-all font-mono text-sm font-semibold">{domain.hostname}</p>
                    <Badge variant={custom ? "outline" : "info"}>{custom ? "租戶自有網域" : "免費子網域"}</Badge>
                    <Badge variant={statusVariant(domain.status)}>{STATUS_LABELS[domain.status]}</Badge>
                    {domain.is_canonical && <Badge variant="success">正式網址</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {domain.redirect_to_canonical && canonical
                      ? `此網址會以 308 永久轉址至 ${canonical.hostname}`
                      : custom
                        ? `TLS：${domain.tls_status === "active" ? "憑證已生效" : "啟用後由 ForgeBase 自動簽發"}`
                        : "ForgeBase 管理 DNS 與 TLS，租戶不需額外設定。"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {!custom && (
                    <Button type="button" size="sm" variant="outline" disabled={Boolean(busy)} onClick={() => setRenameManagedOpen(true)}>
                      變更免費網址
                    </Button>
                  )}
                  {canVerify && (
                    <Button type="button" size="sm" variant="outline" disabled={Boolean(busy)} onClick={() => void verify(domain)}>
                      {busy === `verify:${domain.id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                      檢查 DNS
                    </Button>
                  )}
                  {canActivate && (
                    <Button type="button" size="sm" disabled={Boolean(busy)} onClick={() => void activate(domain)}>
                      {busy === `activate:${domain.id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                      設為正式網址
                    </Button>
                  )}
                  {custom && domain.status === "active" && (
                    <Button type="button" size="sm" variant="destructive" disabled={Boolean(busy)} onClick={() => setSuspendTarget(domain)}>
                      停用網域
                    </Button>
                  )}
                </div>
              </div>

              {custom && (
                <div className="mt-4 flex items-center gap-1.5" aria-label="自有網域啟用進度">
                  {progress.map((step, index) => (
                    <div key={step.label} className="contents">
                      {index > 0 && <div className={`h-px w-5 ${step.done ? "bg-emerald-400" : "bg-border"}`} />}
                      <span className={`rounded-full px-2 py-1 text-[11px] ${step.done ? "bg-emerald-100 text-emerald-800" : "bg-muted text-muted-foreground"}`}>
                        {step.done ? "✓ " : ""}{step.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {custom && domain.status !== "active" && domain.verification && (
                <div className="mt-4 rounded-lg bg-muted/40 p-4">
                  <div className="flex items-start gap-2 text-xs text-muted-foreground">
                    <Route className="mt-0.5 h-4 w-4 shrink-0" />
                    <p>在網域 DNS 後台新增以下兩筆記錄。若使用 Cloudflare，驗證期間請將 Proxy status 設為 DNS only；根網域請用 DNS 供應商的 ALIAS／ANAME。</p>
                  </div>
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    <DnsRecord
                      title="1. 證明網域所有權"
                      type={domain.verification.record_type}
                      name={domain.verification.record_name}
                      value={domain.verification.record_value}
                      copied={copied}
                      copyValue={copyValue}
                      recordKey={`${domain.id}:txt`}
                    />
                    <DnsRecord
                      title="2. 將網站流量指向 ForgeBase"
                      type="CNAME／ALIAS"
                      name={domain.routing.record_name}
                      value={domain.routing.record_value}
                      copied={copied}
                      copyValue={copyValue}
                      recordKey={`${domain.id}:route`}
                    />
                  </div>
                  {domain.failure_reason && (
                    <p className="mt-3 flex items-start gap-2 text-xs text-amber-800">
                      <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                      {domain.failure_reason}
                    </p>
                  )}
                  {domain.last_checked_at && <p className="mt-2 text-[11px] text-muted-foreground">最後檢查：{new Date(domain.last_checked_at).toLocaleString("zh-TW")}</p>}
                </div>
              )}
            </article>
          );
        })}
      </div>

      <div className="mt-5 rounded-lg border border-dashed p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[240px] flex-1 space-y-2">
            <Label htmlFor="tenant-custom-domain">加入租戶自有網域</Label>
            <Input
              id="tenant-custom-domain"
              value={hostname}
              onChange={(event) => setHostname(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void register();
                }
              }}
              placeholder="www.customer.com"
              autoCapitalize="none"
              spellCheck={false}
            />
          </div>
          <Button type="button" onClick={() => void register()} disabled={!hostname.trim() || Boolean(busy)}>
            {busy === "register" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            加入網域
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">加入只會建立驗證工作，不會立即切換正式網站，也不會讓現有網址中斷。</p>
      </div>

      <Dialog open={Boolean(suspendTarget)} onOpenChange={(open) => { if (!open && !busy) setSuspendTarget(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>停用 {suspendTarget?.hostname}？</DialogTitle>
            <DialogDescription>
              此網域會停止由 ForgeBase 提供服務；若它目前是正式網址，系統會在同一筆交易中回復為 {managed?.hostname ?? "免費 ForgeBase 子網域"}。DNS 記錄不會由 ForgeBase 刪除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setSuspendTarget(null)} disabled={Boolean(busy)}>取消</Button>
            <Button type="button" variant="destructive" onClick={() => void suspend()} disabled={Boolean(busy)}>
              {busy?.startsWith("suspend:") && <Loader2 className="h-4 w-4 animate-spin" />}
              確認停用並回復
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={renameManagedOpen} onOpenChange={(open) => { if (!busy) setRenameManagedOpen(open); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>變更免費 ForgeBase 網址</DialogTitle>
            <DialogDescription>
              這只會變更 ForgeBase 提供的子網域，不會修改租戶代碼。舊免費網址會立即停止服務；請在正式對外公布前完成變更。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="managed-domain-label">子網域代碼</Label>
            <div className="flex items-center gap-2">
              <Input
                id="managed-domain-label"
                value={managedLabel}
                onChange={(event) => setManagedLabel(event.target.value.toLowerCase())}
                placeholder="axisform"
                autoCapitalize="none"
                spellCheck={false}
              />
              <span className="shrink-0 text-sm text-muted-foreground">.forgebase.com</span>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setRenameManagedOpen(false)} disabled={Boolean(busy)}>取消</Button>
            <Button type="button" onClick={() => void renameManaged()} disabled={!managedLabel.trim() || Boolean(busy)}>
              {busy === "rename-managed" && <Loader2 className="h-4 w-4 animate-spin" />}
              確認變更免費網址
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function DnsRecord({
  title,
  type,
  name,
  value,
  recordKey,
  copied,
  copyValue,
}: {
  title: string;
  type: string;
  name: string;
  value: string;
  recordKey: string;
  copied: string;
  copyValue: (key: string, value: string) => Promise<void>;
}) {
  return (
    <div className="rounded-md border bg-background p-3">
      <p className="text-xs font-semibold">{title}</p>
      <dl className="mt-2 space-y-2 text-xs">
        <div><dt className="text-muted-foreground">類型</dt><dd className="mt-0.5 font-mono">{type}</dd></div>
        <div><dt className="text-muted-foreground">名稱</dt><dd className="mt-0.5 break-all font-mono">{name}</dd></div>
        <div>
          <dt className="text-muted-foreground">值</dt>
          <dd className="mt-0.5 flex items-start gap-2">
            <span className="min-w-0 flex-1 break-all font-mono">{value}</span>
            <Button type="button" size="icon" variant="ghost" className="h-7 w-7 shrink-0" aria-label={`複製 ${title} 的值`} onClick={() => void copyValue(recordKey, value)}>
              {copied === recordKey ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
            </Button>
          </dd>
        </div>
      </dl>
    </div>
  );
}
