"use client";
/**
 * AiDraftButton — one-click LLM locale draft for entities without a slug
 * (FAQ etc.) where locale variants can't be grouped by slug.
 *
 * Calls POST /content/translate-draft for the current entity, stashes the
 * draft in sessionStorage, then navigates to the create form which prefills.
 */
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { translateApi } from "@/lib/api/content";
import { localeLabel, draftKey, saveDraft } from "@/lib/i18n";

type Props = {
  entityType: string;
  /** Current entity id (edit mode). */
  id: string;
  /** Unique grouping key for the draft handoff (slug or entity id). */
  draftGroup: string;
  targetLocale: string;
  /** e.g. "/dashboard/faqs/new" */
  newHref: string;
  extraQuery?: Record<string, string>;
};

export function AiDraftButton({ entityType, id, draftGroup, targetLocale, newHref, extraQuery }: Props) {
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [drafting, setDrafting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDraft = async () => {
    setDrafting(true);
    setError(null);
    try {
      const res = await translateApi.draft(token, {
        entity_type: entityType,
        source_id: id,
        target_locale: targetLocale,
      });
      saveDraft(draftKey(entityType, draftGroup, targetLocale), res.fields);
      // router.push 會自動加 next.config 的 basePath(/backend)，不能再帶前綴
      const qs = new URLSearchParams({ locale: targetLocale, draft: "1", ...(extraQuery ?? {}) });
      router.push(`${newHref}?${qs.toString()}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "AI 起草失敗，請稍後再試或手動建立");
      setDrafting(false);
    }
  };

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={() => void handleDraft()}
        disabled={drafting}
        className="inline-flex items-center gap-1.5 rounded-md border border-violet-300 bg-violet-50 px-3 py-1.5 text-sm font-medium text-violet-700 hover:bg-violet-100 disabled:opacity-50"
        title={`用 AI 將目前內容翻譯成${localeLabel(targetLocale)}草稿，人工確認後儲存`}
      >
        {drafting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        {drafting ? "AI 起草中…" : `AI 起草${localeLabel(targetLocale)}版`}
      </button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </span>
  );
}
