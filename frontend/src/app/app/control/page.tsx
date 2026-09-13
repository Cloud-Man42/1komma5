"use client";

import Link from "next/link";
import { useAuth } from "@/lib/authContext";

const SECTIONS = [
  { href: "/app/control/charging", label: "Charging", desc: "EV and smart charging", perm: "charging.read" },
  { href: "/app/control/spa", label: "SPA", desc: "Pool heating and schedules", perm: "spa.read" },
  { href: "/app/control/vehicle", label: "Vehicle", desc: "Mercedes status", perm: "dashboard.read" },
] as const;

export default function MobileControlHubPage() {
  const { can } = useAuth();
  const visible = SECTIONS.filter((s) => can(s.perm));

  return (
    <div className="mobile-hub">
      <h1 className="mobile-hub-title">Control</h1>
      {visible.length === 0 ? (
        <p className="muted">No control features available for your role.</p>
      ) : (
        <ul className="mobile-hub-cards">
          {visible.map((section) => (
            <li key={section.href}>
              <Link href={section.href} className="mobile-hub-card-link">
                <strong>{section.label}</strong>
                <span>{section.desc}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
