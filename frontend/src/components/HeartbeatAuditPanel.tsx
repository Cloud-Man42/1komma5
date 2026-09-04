"use client";

import { useEffect, useState } from "react";
import type { HeartbeatAuditDaily } from "@/lib/api";
import { fetchHeartbeatAuditToday } from "@/lib/api";

function formatSek(value: number): string {
  return `${value.toFixed(2)} kr`;
}

export function HeartbeatAuditPanel({ siteSlug }: { siteSlug: string }) {
  const [data, setData] = useState<HeartbeatAuditDaily | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchHeartbeatAuditToday(siteSlug)
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

  return (
    <section className="diagnostics-panel" data-testid="heartbeat-audit-panel">
      <header>
        <h3>Heartbeat Audit</h3>
        <p>Jämför Heartbeat EMS med EMIC-optimering (idag)</p>
      </header>

      {error && !data ? (
        <p>Auditdata otillgänglig.</p>
      ) : null}

      {!data && !error ? <p>Hämtar auditdata…</p> : null}

      {data ? (
        <>
          <div className="diag-audit-metrics">
            <div>
              <span>Faktisk nettokostnad</span>
              <strong>{formatSek(data.rollup.actual_energy_cost_sek)}</strong>
            </div>
            <div>
              <span>Baseline utan optimering</span>
              <strong>{formatSek(data.rollup.baseline_cost_without_optimization_sek)}</strong>
            </div>
            <div>
              <span>Heartbeat-besparing</span>
              <strong>{formatSek(data.rollup.heartbeat_saving_sek)}</strong>
            </div>
            <div>
              <span>EMIC teoretiskt optimum</span>
              <strong>{formatSek(data.rollup.emic_theoretical_optimal_cost_sek)}</strong>
            </div>
            <div>
              <span>Extra EMIC-potential</span>
              <strong>{formatSek(data.rollup.additional_optimization_potential_sek)}</strong>
            </div>
            <div>
              <span>Heartbeat-effektivitet</span>
              <strong data-testid="heartbeat-efficiency">
                {data.rollup.heartbeat_efficiency_pct != null
                  ? `${data.rollup.heartbeat_efficiency_pct.toFixed(1)} %`
                  : "—"}
              </strong>
            </div>
          </div>

          {data.periods.length > 0 ? (
            <div className="diag-audit-table-wrap">
              <table className="diag-audit-table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Heartbeat</th>
                    <th>EMIC</th>
                    <th>Import W</th>
                  </tr>
                </thead>
                <tbody>
                  {data.periods.slice(-8).map((row) => (
                    <tr key={row.period_start}>
                      <td>
                        {new Date(row.period_start).toLocaleTimeString("sv-SE", {
                          hour: "2-digit",
                          minute: "2-digit",
                          timeZone: data.timezone,
                        })}
                      </td>
                      <td>{row.heartbeat_mode ?? row.ai_decision ?? "—"}</td>
                      <td>{row.emic_strategy_state?.replaceAll("_", " ") ?? "—"}</td>
                      <td>{row.grid_import_w != null ? Math.round(row.grid_import_w) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
