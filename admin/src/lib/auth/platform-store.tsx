"use client";
/**
 * Platform Admin Auth — completely independent from tenant auth.
 * Uses a separate storage key and only allows superuser accounts.
 */
import { createContext, useContext, useReducer, useEffect, type ReactNode } from "react";
import type { UserRead, TokenResponse } from "@/lib/api/auth";
import {
  clearPlatformAuthStorage,
  readPlatformAuthStorage,
  writePlatformAuthStorage,
} from "@/lib/auth/platform-storage";

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
function reducer(_state: AuthState, action: AuthAction): AuthState {
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
      return _state;
  }
}

// ── Context ──────────────────────────────────────────────────────────────────
type PlatformAuthContextValue = {
  state: AuthState;
  login: (tokenResponse: TokenResponse) => void;
  logout: () => void;
};

const PlatformAuthContext = createContext<PlatformAuthContextValue | null>(null);

// ── Provider ─────────────────────────────────────────────────────────────────
export function PlatformAuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { status: "loading" });

  // Hydrate from sessionStorage on mount
  useEffect(() => {
    try {
      const raw = readPlatformAuthStorage();
      const stored = raw ? (JSON.parse(raw) as TokenResponse) : null;
      // Only hydrate if the user is actually a superuser
      if (stored?.user && !stored.user.is_superuser) {
        clearPlatformAuthStorage();
        dispatch({ type: "HYDRATED", payload: null });
      } else {
        dispatch({ type: "HYDRATED", payload: stored });
      }
    } catch {
      dispatch({ type: "HYDRATED", payload: null });
    }
  }, []);

  const login = (tokenResponse: TokenResponse) => {
    // Only allow superusers
    if (!tokenResponse.user?.is_superuser) {
      throw new Error("此帳號不具備平台管理員權限");
    }
    writePlatformAuthStorage(JSON.stringify(tokenResponse));
    dispatch({ type: "SET_AUTH", payload: tokenResponse });
  };

  const logout = () => {
    clearPlatformAuthStorage();
    dispatch({ type: "LOGOUT" });
  };

  return (
    <PlatformAuthContext.Provider value={{ state, login, logout }}>
      {children}
    </PlatformAuthContext.Provider>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function usePlatformAuth() {
  const ctx = useContext(PlatformAuthContext);
  if (!ctx) throw new Error("usePlatformAuth must be used within PlatformAuthProvider");
  return ctx;
}
