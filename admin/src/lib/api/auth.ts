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
  is_superuser?: boolean;
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

export type RegisterRequest = {
  email: string;
  password: string;
  full_name: string;
  company_name: string;
  registration_key?: string;
};

export type RegisterResponse = TokenResponse & {
  tenant_id: string;
  tenant_slug: string;
};

export type CapabilityAccessResponse = {
  product: "forgebase";
  features: Record<string, boolean>;
};

export const authApi = {
  register: (payload: RegisterRequest) =>
    apiClient.post<RegisterResponse>("/auth/register", payload),

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

export const capabilityApi = {
  getCurrent: (token: string) =>
    apiClient.get<CapabilityAccessResponse>("/capabilities/access", token),
};
