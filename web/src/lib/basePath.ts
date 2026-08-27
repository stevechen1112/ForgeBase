const configuredBasePath = process.env.NEXT_PUBLIC_BASE_PATH?.trim();

export const basePath = configuredBasePath && configuredBasePath !== "/"
  ? `/${configuredBasePath.replace(/^\/+|\/+$/g, "")}`
  : "";

/** Prefix root-relative URLs used by native anchors and image elements. */
export function withBasePath(url: string): string {
  if (!basePath || !url.startsWith("/") || url === basePath || url.startsWith(`${basePath}/`)) {
    return url;
  }

  return `${basePath}${url}`;
}
