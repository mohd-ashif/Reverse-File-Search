import { usePermissionStore } from "@/store/permissionStore";
import type { Permission } from "@/types/permission";

/**
 * Thin convenience wrapper around `permissionStore`. Trivial one-line hook,
 * added per the original folder-structure spec's `hooks/usePermissions.ts` —
 * existing call sites reading `usePermissionStore` directly (e.g.
 * `PermissionGuard`/`RoleGuard`) are untouched; they can adopt this
 * opportunistically.
 */
export function usePermissions(): Permission[] {
  return usePermissionStore((s) => s.permissions);
}
