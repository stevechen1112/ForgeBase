"use client";
import { PlanGate } from "@/components/plan/PlanGate";

export default function Layout({ children }: { children: React.ReactNode }) {
  return <PlanGate feature="full_tracking">{children}</PlanGate>;
}
