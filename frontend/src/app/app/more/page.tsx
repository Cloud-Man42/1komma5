"use client";

import Link from "next/link";
import { useAuth } from "@/lib/authContext";

export default function MobileMorePage() {
  const { can, user } = useAuth();

  const links = [
    { href: "/app/more/health", label: "System health", show: true },
    { href: "/app/energy/history", label: "History", show: true },
    { href: "/app/more/account", label: "My account", show: Boolean(user) },
    { href: "/app/install", label: "Install PWA", show: true },
    { href: "/app/diagnostics", label: "PWA diagnostics", show: true },
    { href: "/config", label: "Settings / Config", show: can("sites.read") || can("system.read") },
    { href: "/app/more/admin", label: "Administration", show: can("users.read") || can("roles.read") },
    { href: "/overview", label: "Desktop overview", show: true },
  ].filter((l) => l.show);

  return (
    <div className="mobile-hub">
      <h1 className="mobile-hub-title">More</h1>
      <ul className="mobile-hub-list">
        {links.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className="mobile-hub-link">
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
