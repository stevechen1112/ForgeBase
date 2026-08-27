export function shouldFetchEnglishListFallback(locale: string, page: number): boolean {
  return locale !== "en" && page <= 1;
}

export function parseListPage(path: string): number {
  const queryIndex = path.indexOf("?");
  if (queryIndex < 0) return 1;
  const page = Number(new URLSearchParams(path.slice(queryIndex + 1)).get("page") || "1");
  return Number.isFinite(page) && page > 0 ? page : 1;
}

export function withLocaleQuery(path: string, locale: string): string {
  const queryIndex = path.indexOf("?");
  const base = queryIndex < 0 ? path : path.slice(0, queryIndex);
  const params = new URLSearchParams(queryIndex < 0 ? "" : path.slice(queryIndex + 1));
  params.set("locale", locale);
  return `${base}?${params.toString()}`;
}

function itemSlug(item: unknown): string {
  if (!item || typeof item !== "object" || !("slug" in item)) return "";
  const slug = (item as { slug?: unknown }).slug;
  return typeof slug === "string" ? slug.trim() : "";
}

/** English catalog order is the base; the current locale overlays by slug. Items without a slug are not taken from English. */
export function mergePublishedListBySlug<T>(localized: T[], english: T[]): T[] {
  const localizedBySlug = new Map<string, T>();
  for (const item of localized) {
    const slug = itemSlug(item);
    if (slug) localizedBySlug.set(slug, item);
  }

  const used = new Set<string>();
  const merged: T[] = [];
  for (const item of english) {
    const slug = itemSlug(item);
    if (!slug) continue;
    used.add(slug);
    merged.push(localizedBySlug.get(slug) ?? item);
  }

  for (const item of localized) {
    const slug = itemSlug(item);
    if (!slug) {
      merged.push(item);
      continue;
    }
    if (!used.has(slug)) merged.push(item);
  }

  return merged;
}
