import { RouteGuard } from "@/components/auth/RouteGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { PlanProvider } from "@/lib/hooks/usePlan";
import { CopilotFloatingWidget } from "@/components/copilot/CopilotFloatingWidget";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RouteGuard>
      <PlanProvider>
        <div className="flex h-screen overflow-hidden bg-background">
          <Sidebar />
          <main className="flex-1 overflow-y-auto bg-muted/30 p-6">{children}</main>
        </div>
        <CopilotFloatingWidget />
      </PlanProvider>
    </RouteGuard>
  );
}
