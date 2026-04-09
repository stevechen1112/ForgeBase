import { apiClient } from "./client";

export type LoginRequest = {
  email: string;
  password: string;
};

export type UserRead = {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "owner" | "marketing_manager" | "sales";
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  tenant_id?: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserRead;
};

export type TeamMember = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  tenant_id?: string;
};

export type InviteRequest = {
  email: string;
  full_name: string;
  password: string;
  role: string;
};

export type CheckoutResult = {
  subscription_id: string;
  approve_url: string;
};

export type CurrentPlanResponse = {
  plan: string;
  display_name: string;
  features: Record<string, boolean>;
  limits: {
    max_products: number | null;
    max_admins: number | null;
  };
  usage: {
    products: number;
    admins: number;
  };
};

export const authApi = {
  login: (payload: LoginRequest) =>
    apiClient.post<TokenResponse>("/auth/login", payload),

  refresh: (refreshToken: string) =>
    apiClient.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken }),

  listTeam: (token: string) =>
    apiClient.get<TeamMember[]>("/auth/team", token),

  inviteTeamMember: (payload: InviteRequest, token: string) =>
    apiClient.post<TeamMember>("/auth/team/invite", payload, token),

  updateTeamMember: (userId: string, payload: { role?: string; is_active?: boolean }, token: string) =>
    apiClient.patch<TeamMember>(`/auth/team/${userId}`, payload, token),
};

export const subscriptionApi = {
  getPlans: (token: string) =>
    apiClient.get<Record<string, unknown>[]>("/subscription/plans", token),

  getCurrent: (token: string) =>
    apiClient.get<CurrentPlanResponse>("/subscription/current", token),

  checkout: (plan: string, token: string) =>
    apiClient.post<CheckoutResult>("/subscription/checkout", { plan }, token),

  cancel: (token: string) =>
    apiClient.post<{ status: string }>("/subscription/cancel", {}, token),
};
