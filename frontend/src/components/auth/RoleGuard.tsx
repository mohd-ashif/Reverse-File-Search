import type { ReactNode } from "react";

import { useRoleStore } from "@/store/roleStore";

interface RoleGuardProps {
  /** A real role name from the backend's `roles` claim (see app/auth/permissions.py's ROLE_NAMES). */
  role: string;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Gates on the caller's actual role name(s), as returned by the backend in
 * `roles: string[]` on login/refresh/invitation-accept responses (see
 * `TokenResponse` in app/auth/schemas.py) — sourced from the JWT's `roles`
 * claim (`AuthService.get_permissions_and_roles`). Prefer `PermissionGuard`
 * wherever a concrete permission check will do; reach for this only where no
 * single permission cleanly captures the check (e.g. "Organization Admin or
 * higher"-shaped UI).
 */
export function RoleGuard({ role, children, fallback = null }: RoleGuardProps) {
  const hasRole = useRoleStore((s) => s.roles.includes(role));
  return <>{hasRole ? children : fallback}</>;
}
