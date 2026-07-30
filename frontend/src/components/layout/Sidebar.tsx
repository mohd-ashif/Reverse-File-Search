import { NavLink, useNavigate } from "react-router-dom";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { usePermissionStore } from "@/store/permissionStore";
import { ADMIN_NAV_ITEM, NAV_ITEMS, ORGANIZATION_NAV_ITEMS, type NavItem } from "@/components/layout/navItems";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return cn(
    "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
  );
}

function NavItemLink({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink to={item.to} end={item.end} onClick={onNavigate} className={navLinkClass}>
      <Icon className="h-4 w-4" />
      {item.label}
    </NavLink>
  );
}

/**
 * Desktop-only nav links (`hidden md:flex`), rendered horizontally inside
 * the persistent header — despite the name, this app's layout is a single
 * top header rather than a literal side column, so "Sidebar" here means
 * "the desktop nav" per the plan's alternate/simpler split (Navbar = overall
 * header wrapping this + Topbar, Sidebar = desktop-only nav). This keeps the
 * existing header-only visual structure unchanged (no regression) while
 * still isolating nav-item logic/gating into its own component.
 *
 * Individual items are permission-gated inline (missing a permission hides
 * just that one link, never the whole nav).
 */
export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const permissions = usePermissionStore((s) => s.permissions);
  const hasAnyAdminPermission = permissions.some((p) => p.startsWith("admin."));
  const navigate = useNavigate();

  const visibleItems = NAV_ITEMS.filter((item) => !item.permission || permissions.includes(item.permission));
  const visibleOrgItems = ORGANIZATION_NAV_ITEMS.filter(
    (item) => !item.permission || permissions.includes(item.permission)
  );

  return (
    <nav className="hidden items-center gap-1 md:flex" aria-label="Main navigation">
      {visibleItems.map((item) => (
        <NavItemLink key={item.to} item={item} onNavigate={onNavigate} />
      ))}
      {hasAnyAdminPermission ? (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <ADMIN_NAV_ITEM.icon className="h-4 w-4" />
              {ADMIN_NAV_ITEM.label}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            {visibleOrgItems.map((item) => (
              <DropdownMenuItem
                key={item.to}
                onClick={() => {
                  navigate(item.to);
                  onNavigate?.();
                }}
              >
                <item.icon className="mr-2 h-4 w-4" />
                {item.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      ) : null}
    </nav>
  );
}
