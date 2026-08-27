"use client";
import { CapabilityGate } from "@/components/capabilities/CapabilityGate";

export default function Layout({ children }: { children: React.ReactNode }) {
  return <CapabilityGate feature="audience_segments">{children}</CapabilityGate>;
}
