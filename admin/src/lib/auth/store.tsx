"use client";
/**
 * Auth store — 儲存 token 與使用者資訊於 localStorage + React Context。
 * 使用 Context + useReducer，無外部狀態管理函式庫依賴。
 */
import { createContext, useContext, useReducer, useEffect, ReactNode } from "react";
import type { UserRead, TokenResponse } from "@/lib/api/auth";

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

const STORAGE_KEY = "fb_auth";

// ── Provider ─────────────────────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { status: "loading" });

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const stored = raw ? (JSON.parse(raw) as TokenResponse) : null;
      dispatch({ type: "HYDRATED", payload: stored });
    } catch {
      dispatch({ type: "HYDRATED", payload: null });
    }
  }, []);

  // Global 401 handler — any API call with expired token triggers logout
  useEffect(() => {
    const handleUnauthorized = () => {
      localStorage.removeItem(STORAGE_KEY);
      dispatch({ type: "LOGOUT" });
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, []);

  const login = (tokenResponse: TokenResponse) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tokenResponse));
    dispatch({ type: "SET_AUTH", payload: tokenResponse });
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
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
