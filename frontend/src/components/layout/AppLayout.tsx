import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { FileStack, FolderOpen, LayoutDashboard, MessageSquare, Menu, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/folders", label: "Folders", icon: FolderOpen },
  { to: "/files", label: "Files", icon: FileStack },
  { to: "/search", label: "Chat", icon: MessageSquare },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
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
    </>
  );
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between">
          <h1 className="text-lg font-semibold">Reverse File Search</h1>

          <div className="flex items-center gap-2">
            <nav className="hidden items-center gap-1 md:flex" aria-label="Main navigation">
              <NavLinks />
            </nav>

            <ThemeToggle />

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

        {mobileOpen ? (
          <nav className="container flex flex-col gap-1 border-t py-3 md:hidden" aria-label="Mobile navigation">
            <NavLinks onNavigate={() => setMobileOpen(false)} />
          </nav>
        ) : null}
      </header>

      <main className="container flex min-h-0 flex-1 flex-col py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
