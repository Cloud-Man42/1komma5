"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchVehicleIntegrationDiagnostics,
  fetchVehicleIntegrationStatus,
  fetchVehicleRawAttributes,
  runVehicleIntegrationAction,
  type VehicleAttributeObservation,
  type VehicleIntegrationDiagnosticsResponse,
  type VehicleIntegrationStatus,
} from "@/lib/api";

export default function MercedesAdminPage() {
  const [status, setStatus] = useState<VehicleIntegrationStatus | null>(null);
  const [diagnostics, setDiagnostics] = useState<VehicleIntegrationDiagnosticsResponse | null>(null);
  const [observations, setObservations] = useState<VehicleAttributeObservation[]>([]);
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextStatus, nextDiagnostics, raw] = await Promise.all([
        fetchVehicleIntegrationStatus("akarp"),
        fetchVehicleIntegrationDiagnostics("akarp"),
        fetchVehicleRawAttributes("akarp"),
      ]);
      setStatus(nextStatus);
      setDiagnostics(nextDiagnostics);
      setObservations(raw.observations ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function runAction(action: string) {
    const result = await runVehicleIntegrationAction("akarp", action);
    setMessage(result.message);
    await load();
  }

  return (
    <main className="page-shell">
      <div className="page-header">
        <div>
          <p className="page-kicker">Admin</p>
          <h1>Mercedes Integration</h1>
          <p className="page-subtitle">Diagnostik, råattribut och manuella åtgärder för Mercedes me.</p>
        </div>
        <Link href="/config" className="btn btn-secondary">Tillbaka till config</Link>
      </div>

      {message ? <p className="notice notice-info">{message}</p> : null}
      {loading ? <p>Laddar…</p> : null}

      {status ? (
        <section className="card">
          <h2>Status</h2>
          <dl className="kv-grid">
            <dt>Health</dt><dd>{diagnostics?.health_status ?? status.health}</dd>
            <dt>Connection</dt><dd>{status.connection_state}</dd>
            <dt>Username</dt><dd>{status.username || "—"}</dd>
            <dt>Token expires</dt><dd>{status.token_expires_at ?? "—"}</dd>
            <dt>Last error</dt><dd>{status.last_error ?? "—"}</dd>
            <dt>429 count</dt><dd>{status.http_429_count}</dd>
            <dt>Reconnect count</dt><dd>{status.reconnect_count}</dd>
            <dt>Polling interval</dt><dd>{diagnostics?.current_polling_interval_seconds ? `${diagnostics.current_polling_interval_seconds}s` : "—"}</dd>
            <dt>Vehicle data age</dt><dd>{diagnostics?.vehicle_data_age_seconds != null ? `${Math.round(diagnostics.vehicle_data_age_seconds)}s` : "—"}</dd>
            <dt>SoC age</dt><dd>{diagnostics?.soc_age_seconds != null ? `${Math.round(diagnostics.soc_age_seconds)}s` : "—"}</dd>
            <dt>API data age</dt><dd>{diagnostics?.api_data_age_seconds != null ? `${Math.round(diagnostics.api_data_age_seconds)}s` : "—"}</dd>
          </dl>
          <div className="button-row">
            <button type="button" className="btn btn-secondary" onClick={() => void runAction("test-connection")}>Test connection</button>
            <button type="button" className="btn btn-secondary" onClick={() => void runAction("refresh-token")}>Refresh token</button>
            <button type="button" className="btn btn-secondary" onClick={() => void runAction("fetch-vehicle-state")}>Fetch vehicle state</button>
            <button type="button" className="btn btn-secondary" onClick={() => void runAction("reset")}>Reset integration</button>
          </div>
        </section>
      ) : null}

      <section className="card">
        <h2>Raw Data Inspector</h2>
        <p>Maskerade attributobservationer från Mercedes. Inga tokens eller credentials visas.</p>
        {observations.length === 0 ? (
          <p>Inga observationer ännu. Kör collector med aktiv Mercedes-integration.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Attribute</th>
                <th>Source</th>
                <th>Type</th>
                <th>Sample</th>
                <th>Count</th>
                <th>Last seen</th>
              </tr>
            </thead>
            <tbody>
              {observations.map((obs) => (
                <tr key={`${obs.attribute_name}-${obs.source}`}>
                  <td>{obs.attribute_name}</td>
                  <td>{obs.source}</td>
                  <td>{obs.value_type}</td>
                  <td>{obs.masked_sample}</td>
                  <td>{obs.sample_count}</td>
                  <td>{new Date(obs.last_seen_at).toLocaleString("sv-SE")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>Self-heal logg</h2>
        <p>Senaste diagnostik- och själv-läkningshändelser från collector (SoC, REST-sync, anslutning).</p>
        {(diagnostics?.integration_events?.length ?? 0) === 0 ? (
          <p>Inga händelser ännu.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Tid</th>
                <th>Typ</th>
                <th>Allvar</th>
                <th>Meddelande</th>
              </tr>
            </thead>
            <tbody>
              {diagnostics?.integration_events.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.recorded_at).toLocaleString("sv-SE")}</td>
                  <td>{event.event_type}</td>
                  <td>{event.severity}</td>
                  <td>{event.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
