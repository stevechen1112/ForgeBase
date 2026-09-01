"use client";
/**
 * LocaleSwitcher — locale-variant bar for content edit forms.
 *
 * Buyer-locale drafts are generated from the tenant source locale and stay
 * unpublished until the editor uses the existing Publish action.
 */
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { SUPPORTED_LOCALES, localeLabel, toContentLocale } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth/store";
import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { localeDraftApi } from "@/lib/api/content";
import { API_BASE, ApiError, apiClient, buildApiHeaders } from "@/lib/api/client";

type Variant = { id: string; locale: string; status?: string; updated_at?: string };

type Props = {
  entityType: string;
  basePath: string;
  id?: string;
  slug: string;
  currentLocale: string;
  variants?: Variant[];
  currentStatus?: string;
  currentUpdatedAt?: string;
  pairField?: "slug" | "variant_key";
};

const ENTITY_PATH: Record<string, string> = {
  product: "products",
  category: "categories",
  page: "pages",
  application: "applications",
  faq: "faqs",
  certification: "certifications",
  capability: "capabilities",
  comparison: "comparisons",
};

function toSourceLocale(raw: string | null | undefined): string {
  return toContentLocale(raw, "zh-tw");
}

export function LocaleSwitcher({
  entityType,
  basePath,
  id,
  slug,
  currentLocale,
  variants: initialVariants = [],
  currentStatus,
  currentUpdatedAt,
  pairField = "slug",
}: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const { hasFeature } = useCapabilities();
  const canDraft = hasFeature("multilingual");

  const [sourceLocale, setSourceLocale] = useState("zh-tw");
  const [variants, setVariants] = useState<Variant[]>(initialVariants);
  const [pairCurrent, setPairCurrent] = useState<Variant | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const entityPath = ENTITY_PATH[entityType] ?? `${entityType}s`;
  const current = toContentLocale(currentLocale);

  const loadVariants = async () => {
    if (!token || !slug) return;
    const params: Record<string, string | number> = { page_size: 20 };
    params[pairField] = slug;
    if (entityPath === "categories") params.locale = "all";
    try {
      const res = await apiClient.get<{ data: Variant[] }>(
        `/content/${entityPath}?${new URLSearchParams(params as Record<string, string>).toString()}`,
        token,
      );
      const rows = (res.data ?? []) as Variant[];
      setVariants(rows.filter((row) => row.id !== id));
      setPairCurrent(rows.find((row) => row.id === id) ?? null);
    } catch {
      /* keep current */
    }
  };

  useEffect(() => {
    if (!token) return;
    fetch(`${API_BASE}/site-profile`, { headers: buildApiHeaders(token) })
      .then((res) => (res.ok ? res.json() : null))
      .then((profile) => {
        if (profile?.default_locale) setSourceLocale(toSourceLocale(profile.default_locale));
      })
      .catch(() => undefined);
  }, [token]);

  useEffect(() => {
    void loadVariants();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, slug, id]);

  if (!id || !slug) return null;

  const allRows: Variant[] = [
    {
      id,
      locale: current,
      status: currentStatus ?? pairCurrent?.status,
      updated_at: pairCurrent?.updated_at ?? currentUpdatedAt,
    },
    ...variants,
  ];
  const sourceRow = allRows.find((row) => toContentLocale(row.locale) === sourceLocale);
  const missing = SUPPORTED_LOCALES.filter(
    (l) => l.value !== current && !allRows.some((v) => toContentLocale(v.locale) === l.value),
  );
  const isSource = current === sourceLocale;

  const goVariant = (v: Variant) => {
    router.push(`${basePath}/${v.id}/edit`);
  };

  const variantState = (locale: string) => {
    const row = allRows.find((item) => toContentLocale(item.locale) === locale);
    if (!row) return "missing" as const;
    if (row.status === "draft") return "draft" as const;
    if (
      sourceRow?.updated_at
      && row.updated_at
      && (row.status === "published" || row.status === "active")
      && (sourceRow.status === "published" || sourceRow.status === "active")
      && new Date(sourceRow.updated_at).getTime() > new Date(row.updated_at).getTime()
    ) {
      return "stale" as const;
    }
    return "ready" as const;
  };

  const handleDraft = async (target: string) => {
    if (!canDraft || !isSource) return;
    setDrafting(true);
    setMessage(null);
    try {
      const result = await localeDraftApi.create(token, entityPath, id, target);
      setMessage("已產生草稿，尚未出現在公開網站。請開啟該語系、看過後再上架。");
      if (result.target_id) {
        router.push(`${basePath}/${result.target_id}/edit`);
      } else {
        await loadVariants();
      }
    } catch (error) {
      if (error instanceof ApiError && error.targetId) {
        setMessage("客戶語言內容已上架，系統不會覆蓋。正在開啟該語言頁面。");
        router.push(`${basePath}/${error.targetId}/edit`);
      } else {
        setMessage(error instanceof Error ? error.message : "無法產生草稿");
      }
    } finally {
      setDrafting(false);
    }
  };

  return (
    <div className="rounded-md border border-blue-200 bg-blue-50/30 px-4 py-3 space-y-2">
      <p className="text-xs font-medium text-blue-800">語言版本</p>
      <p className="text-xs text-blue-900/80 leading-relaxed">
        用{localeLabel(sourceLocale)}維護正本。客戶語言內容會先產生草稿，確認後再上架才會出現在對應語言的官網。
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="bg-blue-700 text-white hover:bg-blue-800">
          {localeLabel(current)} ● 目前版本
        </Badge>
        {variants.map((v) => {
          const state = variantState(toContentLocale(v.locale));
          return (
            <button key={v.id} type="button" onClick={() => goVariant(v)}>
              <Badge
                variant="outline"
                className={
                  state === "stale"
                    ? "cursor-pointer border-amber-500 text-amber-800 hover:bg-amber-50"
                    : state === "draft"
                      ? "cursor-pointer border-slate-400 text-slate-700 hover:bg-slate-50"
                      : "cursor-pointer border-green-500 text-green-700 hover:bg-green-50"
                }
              >
                {localeLabel(v.locale)}
                {state === "stale" ? " · 需更新" : state === "draft" ? " · 草稿未上架" : " ✓"}
              </Badge>
            </button>
          );
        })}
        {missing.map((l) => (
          <span key={l.value} className="inline-flex items-center gap-1">
            {canDraft && isSource ? (
              <button type="button" disabled={drafting} onClick={() => void handleDraft(l.value)}>
                <Badge
                  variant="outline"
                  className="cursor-pointer border-dashed border-blue-400 text-blue-700 hover:bg-blue-50"
                >
                  {drafting ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
                  依{localeLabel(sourceLocale)}產{l.label}草稿
                </Badge>
              </button>
            ) : (
              <button
                type="button"
                onClick={() =>
                  router.push(
                    `${basePath}/new?${pairField}=${encodeURIComponent(slug)}&locale=${l.value}`,
                  )
                }
              >
                <Badge
                  variant="outline"
                  className="cursor-pointer border-dashed text-muted-foreground hover:border-blue-400 hover:text-blue-600"
                >
                  + {l.label}
                </Badge>
              </button>
            )}
          </span>
        ))}
        {canDraft && isSource && SUPPORTED_LOCALES.filter(
          (locale) => locale.value !== sourceLocale && variantState(locale.value) === "draft",
        ).map((locale) => (
          <button key={`redraft-${locale.value}`} type="button" disabled={drafting} onClick={() => void handleDraft(locale.value)}>
            <Badge variant="outline" className="cursor-pointer border-dashed border-blue-400 text-blue-700">
              {drafting ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
              重新產{locale.label}草稿
            </Badge>
          </button>
        ))}
      </div>
      {message && <p className="text-xs text-blue-900">{message}</p>}
    </div>
  );
}
