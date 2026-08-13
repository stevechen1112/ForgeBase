"use client";
/**
 * LocaleSwitcher — locale-variant bar for content edit forms.
 *
 * Locale variants are maintained manually. Switching variants uses in-app
 * navigation within the same form route family.
 */
import { useRouter } from "next/navigation";
import { SUPPORTED_LOCALES, localeLabel, toContentLocale } from "@/lib/i18n";
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
  basePath,
  id,
  slug,
  currentLocale,
  variants,
  onSelectVariant,
}: Props) {
  const router = useRouter();
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

  return (
    <div className="rounded-md border border-blue-200 bg-blue-50/30 px-4 py-3 space-y-2">
      <p className="text-xs font-medium text-blue-800">語言版本</p>
      <p className="text-xs text-blue-900/80 leading-relaxed">各語言版本皆由內容團隊人工建立、審核與發布。</p>
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
          </span>
        ))}
      </div>
    </div>
  );
}
