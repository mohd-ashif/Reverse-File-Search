import type { ReactNode } from "react";

import { usePermissionStore } from "@/store/permissionStore";
import type { Permission } from "@/types/permission";

interface PermissionGuardProps {
  permission: Permission;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Renders `children` only if the current user's permission set (loaded at
 * login/refresh/boot time into `permissionStore`) includes `permission`.
 * Otherwise renders `fallback` (defaults to nothing).
 *
 * Usage: <PermissionGuard permission="folder.create"><Button>Add Folder</Button></PermissionGuard>
 */
export function PermissionGuard({ permission, children, fallback = null }: PermissionGuardProps) {
  const hasPermission = usePermissionStore((s) => s.permissions.includes(permission));
  return <>{hasPermission ? children : fallback}</>;
}
