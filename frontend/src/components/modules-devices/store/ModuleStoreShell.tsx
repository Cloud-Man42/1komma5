"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { StoreStatusResponse } from "@/lib/api";

const TABS = [
  { href: "/config/modules-devices/store", label: "Discover", exact: true },
  { href: "/config/modules-devices/store/categories", label: "Categories" },
  { href: "/config/modules-devices/store/installed", label: "Installed" },
  { href: "/config/modules-devices/store/updates", label: "Updates" },
  { href: "/config/modules-devices/store/publishers", label: "Publishers" },
  { href: "/config/modules-devices/store/security", label: "Security" },
];

export function ModuleStoreShell({
  children,
  status,
}: {
  children: React.ReactNode;
  status?: StoreStatusResponse | null;
}) {
  const pathname = usePathname();
  return (
    <div className="config-page store-shell" data-testid="module-store-shell">
      <header className="config-page-header">
        <h1 className="config-page-title">Module Store</h1>
        <p className="config-page-lead">Discover, evaluate, and install EMIC modules with full trust and security transparency.</p>
      </header>
      {status ? (
        <div
          className={
            status.invalid || status.offline
              ? "config-banner warn"
              : status.stale
                ? "config-banner"
                : "config-banner success"
          }
          data-testid="store-status-banner"
        >
          {status.message}
          {status.last_success ? ` Last synced: ${new Date(status.last_success).toLocaleString()}.` : null}
        </div>
      ) : null}
      <nav className="config-subnav store-subnav" aria-label="Module Store">
        {TABS.map((tab) => {
          const active =
            tab.exact === true
              ? pathname === tab.href
              : pathname != null && (pathname === tab.href || pathname.startsWith(`${tab.href}/`));
          return (
            <Link key={tab.href} href={tab.href} className={active ? "config-subnav-link active" : "config-subnav-link"}>
              {tab.label}
            </Link>
          );
        })}
      </nav>
      {children}
    </div>
  );
}
