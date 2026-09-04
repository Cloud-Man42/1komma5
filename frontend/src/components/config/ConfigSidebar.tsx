"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CONFIG_NAV_ITEMS, isConfigNavActive } from "./configNavItems";

export function ConfigSidebar() {
  const pathname = usePathname() ?? "";

  return (
    <nav className="config-sidebar" aria-label="Konfigurationsmeny">
      <p className="config-sidebar-kicker">Inställningar</p>
      <ul className="config-sidebar-list">
        {CONFIG_NAV_ITEMS.map((item) => {
          const active = isConfigNavActive(pathname, item);
          return (
            <li key={item.id}>
              <Link
                href={item.href}
                className={`config-sidebar-link${active ? " config-sidebar-link-active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                <span className="config-sidebar-link-label">{item.label}</span>
                <span className="config-sidebar-link-desc">{item.description}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
