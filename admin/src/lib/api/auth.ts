import { apiClient } from "./client";

export type LoginRequest = {
  email: string;
  password: string;
};

export type UserRead = {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "marketing_manager" | "sales";
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserRead;
};

export const authApi = {
  login: (payload: LoginRequest) =>
    apiClient.post<TokenResponse>("/auth/login", payload),

  refresh: (refreshToken: string) =>
    apiClient.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken }),
};
