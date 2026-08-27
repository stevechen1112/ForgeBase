"use client";

import { useCallback, useEffect, useState } from "react";
import { Search, RefreshCw, ExternalLink } from "lucide-react";

import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type AdoptionApplication,
} from "@/lib/api/platform-admin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";

const STATUS_LABELS: Record<AdoptionApplication["status"], string> = {
  new: "待檢視",
  reviewing: "評估中",
  invited: "已邀請",
  declined: "暫不適合",
  archived: "已封存",
};

const SITUATION_LABELS: Record<string, string> = {
  no_site: "尚無網站",
  replace_site: "準備重做網站",
  improve_site: "希望改善現有網站",
  evaluating: "先了解可行性",
};

export default function AdoptionApplicationsPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [items, setItems] = useState<AdoptionApplication[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<AdoptionApplication | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const result = await platformAdminApi.adoptionApplications(token, {
        search: search || undefined,
        status: status || undefined,
        page_size: 100,
      });
      setItems(result.data);
      if (selected) {
        const refreshed =
          result.data.find((item) => item.id === selected.id) ?? null;
        setSelected(refreshed);
        setNote(refreshed?.internal_note ?? "");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "載入導入申請失敗");
    } finally {
      setLoading(false);
    }
  }, [token, search, status, selected]);

  useEffect(() => {
    if (!token) return;
    const timer = window.setTimeout(() => void load(), 200);
    return () => window.clearTimeout(timer);
    // selected must not trigger a refetch loop; it is refreshed after explicit saves.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, search, status]);

  async function save(nextStatus = selected?.status) {
    if (!selected || !nextStatus) return;
    setSaving(true);
    setError("");
    try {
      const updated = await platformAdminApi.updateAdoptionApplication(
        token,
        selected.id,
        {
          status: nextStatus,
          internal_note: note,
        },
      );
      setSelected(updated);
      setItems((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "更新申請失敗");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">導入申請</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            這些資料只代表有人申請評估，不會自動建立租戶、試用或銷售案件。
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => void load()}
          disabled={loading}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-3 rounded-xl border bg-card p-4 md:grid-cols-[minmax(240px,1fr)_180px]">
        <label className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜尋公司或 Email"
            className="pl-9"
          />
        </label>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="h-10 rounded-md border bg-background px-3 text-sm"
        >
          <option value="">全部狀態</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="overflow-hidden rounded-xl border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b bg-muted/40 text-left text-xs text-muted-foreground">
                  <th className="px-4 py-3">申請</th>
                  <th className="px-4 py-3">公司／產業</th>
                  <th className="px-4 py-3">聯絡人</th>
                  <th className="px-4 py-3">狀態</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => {
                      setSelected(item);
                      setNote(item.internal_note ?? "");
                    }}
                    className={`cursor-pointer border-b last:border-0 hover:bg-muted/30 ${selected?.id === item.id ? "bg-primary/5" : ""}`}
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium">{item.application_number}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {new Date(item.created_at).toLocaleString("zh-TW")}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium">{item.company_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.industry} ·{" "}
                        {SITUATION_LABELS[item.current_situation] ??
                          item.current_situation}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <p>{item.contact_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.work_email}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          item.status === "new" ? "default" : "secondary"
                        }
                      >
                        {STATUS_LABELS[item.status]}
                      </Badge>
                    </td>
                  </tr>
                ))}
                {!loading && items.length === 0 && (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-4 py-12 text-center text-muted-foreground"
                    >
                      目前沒有符合條件的申請
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="rounded-xl border bg-card p-5">
          {!selected ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              選擇一筆申請查看完整內容
            </p>
          ) : (
            <div className="space-y-5">
              <div>
                <p className="text-xs text-muted-foreground">
                  {selected.application_number}
                </p>
                <h2 className="mt-1 text-lg font-bold">
                  {selected.company_name}
                </h2>
              </div>
              <dl className="grid grid-cols-[90px_1fr] gap-x-3 gap-y-2 text-sm">
                <dt className="text-muted-foreground">聯絡人</dt>
                <dd>
                  {selected.contact_name}
                  {selected.job_title ? `／${selected.job_title}` : ""}
                </dd>
                <dt className="text-muted-foreground">Email</dt>
                <dd className="break-all">{selected.work_email}</dd>
                <dt className="text-muted-foreground">電話</dt>
                <dd>{selected.phone || "未提供"}</dd>
                <dt className="text-muted-foreground">目標市場</dt>
                <dd>{selected.target_markets || "未提供"}</dd>
                <dt className="text-muted-foreground">語言</dt>
                <dd>{selected.preferred_language}</dd>
                <dt className="text-muted-foreground">目前情況</dt>
                <dd>
                  {SITUATION_LABELS[selected.current_situation] ??
                    selected.current_situation}
                </dd>
              </dl>
              {selected.website_url && (
                <a
                  href={selected.website_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  查看現有網站 <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
              <div>
                <p className="mb-1 text-xs font-medium text-muted-foreground">
                  希望處理的問題
                </p>
                <p className="whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-sm leading-relaxed">
                  {selected.requested_scope}
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground">
                  內部備註
                </label>
                <Textarea
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  rows={5}
                  placeholder="只供 ForgeBase 團隊查看"
                />
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <select
                  value={selected.status}
                  onChange={(event) =>
                    setSelected({
                      ...selected,
                      status: event.target
                        .value as AdoptionApplication["status"],
                    })
                  }
                  className="h-10 rounded-md border bg-background px-3 text-sm"
                >
                  {Object.entries(STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <Button onClick={() => void save()} disabled={saving}>
                  {saving ? "儲存中…" : "儲存處理狀態"}
                </Button>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
