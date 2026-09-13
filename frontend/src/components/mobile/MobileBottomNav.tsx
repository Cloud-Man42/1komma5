"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/authContext";

const TABS = [
  { id: "home", href: "/app", label: "Home", match: (p: string) => p === "/app" || p === "/overview" || p === "/" },
  { id: "sites", href: "/app/sites", label: "Sites", match: (p: string) => p.startsWith("/app/sites") || p.startsWith("/sites/") },
  { id: "energy", href: "/app/energy", label: "Energy", match: (p: string) => p.startsWith("/app/energy") || p.includes("/energy") || p.includes("/solar") || p.includes("/costs") },
  { id: "control", href: "/app/control", label: "Control", match: (p: string) => p.startsWith("/app/control") || p.includes("/ev") || p.includes("/spa") || p.includes("/vehicle") },
  { id: "more", href: "/app/more", label: "More", match: (p: string) => p.startsWith("/app/more") || p.startsWith("/config") || p.startsWith("/admin") || p.startsWith("/account") },
] as const;

export function MobileBottomNav() {
  const pathname = usePathname();
  const { can } = useAuth();

  return (
    <nav className="mobile-bottom-nav" aria-label="Huvudnavigering">
      {TABS.map((tab) => {
        if (tab.id === "control" && !can("charging.read") && !can("spa.read")) return null;
        const active = tab.match(pathname);
        return (
          <Link
            key={tab.id}
            href={tab.href}
            className={`mobile-bottom-nav-item${active ? " mobile-bottom-nav-item-active" : ""}`}
            aria-current={active ? "page" : undefined}
          >
            <span className="mobile-bottom-nav-icon" aria-hidden="true">
              {tab.label.charAt(0)}
            </span>
            <span className="mobile-bottom-nav-label">{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
