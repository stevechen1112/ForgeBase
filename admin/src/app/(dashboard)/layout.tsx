import { RouteGuard } from "@/components/auth/RouteGuard";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { PlanProvider } from "@/lib/hooks/usePlan";
import { CopilotFloatingWidget } from "@/components/copilot/CopilotFloatingWidget";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RouteGuard>
      <PlanProvider>
        <DashboardShell>{children}</DashboardShell>
        <CopilotFloatingWidget />
      </PlanProvider>
    </RouteGuard>
  );
}
