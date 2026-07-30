import { Navigate, Outlet, useLocation } from "react-router-dom";

import { Spinner } from "@/components/ui/spinner";
import { useAuthStore } from "@/store/authStore";

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

/**
 * Gates the wrapped route tree behind authentication. Renders a full-page
 * spinner while auth status is still being determined ("idle"/"loading" —
 * e.g. the silent boot-time refresh hasn't resolved yet), redirects to
 * `/login` (preserving the attempted location) once we know for certain the
 * visitor is unauthenticated, and otherwise renders the nested routes.
 */
export function ProtectedRoute() {
  const status = useAuthStore((s) => s.status);
  const location = useLocation();

  if (status === "idle" || status === "loading") {
    return <FullPageSpinner />;
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
