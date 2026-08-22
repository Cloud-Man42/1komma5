"use client";

import { useEffect, useState } from "react";

import { SpaEnergyPeriod, fetchSpaEnergyPeriod } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

function formatKwh(value: number): string {
  return `${value.toFixed(1)} kWh`;
}

export function SpaEnergyAnalysis({ siteSlug, period }: { siteSlug: string; period: string }) {
  const [data, setData] = useState<SpaEnergyPeriod | null>(null);

  useEffect(() => {
    fetchSpaEnergyPeriod(siteSlug, period)
      .then(setData)
      .catch(() => setData(null));
  }, [siteSlug, period]);

  if (!data?.has_data) {
    return <p className="muted">Ingen energidata för vald period.</p>;
  }

  const total = data.energy_kwh;
  const pct = (part: number) => (total > 0 ? ((part / total) * 100).toFixed(1) : "0.0");

  return (
    <section className="spa-analysis" data-testid="spa-energy-analysis">
      <h4>Spa → Energi</h4>
      <p>
        Förbrukning: <strong>{formatKwh(data.energy_kwh)}</strong>
      </p>
      <ul>
        <li>Från sol: {formatKwh(data.solar_direct_kwh)} ({pct(data.solar_direct_kwh)} %)</li>
        <li>Från batteri: {formatKwh(data.solar_battery_kwh + data.grid_battery_kwh)} ({pct(data.solar_battery_kwh + data.grid_battery_kwh)} %)</li>
        <li>Från nät: {formatKwh(data.grid_direct_kwh)} ({pct(data.grid_direct_kwh)} %)</li>
        {data.unknown_kwh > 0 && <li>Okänd: {formatKwh(data.unknown_kwh)}</li>}
      </ul>
      <p>
        Faktisk kostnad: <strong>{formatSekAmount(data.actual_cost_sek).label}</strong>
      </p>
      {data.reference_cost_sek != null && (
        <p>Kostnad utan egen energi: {formatSekAmount(data.reference_cost_sek).label}</p>
      )}
      {data.savings_sek != null && (
        <p>
          Besparing: <strong>{formatSekAmount(data.savings_sek).label}</strong>
          {data.savings_pct != null ? ` (${data.savings_pct.toFixed(0)} %)` : ""}
        </p>
      )}
    </section>
  );
}
