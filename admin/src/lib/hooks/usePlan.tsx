"use client";
/**
 * Plan feature flag context.
 *
 * Wraps the dashboard layout so any child component can call usePlan()
 * to check whether the current tenant's plan includes a given feature.
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
import { subscriptionApi, type CurrentPlanResponse } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/store";

// ── Types ────────────────────────────────────────────────────────────────────
type PlanState =
  | { status: "loading" }
  | { status: "ready"; data: CurrentPlanResponse }
  | { status: "error" };

type PlanContextValue = {
  isLoading: boolean;
  plan: string;
  features: Record<string, boolean>;
  hasFeature: (key: string) => boolean;
  refresh: () => void;
};

// ── Context ──────────────────────────────────────────────────────────────────
const PlanContext = createContext<PlanContextValue | null>(null);

// ── Provider ─────────────────────────────────────────────────────────────────
export function PlanProvider({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  const [planState, setPlanState] = useState<PlanState>({ status: "loading" });
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (state.status !== "authenticated") {
      setPlanState({ status: "loading" });
      return;
    }
    let cancelled = false;
    const token = state.accessToken;

    subscriptionApi
      .getCurrent(token)
      .then((data) => {
        if (!cancelled) setPlanState({ status: "ready", data });
      })
      .catch(() => {
        if (!cancelled) setPlanState({ status: "error" });
      });

    return () => {
      cancelled = true;
    };
  // refreshKey allows manual cache invalidation after plan upgrade
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.status, refreshKey]);

  const hasFeature = (key: string): boolean => {
    // While loading, return true (optimistic) to avoid flickering locked walls.
    // If loading failed, fail closed so UI remains aligned with backend enforcement.
    if (planState.status === "loading") return true;
    if (planState.status !== "ready") return false;
    return planState.data.features[key] ?? false;
  };

  const value: PlanContextValue = {
    isLoading: planState.status === "loading",
    plan: planState.status === "ready" ? planState.data.plan : "starter",
    features: planState.status === "ready" ? planState.data.features : {},
    hasFeature,
    refresh: () => setRefreshKey((k) => k + 1),
  };

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function usePlan(): PlanContextValue {
  const ctx = useContext(PlanContext);
  if (!ctx) throw new Error("usePlan must be used within PlanProvider");
  return ctx;
}
