"use client";

import { useEffect, useState } from "react";
import { SpaShadow, fetchSpaShadow } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

export function SpaShadowModePanel({ siteSlug }: { siteSlug: string }) {
  const [shadow, setShadow] = useState<SpaShadow | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSpaShadow(siteSlug)
      .then(setShadow)
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda shadow mode"));
  }, [siteSlug]);

  if (error) return <p className="form-error">{error}</p>;
  if (!shadow) return <p className="muted">Laddar shadow mode…</p>;

  return (
    <section className="card" data-testid="spa-shadow-panel">
      <h3>Shadow Mode</h3>
      {shadow.shadow_mode_active ? (
        <p className="muted">Shadow Mode är aktiv — EMIC jämför faktiskt schema mot optimal plan.</p>
      ) : (
        <p className="muted">Shadow Mode är inaktiv.</p>
      )}
      {shadow.integration_degraded && (
        <p className="form-error">{shadow.integration_degraded_message_sv}</p>
      )}
      <div className="spa-kpi-grid">
        <div className="spa-kpi">
          <p className="spa-kpi-value">{formatSekAmount(shadow.total_actual_cost_sek).label}</p>
          <p className="spa-kpi-label">Faktisk kostnad (7 d)</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">{formatSekAmount(shadow.total_optimized_cost_sek).label}</p>
          <p className="spa-kpi-label">EMIC-optimerad (Beräknad)</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">{formatSekAmount(shadow.total_potential_saving_sek).label}</p>
          <p className="spa-kpi-label">Potentiell besparing</p>
        </div>
      </div>
      {shadow.days.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Datum</th>
              <th>Faktisk</th>
              <th>Optimerad</th>
              <th>Besparing</th>
            </tr>
          </thead>
          <tbody>
            {shadow.days.map((day) => (
              <tr key={day.date_label}>
                <td>{day.date_label}</td>
                <td>{formatSekAmount(day.actual_cost_sek).label}</td>
                <td>{formatSekAmount(day.optimized_cost_sek).label}</td>
                <td>{formatSekAmount(day.potential_saving_sek).label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
