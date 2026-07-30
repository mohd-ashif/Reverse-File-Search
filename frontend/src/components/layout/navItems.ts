import type { LucideIcon } from "lucide-react";
import { FileStack, FolderOpen, LayoutDashboard, Mail, MessageSquare, Settings, ShieldCheck, Users } from "lucide-react";

import type { Permission } from "@/types/permission";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  /** Item only renders if the user holds this permission. Omit for "always shown". */
  permission?: Permission;
}

/**
 * Main navigation, shared between the desktop `Sidebar` and the mobile
 * `Navbar` menu so the two never drift out of sync.
 *
 * Gating notes:
 * - Dashboard has no `permission` — shown to any authenticated user.
 * - Folders/Files/Search are gated on the concrete permission the spec
 *   calls out (`folder.read`/`file.read`/`search.execute`).
 * - There is no "Administration" entry here: an admin-only section is
 *   rendered separately (see `ADMIN_NAV_ITEM` below) because it's gated on
 *   "any admin.* permission", not a single `Permission` value, which this
 *   array's shape doesn't express.
 */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/folders", label: "Folders", icon: FolderOpen, permission: "folder.read" },
  { to: "/files", label: "Files", icon: FileStack, permission: "file.read" },
  { to: "/search", label: "Search", icon: MessageSquare, permission: "search.execute" },
];

/**
 * "Organization" admin section: rendered as a submenu (see `Sidebar`/`Navbar`)
 * whenever the user holds any `admin.*` permission. Members/Invitations
 * additionally require `admin.users`; Settings requires `admin.settings` —
 * matching the endpoints those pages call.
 */
export const ADMIN_NAV_ITEM: NavItem = {
  to: "/organization/dashboard",
  label: "Organization",
  icon: ShieldCheck,
};

export const ORGANIZATION_NAV_ITEMS: NavItem[] = [
  { to: "/organization/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/organization/members", label: "Members", icon: Users, permission: "admin.users" },
  { to: "/organization/invitations", label: "Invitations", icon: Mail, permission: "admin.users" },
  { to: "/organization/settings", label: "Settings", icon: Settings, permission: "admin.settings" },
];
