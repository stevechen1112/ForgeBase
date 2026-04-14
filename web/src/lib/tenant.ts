const TENANT_HEADER = "X-Tenant-ID";

export function getTenantIdentifier(): string | null {
  const value = process.env.NEXT_PUBLIC_TENANT_ID || process.env.NEXT_PUBLIC_TENANT_SLUG;
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

export function withTenantHeaders(headers?: HeadersInit): Headers {
  const nextHeaders = new Headers(headers);
  const tenantIdentifier = getTenantIdentifier();
  if (tenantIdentifier) {
    nextHeaders.set(TENANT_HEADER, tenantIdentifier);
  }
  return nextHeaders;
}

export function withTenantHost(headers?: HeadersInit, host?: string | null): Headers {
  const nextHeaders = withTenantHeaders(headers);
  if (host) {
    nextHeaders.set("X-Tenant-Host", host);
  }
  return nextHeaders;
}