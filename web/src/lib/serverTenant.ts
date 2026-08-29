import "server-only";

import { headers } from "next/headers";
import { getTenantIdentifier } from "@/lib/tenant";

const INTERNAL_HOST_HEADER = "X-ForgeBase-Tenant-Host";
const INTERNAL_SECRET_HEADER = "X-ForgeBase-Routing-Secret";

function normalizeHost(value?: string | null): string | null {
  const candidate = value?.split(",", 1)[0]?.trim();
  if (!candidate) return null;

  try {
    const hostname = new URL(`https://${candidate}`).hostname.toLowerCase();
    if (!hostname || hostname === "localhost" || !hostname.includes(".")) return null;
    return hostname;
  } catch {
    return null;
  }
}

export function withServerTenantHost(headersInit?: HeadersInit, host?: string | null): Headers {
  const nextHeaders = new Headers(headersInit);
  const normalizedHost = normalizeHost(host);
  const routingSecret = process.env.TENANT_ROUTING_SECRET?.trim();

  if (normalizedHost && routingSecret) {
    nextHeaders.set(INTERNAL_HOST_HEADER, normalizedHost);
    nextHeaders.set(INTERNAL_SECRET_HEADER, routingSecret);
    return nextHeaders;
  }

  // Temporary rollout bridge for the existing per-tenant images. This path is
  // removed when PUBLIC_TENANT_HEADER_COMPATIBILITY_ENABLED is disabled.
  const tenantIdentifier = getTenantIdentifier();
  if (tenantIdentifier) nextHeaders.set("X-Tenant-ID", tenantIdentifier);
  return nextHeaders;
}

export async function getRequestTenantHost(): Promise<string | null> {
  const requestHeaders = await headers();
  return normalizeHost(requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host"));
}

export async function withRequestTenantHeaders(headersInit?: HeadersInit): Promise<{
  headers: Headers;
  host: string | null;
}> {
  const host = await getRequestTenantHost();
  return { headers: withServerTenantHost(headersInit, host), host };
}

export function tenantCacheTag(host: string | null): string {
  return `tenant:${normalizeHost(host) ?? "legacy-build"}`;
}
