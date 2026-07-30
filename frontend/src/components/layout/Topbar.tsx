import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, ChevronsUpDown, Menu, User as UserIcon, X } from "lucide-react";
import { toast } from "sonner";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { useLogout } from "@/hooks/useAuth";
import { useSwitchOrganization } from "@/hooks/useOrganizations";
import { useAuthStore } from "@/store/authStore";
import { useOrganizationStore } from "@/store/organizationStore";

function OrganizationSwitcher() {
  const organization = useOrganizationStore((s) => s.organization);
  const memberships = useOrganizationStore((s) => s.memberships);
  const switchOrganization = useSwitchOrganization();

  if (memberships.length <= 1) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="hidden gap-2 sm:flex">
          {organization?.name ?? "Select organization"}
          <ChevronsUpDown className="h-3.5 w-3.5 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {memberships.map((org) => (
          <DropdownMenuItem
            key={org.id}
            onSelect={() => {
              if (org.id === organization?.id) return;
              switchOrganization.mutate(org.id, {
                onSuccess: () => toast.success(`Switched to ${org.name}`),
                onError: (e) => toast.error("Failed to switch organization", { description: e instanceof Error ? e.message : undefined }),
              });
            }}
          >
            {org.id === organization?.id ? <Check className="mr-2 h-4 w-4" /> : <span className="mr-2 w-4" />}
            {org.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function initialsFor(name: string | null, email: string): string {
  const source = name?.trim() || email;
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}

function UserMenu() {
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();
  const navigate = useNavigate();

  if (!user) {
    return null;
  }

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSettled: () => navigate("/login", { replace: true }),
    });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="rounded-full"
          aria-label="Open account menu"
        >
          {user.avatar_url ? (
            <img src={user.avatar_url} alt="" className="h-8 w-8 rounded-full object-cover" />
          ) : (
            <span className="text-xs font-semibold">{initialsFor(user.full_name, user.email)}</span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="truncate">{user.full_name || user.email}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate("/profile")}>
          <UserIcon className="mr-2 h-4 w-4" />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/security")}>Security</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/organization/dashboard")}>Organization</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleLogout} className="text-destructive focus:text-destructive">
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * The persistent header bar present on every authenticated page — logo/
 * title, the desktop `Sidebar` nav, `ThemeToggle`, the user-avatar dropdown
 * (`Profile`/`Security`/`Organization`/`Logout`), and the mobile hamburger
 * toggle. Below `md`, toggling the hamburger reveals `Navbar`'s stacked
 * mobile nav list directly under this header — same structure/behavior as
 * the original single-file `AppLayout.tsx`, just split into components.
 */
export function Topbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="border-b">
      <div className="container flex h-16 items-center justify-between">
        <h1 className="text-lg font-semibold">Reverse File Search</h1>

        <div className="flex items-center gap-2">
          <Sidebar />

          <OrganizationSwitcher />
          <ThemeToggle />
          <UserMenu />

          <button
            type="button"
            className="rounded-md p-2 hover:bg-accent md:hidden"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((prev) => !prev)}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      <Navbar open={mobileOpen} onNavigate={() => setMobileOpen(false)} />
    </header>
  );
}
