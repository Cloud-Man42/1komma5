"use client";

import { SpaHealth } from "@/lib/api";

export function SpaHealthPanel({ health }: { health: SpaHealth }) {
  const lowQuality =
    (health.estimated_pct ?? 0) + (health.missing_pct ?? 0) > 40;

  return (
    <section className="diagnostics-panel" data-testid="spa-health-panel">
      <h4>Health Center — Arctic Spa</h4>
      <ul>
        <li>API: {health.api_status}</li>
        <li>Spa: {health.spa_status}</li>
        <li>Polling: {health.polling_status}</li>
        <li>Databas: {health.database_status}</li>
        <li>Samples senaste 24h: {health.samples_last_24h}</li>
        <li>Samples med effekt: {health.samples_with_power_24h}</li>
        <li>Sample-energi 24h: {health.sample_energy_kwh_24h.toFixed(2)} kWh</li>
        <li>Intervall senaste 24h: {health.intervals_last_24h}</li>
        <li>Datakvalitet: {health.data_quality}</li>
      </ul>
      {lowQuality && (
        <p className="form-error">Varning: datakvaliteten är låg (estimerad/saknad data).</p>
      )}
      {health.last_error && health.last_error.trim().length > 0 && (
        <p className="muted">Senaste fel: {health.last_error}</p>
      )}
      {health.integration_degraded && (
        <p className="form-error">{health.integration_degraded_message_sv || "Smartstyrning är tillfälligt otillgänglig."}</p>
      )}
      {health.actuator_state && <p className="muted">Actuator: {health.actuator_state}</p>}
    </section>
  );
}
