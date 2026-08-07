"use client";
/**
 * LocaleSwitcher — locale-variant bar for content edit forms.
 *
 * English is the source of truth: saving EN auto-syncs zh-tw (Professional).
 * Switching variants uses in-app navigation (same form route family).
 * Manual edits on zh-tw are lock-protected from later auto-sync.
 */
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { translateApi } from "@/lib/api/content";
import { SUPPORTED_LOCALES, localeLabel, draftKey, saveDraft, toContentLocale } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";

type Variant = { id: string; locale: string };

type Props = {
  entityType: string;
  /** e.g. "/dashboard/products" — used to build edit/new links */
  basePath: string;
  /** Current entity id (edit mode). The whole bar is hidden without it. */
  id?: string;
  slug: string;
  currentLocale: string;
  variants: Variant[];
  /** Called when selecting an existing variant — defaults to soft navigate to edit */
  onSelectVariant?: (variant: Variant) => void;
};

export function LocaleSwitcher({
  entityType,
  basePath,
  id,
  slug,
  currentLocale,
  variants,
  onSelectVariant,
}: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [drafting, setDrafting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!id || !slug) return null;

  const current = toContentLocale(currentLocale);
  const missing = SUPPORTED_LOCALES.filter(
    (l) => l.value !== current && !variants.some((v) => toContentLocale(v.locale) === l.value),
  );

  const goVariant = (v: Variant) => {
    if (onSelectVariant) {
      onSelectVariant(v);
      return;
    }
    router.push(`${basePath}/${v.id}/edit`);
  };

  const handleDraft = async (targetLocale: string) => {
    setDrafting(targetLocale);
    setError(null);
    try {
      const res = await translateApi.draft(token, {
        entity_type: entityType,
        source_id: id,
        target_locale: targetLocale,
      });
      saveDraft(draftKey(entityType, slug, targetLocale), res.fields);
      router.push(
        `${basePath}/new?slug=${encodeURIComponent(slug)}&locale=${targetLocale}&draft=1`,
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "AI 起草失敗，請稍後再試或手動建立");
      setDrafting(null);
    }
  };

  return (
    <div className="rounded-md border border-blue-200 bg-blue-50/30 px-4 py-3 space-y-2">
      <p className="text-xs font-medium text-blue-800">語言版本</p>
      <p className="text-xs text-blue-900/80 leading-relaxed">
        以英文為準：儲存英文後會自動更新繁中並上線（Professional）。你手動改過的繁中欄位不會被覆蓋。
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="bg-blue-700 text-white hover:bg-blue-800">
          {localeLabel(current)} ● 目前版本
        </Badge>
        {variants.map((v) => (
          <button key={v.id} type="button" onClick={() => goVariant(v)}>
            <Badge
              variant="outline"
              className="cursor-pointer border-green-500 text-green-700 hover:bg-green-50"
            >
              {localeLabel(v.locale)} ✓
            </Badge>
          </button>
        ))}
        {missing.map((l) => (
          <span key={l.value} className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() =>
                router.push(
                  `${basePath}/new?slug=${encodeURIComponent(slug)}&locale=${l.value}`,
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
            {current === "en" && (
              <button
                type="button"
                onClick={() => void handleDraft(l.value)}
                disabled={drafting !== null}
                className="inline-flex items-center gap-1 rounded-full border border-violet-300 bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700 hover:bg-violet-100 disabled:opacity-50"
                title={`手動 AI 起草${l.label}（通常存英文會自動同步）`}
              >
                {drafting === l.value ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Sparkles className="h-3 w-3" />
                )}
                {drafting === l.value ? "起草中…" : "AI 起草"}
              </button>
            )}
          </span>
        ))}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
