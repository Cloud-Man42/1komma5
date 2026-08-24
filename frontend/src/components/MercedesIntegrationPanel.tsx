"use client";

import { VehicleIntegrationStatus } from "@/lib/api";

export function MercedesIntegrationPanel({
  siteSlug,
  status,
}: {
  siteSlug: string;
  status: VehicleIntegrationStatus;
}) {
  return (
    <details className="diagnostics-subpanel" data-testid="mercedes-integration-panel">
      <summary>Integrationsdiagnostik ({siteSlug})</summary>
      <div className="diagnostics-grid">
        <div>
          <span className="muted">Anslutning</span>
          <strong>{status.connection_state}</strong>
        </div>
        <div>
          <span className="muted">Hälsa</span>
          <strong>{status.health}</strong>
        </div>
        <div>
          <span className="muted">Region</span>
          <strong>{status.region}</strong>
        </div>
        <div>
          <span className="muted">Återanslutningar</span>
          <strong>{status.reconnect_count}</strong>
        </div>
        <div>
          <span className="muted">HTTP 429</span>
          <strong>{status.http_429_count}</strong>
        </div>
        <div>
          <span className="muted">Decode-fel</span>
          <strong>{status.decode_failure_count}</strong>
        </div>
        <div>
          <span className="muted">Kommandon</span>
          <strong>{status.commands_enabled ? "Aktiverade" : "Avstängda"}</strong>
        </div>
        {status.last_error && (
          <div className="diagnostics-span-all">
            <span className="muted">Senaste fel</span>
            <strong>{status.last_error}</strong>
          </div>
        )}
      </div>
    </details>
  );
}
