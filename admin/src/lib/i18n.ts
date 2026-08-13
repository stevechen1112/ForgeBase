/**
 * Shared locale constants + draft handoff helpers for content forms.
 */

export const SOURCE_LOCALE = "en";

export const SUPPORTED_LOCALES = [
  { value: "en", label: "English" },
  { value: "zh-tw", label: "繁體中文" },
] as const;

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]["value"];

/** Normalize UI / route tags to CMS canonical locale (zh-TW → zh-tw). */
export function toContentLocale(raw: string | null | undefined, fallback: SupportedLocale = "en"): string {
  if (!raw) return fallback;
  const key = raw.trim();
  if (key === "en") return "en";
  const lowered = key.toLowerCase().replace(/_/g, "-");
  if (lowered === "zh-tw") return "zh-tw";
  if (lowered === "en") return "en";
  return fallback;
}

export function localeLabel(value: string): string {
  const canonical = toContentLocale(value, value as SupportedLocale);
  return SUPPORTED_LOCALES.find((l) => l.value === canonical)?.label ?? value;
}

/** Legacy sessionStorage key retained only for harmless manual form-prefill compatibility. */
export function draftKey(entityType: string, slug: string, locale: string): string {
  return `content-prefill:${entityType}:${slug}:${locale}`;
}

export function saveDraft(key: string, fields: Record<string, string>): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(fields));
  } catch { /* storage full / unavailable — form just opens empty */ }
}

export function takeDraft(key: string): Record<string, string> | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    sessionStorage.removeItem(key);
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? (parsed as Record<string, string>) : null;
  } catch {
    return null;
  }
}
