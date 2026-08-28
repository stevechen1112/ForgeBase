"use client";

import Link from "next/link";
import { ArrowRight, type LucideIcon } from "lucide-react";

import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { useAuth } from "@/lib/auth/store";
import type { UserRead } from "@/lib/api/auth";
import { cn } from "@/lib/utils";

export type WorkspaceItem = {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  feature?: string;
  allowedRoles?: UserRead["role"][];
  accent?: "blue" | "amber" | "emerald" | "violet";
};

export type FlowStep = {
  label: string;
  feature?: string;
};

const accentClasses = {
  blue: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
  amber: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
  emerald: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
  violet: "bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300",
};

export function WorkspaceHub({
  eyebrow,
  title,
  description,
  items,
  flow,
}: {
  eyebrow: string;
  title: string;
  description: string;
  items: WorkspaceItem[];
  flow?: FlowStep[];
}) {
  const { state } = useAuth();
  const { hasFeature, isLoading } = useCapabilities();
  const role = state.status === "authenticated" ? state.user.role : null;
  const visibleItems = items.filter((item) => {
    if (item.allowedRoles && (!role || !item.allowedRoles.includes(role))) return false;
    return !item.feature || (!isLoading && hasFeature(item.feature));
  });

  return (
    <div className="space-y-7">
      <header className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
      </header>

      {flow && (
        <section aria-label="ForgeBase 北極星流程" className="rounded-2xl border bg-card p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-semibold">北極星商機流程</h2>
              <p className="mt-1 text-xs text-muted-foreground">受控中代表能力仍在品質、供應商或法遵 Gate，不代表已識別訪客本人。</p>
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {flow.map((step, index) => {
              const enabled = !step.feature || (!isLoading && hasFeature(step.feature));
              return (
                <div key={step.label} className="flex shrink-0 items-center gap-2">
                  <div className={cn(
                    "min-w-28 rounded-xl border px-3 py-3",
                    enabled ? "border-emerald-200 bg-emerald-50/70 dark:border-emerald-900 dark:bg-emerald-950/20" : "border-amber-200 bg-amber-50/70 dark:border-amber-900 dark:bg-amber-950/20",
                  )}>
                    <p className="text-sm font-medium">{step.label}</p>
                    <p className={cn("mt-1 text-[11px] font-medium", enabled ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300")}>{enabled ? "運作中" : "受控中"}</p>
                  </div>
                  {index < flow.length - 1 && <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground/50" />}
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const accent = item.accent ?? "blue";
          return (
            <Link
              key={item.href}
              href={item.href}
              className="group rounded-2xl border bg-card p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              <div className="flex items-start justify-between gap-4">
                <span className={cn("flex h-10 w-10 items-center justify-center rounded-xl", accentClasses[accent])}>
                  <Icon className="h-5 w-5" />
                </span>
                <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
              </div>
              <h2 className="mt-5 font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.description}</p>
            </Link>
          );
        })}
      </section>
    </div>
  );
}
