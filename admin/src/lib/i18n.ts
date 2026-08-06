/**
 * Shared locale constants + draft handoff helpers for content forms.
 */

export const SUPPORTED_LOCALES = [
  { value: "en", label: "English" },
  { value: "zh-tw", label: "繁體中文" },
] as const;

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]["value"];

export function localeLabel(value: string): string {
  return SUPPORTED_LOCALES.find((l) => l.value === value)?.label ?? value;
}

/** sessionStorage key for passing an AI translation draft to a /new form. */
export function draftKey(entityType: string, slug: string, locale: string): string {
  return `translate-draft:${entityType}:${slug}:${locale}`;
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
