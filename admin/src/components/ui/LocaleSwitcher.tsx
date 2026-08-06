"use client";
/**
 * LocaleSwitcher — shared locale-variant bar for content edit forms.
 *
 * Shows the current locale, links to existing variants, and for missing
 * locales offers:
 *   1. "+ <locale>" — open a blank create form for that locale
 *   2. "AI 起草" — call POST /content/translate-draft on the current entity,
 *      stash the draft in sessionStorage, then open the create form which
 *      prefills from it. Human reviews and saves; nothing is auto-published.
 */
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { translateApi } from "@/lib/api/content";
import { SUPPORTED_LOCALES, localeLabel, draftKey, saveDraft } from "@/lib/i18n";
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
  /** basePath prefix — admin lives under /backend */
  hrefPrefix?: string;
};

export function LocaleSwitcher({
  entityType,
  basePath,
  id,
  slug,
  currentLocale,
  variants,
  hrefPrefix = "/backend",
}: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [drafting, setDrafting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!id || !slug) return null;

  const missing = SUPPORTED_LOCALES.filter(
    (l) => l.value !== currentLocale && !variants.some((v) => v.locale === l.value),
  );

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
      // router.push 會自動加 next.config 的 basePath(/backend)，不能再帶前綴
      router.push(
        `${basePath}/new?slug=${encodeURIComponent(slug)}&locale=${targetLocale}&draft=1`,
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "AI 起草失敗，請稍後再試或手動建立");
      setDrafting(null);
    }
  };

  return (
    <div className="rounded-md border border-blue-200 bg-blue-50/30 px-4 py-3">
      <p className="mb-2 text-xs font-medium text-blue-800">語言版本（英／繁人工維護，AI 起草後人工確認）</p>
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="bg-blue-700 text-white hover:bg-blue-800">
          {localeLabel(currentLocale)} ● 目前版本
        </Badge>
        {variants.map((v) => (
          <a key={v.id} href={`${hrefPrefix}${basePath}/${v.id}/edit`}>
            <Badge
              variant="outline"
              className="cursor-pointer border-green-500 text-green-700 hover:bg-green-50"
            >
              {localeLabel(v.locale)} ✓
            </Badge>
          </a>
        ))}
        {missing.map((l) => (
          <span key={l.value} className="inline-flex items-center gap-1">
            <a href={`${hrefPrefix}${basePath}/new?slug=${encodeURIComponent(slug)}&locale=${l.value}`}>
              <Badge
                variant="outline"
                className="cursor-pointer border-dashed text-muted-foreground hover:border-blue-400 hover:text-blue-600"
              >
                + {l.label}
              </Badge>
            </a>
            <button
              type="button"
              onClick={() => void handleDraft(l.value)}
              disabled={drafting !== null}
              className="inline-flex items-center gap-1 rounded-full border border-violet-300 bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700 hover:bg-violet-100 disabled:opacity-50"
              title={`用 AI 將目前版本翻譯成${l.label}草稿，人工確認後儲存`}
            >
              {drafting === l.value ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Sparkles className="h-3 w-3" />
              )}
              {drafting === l.value ? "起草中…" : "AI 起草"}
            </button>
          </span>
        ))}
      </div>
      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </div>
  );
}
