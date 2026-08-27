import { getMessageNamespace } from "@/lib/messages.server";
import { resolveLocale } from "@/lib/siteCopy";

type CommonMessages = {
  localeFallbackTitle: string;
  localeFallbackDescription: string;
};

type LocaleFallbackNoticeProps = {
  locale: string;
  className?: string;
};

function getItemLocale(item: unknown): string | null {
  if (!item || typeof item !== "object" || !("locale" in item)) {
    return null;
  }

  const value = (item as { locale?: unknown }).locale;
  return typeof value === "string" ? value : null;
}

export function hasLocaleFallback(locale: string, items: Array<unknown>): boolean {
  const resolvedLocale = resolveLocale(locale);
  if (resolvedLocale === "en") return false;

  return items.some((item) => {
    const itemLocale = getItemLocale(item);
    return itemLocale ? resolveLocale(itemLocale) !== resolvedLocale : false;
  });
}

export async function LocaleFallbackNotice({ locale, className }: LocaleFallbackNoticeProps) {
  const resolvedLocale = resolveLocale(locale);
  if (resolvedLocale === "en") return null;

  const copy = await getMessageNamespace<CommonMessages>("common");

  return (
    <div className={`rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 ${className ?? ""}`.trim()}>
      <p className="font-semibold">{copy.localeFallbackTitle}</p>
      <p className="mt-1 leading-relaxed text-amber-800">{copy.localeFallbackDescription}</p>
    </div>
  );
}
