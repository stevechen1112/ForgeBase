export function localizedPath(locale: string, path: string): string {
  if (!path.startsWith("/") || path.startsWith("//")) return path;
  if (locale !== "zh-TW") return path;
  if (path === "/zh-TW" || path.startsWith("/zh-TW/")) return path;
  return path === "/" ? "/zh-TW" : `/zh-TW${path}`;
}
