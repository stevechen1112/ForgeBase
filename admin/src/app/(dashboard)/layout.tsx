import { RouteGuard } from "@/components/auth/RouteGuard";
import { FeatureAccessGuard } from "@/components/auth/FeatureAccessGuard";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { CapabilityProvider } from "@/lib/hooks/useCapabilities";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RouteGuard>
      <CapabilityProvider>
        <DashboardShell><FeatureAccessGuard>{children}</FeatureAccessGuard></DashboardShell>
      </CapabilityProvider>
    </RouteGuard>
  );
}
