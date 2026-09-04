"use client";

import {
  ChargeAmpsReadinessSection,
  HeartbeatConfigPanel,
  HeartbeatStatusCard,
} from "@/components/config/HeartbeatConfigPanel";

export default function ConfigSystemPage() {
  return (
    <>
      <header className="config-page-header">
        <h2 className="config-page-title">System</h2>
        <p className="muted config-page-intro">
          Heartbeat-anslutning, dashboard-intervall, Charge Amps och smart laddnings-readiness.
        </p>
      </header>
      <HeartbeatConfigPanel />
      <ChargeAmpsReadinessSection />
      <HeartbeatStatusCard />
    </>
  );
}
