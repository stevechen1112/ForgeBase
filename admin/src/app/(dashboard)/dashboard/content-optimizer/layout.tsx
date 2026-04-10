"use client";
import { PlanGate } from "@/components/plan/PlanGate";

export default function Layout({ children }: { children: React.ReactNode }) {
  return <PlanGate feature="ai_content_generation">{children}</PlanGate>;
}
