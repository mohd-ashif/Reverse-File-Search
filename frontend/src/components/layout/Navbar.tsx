import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";
import { usePermissionStore } from "@/store/permissionStore";
import { NAV_ITEMS, ORGANIZATION_NAV_ITEMS } from "@/components/layout/navItems";

/**
 * Mobile nav: the same permission-gated item list as `Sidebar.tsx`, laid out
 * as a stacked list under the header (replaces the old inline hamburger
 * dropdown in `AppLayout.tsx`). Only rendered when the mobile menu is open;
 * `Topbar` owns the hamburger button and the open/close state.
 */
export function Navbar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  const permissions = usePermissionStore((s) => s.permissions);
  const hasAnyAdminPermission = permissions.some((p) => p.startsWith("admin."));
  const visibleItems = NAV_ITEMS.filter((item) => !item.permission || permissions.includes(item.permission));
  const visibleOrgItems = ORGANIZATION_NAV_ITEMS.filter(
    (item) => !item.permission || permissions.includes(item.permission)
  );

  if (!open) {
    return null;
  }

  return (
    <nav className="container flex flex-col gap-1 border-t py-3 md:hidden" aria-label="Mobile navigation">
      {visibleItems.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )
          }
        >
          <Icon className="h-4 w-4" />
          {label}
        </NavLink>
      ))}

      {hasAnyAdminPermission ? (
        <div className="mt-2 border-t pt-2">
          <p className="px-3 pb-1 text-xs font-semibold uppercase text-muted-foreground">Organization</p>
          {visibleOrgItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </div>
      ) : null}
    </nav>
  );
}
