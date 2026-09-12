"use client";

import { HeartbeatAccountsPanel } from "@/components/config/HeartbeatAccountsPanel";
import {
  ChargeAmpsReadinessSection,
  HeartbeatStatusCard,
} from "@/components/config/HeartbeatConfigPanel";
import { SiteModulesPanel } from "@/components/config/SiteModulesPanel";

export default function ConfigSystemPage() {
  return (
    <>
      <header className="config-page-header">
        <h2 className="config-page-title">System</h2>
        <p className="muted config-page-intro">
          Heartbeat-anslutning, dashboard-intervall, Charge Amps, moduler och smart laddnings-readiness.
          {" "}
          <a href="/config/modules-devices?site=akarp">Öppna Moduler &amp; enheter →</a>
        </p>
      </header>
      <HeartbeatAccountsPanel />
      <SiteModulesPanel siteSlug="akarp" />
      <ChargeAmpsReadinessSection />
      <HeartbeatStatusCard />
    </>
  );
}
