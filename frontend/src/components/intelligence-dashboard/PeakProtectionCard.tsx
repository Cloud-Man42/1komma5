"use client";

import { useMemo } from "react";
import type { SiteDashboard } from "@/lib/api";

type Props = {
  dashboard: SiteDashboard;
};

function isPeakAlert(message: string): boolean {
  const haystack = message.toLowerCase();
  return (
    haystack.includes("effekttariff") ||
    haystack.includes("säkring") ||
    haystack.includes("effekttopp") ||
    haystack.includes("import") && haystack.includes("gräns")
  );
}

export function PeakProtectionCard({ dashboard }: Props) {
  const peakAlerts = useMemo(
    () => dashboard.alerts.filter((alert) => isPeakAlert(alert.message_sv)),
    [dashboard.alerts],
  );

  if (peakAlerts.length === 0) {
    return (
      <section className="idash-panel idash-peak-protection-panel" data-testid="peak-protection-card">
        <h2 className="idash-panel-title">EFFEKTTARIFF &amp; SÄKRING</h2>
        <p className="idash-muted">Ingen aktiv effekttoppsvarning just nu.</p>
      </section>
    );
  }

  return (
    <section className="idash-panel idash-peak-protection-panel idash-peak-protection-active" data-testid="peak-protection-card">
      <h2 className="idash-panel-title">EFFEKTTARIFF &amp; SÄKRING</h2>
      <ul className="idash-peak-protection-list">
        {peakAlerts.map((alert, index) => (
          <li key={`${alert.severity}-${index}`} className={`idash-peak-alert idash-peak-alert-${alert.severity}`}>
            {alert.message_sv}
          </li>
        ))}
      </ul>
    </section>
  );
}
