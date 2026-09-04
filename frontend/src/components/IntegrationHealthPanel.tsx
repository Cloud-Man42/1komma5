"use client";

import { useEffect, useState } from "react";
import { fetchIntegrationHealth, type IntegrationHealthResponse } from "@/lib/api";
import { integrationProviderLabelSv } from "@/lib/integrationHealthLabels";

function statusLabel(status: string): string {
  switch (status) {
    case "ok":
      return "OK";
    case "error":
      return "Fel";
    case "stale":
      return "Inaktuell";
    default:
      return status;
  }
}

function formatStaleSeconds(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)} s`;
  return `${Math.round(seconds / 60)} min`;
}

export function IntegrationHealthPanel({ siteSlug }: { siteSlug: string }) {
  const [data, setData] = useState<IntegrationHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchIntegrationHealth(siteSlug)
      .then((payload) => {
        if (active) {
          setData(payload);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setData(null);
          setError(err.message);
        }
      });
    return () => {
      active = false;
    };
  }, [siteSlug]);

  const alertCount =
    data?.providers.filter(
      (row) => row.status !== "ok" || row.consecutive_failures >= 3,
    ).length ?? 0;

  return (
    <section className="diagnostics-panel" data-testid="integration-health-panel">
      <header>
        <h3>Integrationshälsa</h3>
        <p>Status för externa providers (Heartbeat, laddare, m.m.)</p>
      </header>

      {error && !data ? <p className="form-error">{error}</p> : null}
      {!data && !error ? <p>Hämtar integrationshälsa…</p> : null}

      {data ? (
        <>
          {alertCount > 0 ? (
            <p className="form-error" data-testid="integration-health-alert">
              {alertCount} provider(s) behöver uppmärksamhet
            </p>
          ) : (
            <p className="form-success">Alla registrerade providers ser friska ut.</p>
          )}

          {data.providers.length === 0 ? (
            <p className="muted">Ingen integrationsdata registrerad ännu.</p>
          ) : (
            <table className="config-table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Latens</th>
                  <th>Misslyckanden</th>
                  <th>Inaktuell</th>
                  <th>Senaste fel</th>
                </tr>
              </thead>
              <tbody>
                {data.providers.map((row) => (
                  <tr key={row.provider} data-testid={`integration-health-row-${row.provider}`}>
                    <td>{integrationProviderLabelSv(row.provider)}</td>
                    <td>{statusLabel(row.status)}</td>
                    <td>{row.latency_ms != null ? `${Math.round(row.latency_ms)} ms` : "—"}</td>
                    <td>{row.consecutive_failures}</td>
                    <td>{formatStaleSeconds(row.stale_seconds)}</td>
                    <td>{row.last_error_class ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      ) : null}
    </section>
  );
}
