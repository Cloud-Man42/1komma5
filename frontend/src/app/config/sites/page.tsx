"use client";

import { SiteListPanel } from "@/components/config/sites/SiteListPanel";

export default function ConfigSitesPage() {
  return (
    <>
      <header className="config-page-header">
        <h2 className="config-page-title">Anläggningar</h2>
        <p className="muted config-page-intro">
          Skapa nya sites och öppna detaljkonfiguration per anläggning.
        </p>
      </header>
      <SiteListPanel />
    </>
  );
}
