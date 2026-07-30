import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import { Spinner } from "@/components/ui/spinner";
import { useBootstrapAuth } from "@/hooks/useAuth";
import { useOrganizations } from "@/hooks/useOrganizations";
import { useAuthStore } from "@/store/authStore";
import { useOrganizationStore } from "@/store/organizationStore";

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

/**
 * Wraps the entire route tree. Fires the once-per-app-load silent
 * `/auth/refresh` bootstrap (see `useBootstrapAuth`) and shows a full-page
 * spinner until that resolves, so unauthenticated/authenticated status is
 * known BEFORE any route (public or protected) renders — this is what
 * prevents a login-page flash for visitors who actually have a valid
 * session cookie.
 */
export function AppBootGate() {
  useBootstrapAuth();
  const status = useAuthStore((s) => s.status);
  const { data: organizations } = useOrganizations();

  useEffect(() => {
    if (organizations) {
      useOrganizationStore.getState().setMemberships(organizations);
    }
  }, [organizations]);

  if (status === "idle" || status === "loading") {
    return <FullPageSpinner />;
  }

  return <Outlet />;
}
