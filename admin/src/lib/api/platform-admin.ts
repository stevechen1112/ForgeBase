// Platform Admin API — superuser only
import { apiClient } from "./client";

export type PlatformDashboard = {
  total_tenants: number;
  active_tenants: number;
  total_users: number;
  active_users: number;
  total_products: number;
  total_rfqs: number;
  total_visitors: number;
  daily_rfqs: { date: string; count: number }[];
  top_tenants: { name: string; rfq_count: number }[];
};

export type TenantSummary = {
  id: string;
  name: string;
  slug: string;
  plan: string;
  is_active: boolean;
  created_at: string;
  user_count: number;
  product_count: number;
  rfq_count: number;
  visitor_count: number;
  paypal_subscription_id?: string;
};

export type TenantDetail = TenantSummary & {
  max_products?: number;
  max_admins?: number;
  paypal_payer_email?: string;
  users: { id: string; email: string; full_name: string; role: string; is_active: boolean }[];
  recent_rfqs: { id: string; contact_name: string; contact_email: string; status: string; submitted_at?: string }[];
};

export type AdminUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
  tenant_id?: string;
  tenant_name?: string;
  created_at?: string;
  last_login_at?: string;
};

export type SystemHealth = {
  status: string;
  database: string;
  uptime_seconds: number;
  python_version: string;
};

export type TenantUpdate = {
  plan?: string;
  is_active?: boolean;
  max_products?: number;
  max_admins?: number;
};

export const platformAdminApi = {
  dashboard: (token: string) =>
    apiClient.get<PlatformDashboard>("/admin/dashboard", token),

  tenants: (token: string, params?: { search?: string; is_active?: boolean; skip?: number; limit?: number }) => {
    const qs = params
      ? "?" + new URLSearchParams(
          Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]))
        ).toString()
      : "";
    return apiClient.get<TenantSummary[]>(`/admin/tenants${qs}`, token);
  },

  tenant: (token: string, id: string) =>
    apiClient.get<TenantDetail>(`/admin/tenants/${id}`, token),

  updateTenant: (token: string, id: string, body: TenantUpdate) =>
    apiClient.put<TenantSummary>(`/admin/tenants/${id}`, body, token),

  users: (token: string, params?: { search?: string; tenant_id?: string; skip?: number; limit?: number }) => {
    const qs = params
      ? "?" + new URLSearchParams(
          Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]))
        ).toString()
      : "";
    return apiClient.get<AdminUser[]>(`/admin/users${qs}`, token);
  },

  systemHealth: (token: string) =>
    apiClient.get<SystemHealth>("/admin/system/health", token),
};
