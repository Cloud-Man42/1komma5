"use client";

import Link from "next/link";

const SECTIONS = [
  { href: "/app/energy/solar", label: "Solar", desc: "Production today and forecast" },
  { href: "/app/energy/battery", label: "Battery", desc: "SoC, storage and power" },
  { href: "/app/energy/grid", label: "Grid", desc: "Import, export and net" },
  { href: "/app/energy/consumption", label: "Consumption", desc: "Load now and today" },
  { href: "/app/energy/forecast", label: "Forecast", desc: "Solar intelligence" },
  { href: "/app/energy/economy", label: "Economy", desc: "Cost and savings" },
  { href: "/app/energy/history", label: "History", desc: "Energy history by site" },
] as const;

export default function MobileEnergyHubPage() {
  return (
    <div className="mobile-hub">
      <h1 className="mobile-hub-title">Energy</h1>
      <p className="muted">Solar, battery, grid and consumption</p>
      <ul className="mobile-hub-cards">
        {SECTIONS.map((section) => (
          <li key={section.href}>
            <Link href={section.href} className="mobile-hub-card-link">
              <strong>{section.label}</strong>
              <span>{section.desc}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
