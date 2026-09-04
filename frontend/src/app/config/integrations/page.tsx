"use client";

import Link from "next/link";

const INTEGRATIONS = [
  {
    href: "/admin/integrations/mercedes",
    title: "Mercedes me",
    description: "Diagnostik och råattribut för kopplade fordon.",
  },
  {
    href: "/admin/integrations/chargefinder",
    title: "ChargeFinder",
    description: "Laddstationslookup och diagnostik.",
  },
];

export default function ConfigIntegrationsPage() {
  return (
    <>
      <header className="config-page-header">
        <h2 className="config-page-title">Integrationer</h2>
        <p className="muted config-page-intro">
          Externa tjänster med egna admin-vyer. Per-site-koppling görs under anläggningar.
        </p>
      </header>
      <div className="config-integration-grid">
        {INTEGRATIONS.map((item) => (
          <Link key={item.href} href={item.href} className="config-integration-card">
            <h3 className="config-status-card-title">{item.title}</h3>
            <p className="config-status-card-body">{item.description}</p>
            <span className="btn-secondary">Öppna →</span>
          </Link>
        ))}
      </div>
    </>
  );
}
