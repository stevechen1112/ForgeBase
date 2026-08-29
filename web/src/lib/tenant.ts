export function getTenantIdentifier(): string | null {
  const value = process.env.NEXT_PUBLIC_TENANT_ID || process.env.NEXT_PUBLIC_TENANT_SLUG;
  const normalized = value?.trim();
  return normalized ? normalized : null;
}
