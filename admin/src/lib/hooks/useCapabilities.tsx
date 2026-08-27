"use client";
/**
 * Capability access context for the single ForgeBase product.
 *
 * Wraps the dashboard layout so any child component can call useCapabilities()
 * to check whether a capability is enabled for the current tenant.
 *
 * The data is fetched once when the user is authenticated and cached
 * for the lifetime of the session.
 */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { capabilityApi, type CapabilityAccessResponse } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/store";

// ── Types ────────────────────────────────────────────────────────────────────
type CapabilityState =
  | { status: "loading" }
  | { status: "ready"; data: CapabilityAccessResponse }
  | { status: "error" };

type CapabilityContextValue = {
  isLoading: boolean;
  features: Record<string, boolean>;
  hasFeature: (key: string) => boolean;
  refresh: () => void;
};

// ── Context ──────────────────────────────────────────────────────────────────
const CapabilityContext = createContext<CapabilityContextValue | null>(null);

// ── Provider ─────────────────────────────────────────────────────────────────
export function CapabilityProvider({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  const [capabilityState, setCapabilityState] = useState<CapabilityState>({ status: "loading" });
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (
      state.status !== "authenticated"
      || state.user.is_superuser
      || !state.user.tenant_id
    ) {
      setCapabilityState({ status: "loading" });
      return;
    }
    let cancelled = false;
    const token = state.accessToken;

    capabilityApi
      .getCurrent(token)
      .then((data) => {
        if (!cancelled) setCapabilityState({ status: "ready", data });
      })
      .catch(() => {
        if (!cancelled) setCapabilityState({ status: "error" });
      });

    return () => {
      cancelled = true;
    };
  // refreshKey allows invalidation after an operator changes capability access.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.status, refreshKey]);

  const hasFeature = (key: string): boolean => {
    // While loading, return true (optimistic) to avoid flickering locked walls.
    // If loading failed, fail closed so UI remains aligned with backend enforcement.
    if (capabilityState.status === "loading") return true;
    if (capabilityState.status !== "ready") return false;
    return capabilityState.data.features[key] ?? false;
  };

  const value: CapabilityContextValue = {
    isLoading: capabilityState.status === "loading",
    features: capabilityState.status === "ready" ? capabilityState.data.features : {},
    hasFeature,
    refresh: () => setRefreshKey((k) => k + 1),
  };

  return <CapabilityContext.Provider value={value}>{children}</CapabilityContext.Provider>;
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useCapabilities(): CapabilityContextValue {
  const ctx = useContext(CapabilityContext);
  if (!ctx) throw new Error("useCapabilities must be used within CapabilityProvider");
  return ctx;
}
