"use client";

import { useEffect, useState } from "react";

import { SpaHistory, fetchSpaHistory } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

export function SpaEnergyHistory({ siteSlug, period }: { siteSlug: string; period: string }) {
  const [history, setHistory] = useState<SpaHistory | null>(null);

  useEffect(() => {
    fetchSpaHistory(siteSlug, period)
      .then(setHistory)
      .catch(() => setHistory({ period, points: [] }));
  }, [siteSlug, period]);

  if (!history || history.points.length === 0) {
    return <p className="muted">Väntar på mätdata för historik.</p>;
  }

  return (
    <section data-testid="spa-energy-history">
      <h4>Historik</h4>
      <div className="spa-history-chart">
        {history.points.map((point) => {
          const maxPower = Math.max(...history.points.map((p) => p.power_w ?? 0), 1);
          const height = point.power_w ? Math.max(4, (point.power_w / maxPower) * 100) : 0;
          return (
            <div key={point.timestamp} className="spa-history-bar" title={`${point.energy_kwh?.toFixed(2) ?? 0} kWh`}>
              <div className="spa-history-bar-fill" style={{ height: `${height}%` }} />
            </div>
          );
        })}
      </div>
      <ul className="spa-history-list">
        {history.points.slice(-5).map((point) => (
          <li key={point.timestamp}>
            {new Date(point.timestamp).toLocaleString("sv-SE")} — {point.energy_kwh?.toFixed(2) ?? "0"} kWh
            {point.cost_sek != null ? ` · ${formatSekAmount(point.cost_sek).label}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
