"use client";

import { useEffect, useState } from "react";

import { SpaEnergyPeriod, fetchSpaEnergyPeriod } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

function formatKwh(value: number): string {
  return `${value.toFixed(1)} kWh`;
}

export function SpaEnergyAnalysis({
  siteSlug,
  period,
  data: externalData,
}: {
  siteSlug: string;
  period: string;
  data?: SpaEnergyPeriod | null;
}) {
  const [data, setData] = useState<SpaEnergyPeriod | null>(externalData ?? null);

  useEffect(() => {
    if (externalData !== undefined) {
      setData(externalData);
      return;
    }
    fetchSpaEnergyPeriod(siteSlug, period)
      .then(setData)
      .catch(() => setData(null));
  }, [siteSlug, period, externalData]);

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
        <li>Från sol: {formatKwh(data.solar_kwh)} ({pct(data.solar_kwh)} %)</li>
        <li>Från batteri: {formatKwh(data.battery_kwh)} ({pct(data.battery_kwh)} %)</li>
        <li>Från nät: {formatKwh(data.grid_kwh)} ({pct(data.grid_kwh)} %)</li>
        {data.unknown_kwh > 0 && <li>Okänd: {formatKwh(data.unknown_kwh)}</li>}
      </ul>
      <h5>Kostnadsfördelning</h5>
      <ul>
        <li>
          Kostnad köpt el: <strong>{formatSekAmount(data.grid_cost_sek).label}</strong>
        </li>
        <li>Besparing solel: {formatSekAmount(data.solar_value_sek).label}</li>
        <li>Besparing batteri: {formatSekAmount(data.battery_value_sek).label}</li>
      </ul>
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
