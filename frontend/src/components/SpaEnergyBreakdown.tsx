"use client";

import { useEffect, useState } from "react";

import { SpaEnergyBreakdown as SpaEnergyBreakdownData, fetchSpaEnergyBreakdown } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

function formatKwh(value: number): string {
  return `${value.toFixed(1)} kWh`;
}

function periodColumnLabel(period: string): string {
  if (period === "year" || period === "total" || period === "rolling12") return "Månad";
  return "Datum";
}

export function SpaEnergyBreakdown({ siteSlug, period }: { siteSlug: string; period: string }) {
  const [data, setData] = useState<SpaEnergyBreakdownData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    fetchSpaEnergyBreakdown(siteSlug, period)
      .then(setData)
      .catch((err: unknown) => {
        setData(null);
        setError(err instanceof Error ? err.message : "Kunde inte ladda energifördelning");
      });
  }, [siteSlug, period]);

  if (error) {
    return <p className="form-error" role="alert">{error}</p>;
  }

  if (!data || data.rows.length === 0) {
    return <p className="muted">Ingen daglig energidata för vald period.</p>;
  }

  return (
    <section data-testid="spa-energy-breakdown">
      <h4>Energi per {data.granularity === "month" ? "månad" : "dag"}</h4>
      <div className="peaks-table-wrap">
        <table className="peaks-table finance-table spa-breakdown-table">
          <thead>
            <tr>
              <th scope="col">{periodColumnLabel(period)}</th>
              <th scope="col">Förbrukning</th>
              <th scope="col">Solel</th>
              <th scope="col">Batteri</th>
              <th scope="col">Nät</th>
              <th scope="col">Kostnad köpt el</th>
              <th scope="col">Värde solel</th>
              <th scope="col">Värde batteri</th>
            </tr>
          </thead>
          <tbody>
            {[...data.rows].reverse().map((row) => (
              <tr key={row.period_start}>
                <th scope="row">{row.period_label}</th>
                <td>{formatKwh(row.energy_kwh)}</td>
                <td>{formatKwh(row.solar_kwh)}</td>
                <td>{formatKwh(row.battery_kwh)}</td>
                <td>{formatKwh(row.grid_kwh)}</td>
                <td>{formatSekAmount(row.grid_cost_sek).label}</td>
                <td>{formatSekAmount(row.solar_value_sek).label}</td>
                <td>{formatSekAmount(row.battery_value_sek).label}</td>
              </tr>
            ))}
          </tbody>
          {data.total.has_data && (
            <tfoot>
              <tr>
                <th scope="row">Totalt</th>
                <td>{formatKwh(data.total.energy_kwh)}</td>
                <td>{formatKwh(data.total.solar_kwh)}</td>
                <td>{formatKwh(data.total.battery_kwh)}</td>
                <td>{formatKwh(data.total.grid_kwh)}</td>
                <td>{formatSekAmount(data.total.grid_cost_sek).label}</td>
                <td>{formatSekAmount(data.total.solar_value_sek).label}</td>
                <td>{formatSekAmount(data.total.battery_value_sek).label}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </section>
  );
}
