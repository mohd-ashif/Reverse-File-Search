import { Outlet } from "react-router-dom";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Topbar } from "@/components/layout/Topbar";

export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Topbar />

      <main className="container flex min-h-0 flex-1 flex-col py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
