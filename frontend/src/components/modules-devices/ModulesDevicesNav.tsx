"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/config/modules-devices", label: "Översikt" },
  { href: "/config/modules-devices/modules", label: "Moduler" },
  { href: "/config/modules-devices/store", label: "Module Store" },
  { href: "/config/modules-devices/runtime", label: "Runtime Isolation" },
  { href: "/config/modules-devices/governance/publishers", label: "Governance: Publishers" },
  { href: "/config/modules-devices/governance/policy", label: "Governance: Policy" },
  { href: "/config/modules-devices/governance/diagnostics", label: "Governance: Diagnostics" },
  { href: "/config/modules-devices/publishers", label: "Publisher keys" },
  { href: "/config/modules-devices/devices", label: "Enheter" },
];

export function ModulesDevicesNav() {
  const pathname = usePathname();
  return (
    <nav className="config-subnav" aria-label="Moduler och enheter">
      {ITEMS.map((item) => {
        const active = pathname != null && (pathname === item.href || pathname.startsWith(`${item.href}/`));
        return (
          <Link
            key={item.href}
            href={item.href}
            className={active ? "config-subnav-link active" : "config-subnav-link"}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
