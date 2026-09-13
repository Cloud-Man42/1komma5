"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { HomeDashboardButton } from "@/components/HomeDashboardButton";
import { UserMenu } from "@/components/UserMenu";
import { useAuth } from "@/lib/authContext";

const NAV = [
  { href: "/admin/users", label: "Användare", permission: "users.read" },
  { href: "/admin/roles", label: "Roller", permission: "roles.read" },
  { href: "/admin/audit", label: "Audit", permission: "audit.read" },
] as const;

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { can, user, loading } = useAuth();
  const userAuthEnabled = process.env.NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED === "true";

  return (
    <div className="admin-hub" data-testid="admin-shell">
      <header className="admin-hub-header">
        <div>
          <div className="admin-hub-home-row">
            <HomeDashboardButton />
            <span className="back-link">Dashboard</span>
          </div>
          <h1 className="admin-page-title">Administration</h1>
          <p className="muted admin-page-intro">Användare, roller och säkerhetslogg.</p>
        </div>
        {userAuthEnabled && !loading && user ? <UserMenu compact /> : null}
      </header>
      <div className="admin-hub-body">
        <nav className="admin-sidebar" aria-label="Administration">
          <div className="admin-sidebar-nav">
            {NAV.filter((item) => can(item.permission)).map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={
                  pathname === item.href || pathname.startsWith(`${item.href}/`)
                    ? "admin-sidebar-link admin-sidebar-link-active"
                    : "admin-sidebar-link"
                }
              >
                {item.label}
              </Link>
            ))}
          </div>
        </nav>
        <main className="admin-main">{children}</main>
      </div>
    </div>
  );
}
