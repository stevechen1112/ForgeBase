"use client";
/**
 * Auth store — 儲存 token 與使用者資訊於 localStorage + React Context。
 * 使用 Context + useReducer，無外部狀態管理函式庫依賴。
 */
import { createContext, useContext, useReducer, useEffect, ReactNode } from "react";
import type { UserRead, TokenResponse } from "@/lib/api/auth";
import { clearAuthStorage, readAuthStorage, writeAuthStorage } from "@/lib/auth/storage";

function isTenantSession(payload: TokenResponse | null): payload is TokenResponse {
  return Boolean(payload?.user?.tenant_id && !payload.user.is_superuser);
}

// ── Types ────────────────────────────────────────────────────────────────────
type AuthState =
  | { status: "loading" }
  | { status: "unauthenticated" }
  | { status: "authenticated"; user: UserRead; accessToken: string; refreshToken: string };

type AuthAction =
  | { type: "SET_AUTH"; payload: TokenResponse }
  | { type: "LOGOUT" }
  | { type: "HYDRATED"; payload: TokenResponse | null };

// ── Reducer ──────────────────────────────────────────────────────────────────
function reducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "SET_AUTH":
      return {
        status: "authenticated",
        user: action.payload.user,
        accessToken: action.payload.access_token,
        refreshToken: action.payload.refresh_token,
      };
    case "LOGOUT":
      return { status: "unauthenticated" };
    case "HYDRATED":
      if (!action.payload) return { status: "unauthenticated" };
      return {
        status: "authenticated",
        user: action.payload.user,
        accessToken: action.payload.access_token,
        refreshToken: action.payload.refresh_token,
      };
    default:
      return state;
  }
}

// ── Context ──────────────────────────────────────────────────────────────────
type AuthContextValue = {
  state: AuthState;
  login: (tokenResponse: TokenResponse) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ─────────────────────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { status: "loading" });

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const raw = readAuthStorage();
      const stored = raw ? (JSON.parse(raw) as TokenResponse) : null;
      if (!isTenantSession(stored)) {
        clearAuthStorage();
        dispatch({ type: "HYDRATED", payload: null });
        return;
      }
      dispatch({ type: "HYDRATED", payload: stored });
    } catch {
      dispatch({ type: "HYDRATED", payload: null });
    }
  }, []);

  // Global 401 handler — any API call with expired token triggers logout
  useEffect(() => {
    const handleUnauthorized = () => {
      clearAuthStorage();
      dispatch({ type: "LOGOUT" });
    };
    const handleRefreshed = (e: Event) => {
      const detail = (e as CustomEvent<TokenResponse>).detail;
      if (isTenantSession(detail)) {
        dispatch({ type: "SET_AUTH", payload: detail });
      } else {
        clearAuthStorage();
        dispatch({ type: "LOGOUT" });
      }
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    window.addEventListener("auth:refreshed", handleRefreshed);
    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
      window.removeEventListener("auth:refreshed", handleRefreshed);
    };
  }, []);

  const login = (tokenResponse: TokenResponse) => {
    if (!isTenantSession(tokenResponse)) {
      clearAuthStorage();
      throw new Error("此帳號不是租戶後台帳號");
    }
    writeAuthStorage(JSON.stringify(tokenResponse));
    dispatch({ type: "SET_AUTH", payload: tokenResponse });
  };

  const logout = () => {
    clearAuthStorage();
    dispatch({ type: "LOGOUT" });
  };

  return (
    <AuthContext.Provider value={{ state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
