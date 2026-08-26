"use client";

import { useEffect, useState } from "react";

import { SpaHistory, fetchSpaHistory } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

function pointLabel(point: SpaHistory["points"][number]): string {
  if (point.period_label) return point.period_label;
  return new Date(point.timestamp).toLocaleString("sv-SE");
}

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
            <div
              key={point.timestamp}
              className="spa-history-bar"
              title={`${point.energy_kwh?.toFixed(2) ?? 0} kWh`}
            >
              <div className="spa-history-bar-fill" style={{ height: `${height}%` }} />
            </div>
          );
        })}
      </div>
      <ul className="spa-history-list">
        {history.points.slice(-5).map((point) => (
          <li key={point.timestamp}>
            {pointLabel(point)} — {point.energy_kwh?.toFixed(2) ?? "0"} kWh
            {point.grid_cost_sek != null ? ` · köpt el ${formatSekAmount(point.grid_cost_sek).label}` : ""}
            {point.solar_value_sek != null && point.solar_value_sek > 0
              ? ` · besparing solel ${formatSekAmount(point.solar_value_sek).label}`
              : ""}
            {point.battery_value_sek != null && point.battery_value_sek > 0
              ? ` · batteri ${formatSekAmount(point.battery_value_sek).label}`
              : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
