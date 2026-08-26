"use client";

import { useEffect, useState } from "react";
import { SpaEconomics, fetchSpaEconomics } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

const PERIODS = [
  { id: "today", label: "Idag" },
  { id: "month", label: "Månad" },
  { id: "year", label: "År" },
];

export function SpaEconomicsPanel({ siteSlug }: { siteSlug: string }) {
  const [period, setPeriod] = useState("today");
  const [data, setData] = useState<SpaEconomics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSpaEconomics(siteSlug, period)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda ekonomi"));
  }, [siteSlug, period]);

  const qualityLabel = data?.data_quality === "MEASURED" ? "Mätt" : "Beräknad";

  return (
    <section className="card" data-testid="spa-economics-panel">
      <h3>Ekonomi</h3>
      <div className="spa-tabs">
        {PERIODS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={period === p.id ? "spa-tab active" : "spa-tab"}
            onClick={() => setPeriod(p.id)}
          >
            {p.label}
          </button>
        ))}
      </div>
      {error && <p className="form-error">{error}</p>}
      {!data && !error && <p className="muted">Laddar…</p>}
      {data && (
        <div className="spa-kpi-grid">
          <div className="spa-kpi">
            <p className="spa-kpi-value">{data.energy_kwh.toFixed(1)} kWh</p>
            <p className="spa-kpi-label">Förbrukning ({qualityLabel})</p>
          </div>
          <div className="spa-kpi">
            <p className="spa-kpi-value">{formatSekAmount(data.cost_sek).label}</p>
            <p className="spa-kpi-label">Kostnad</p>
          </div>
          <div className="spa-kpi">
            <p className="spa-kpi-value">{data.solar_share_pct != null ? `${data.solar_share_pct} %` : "—"}</p>
            <p className="spa-kpi-label">Solel</p>
          </div>
          <div className="spa-kpi">
            <p className="spa-kpi-value">{data.battery_share_pct != null ? `${data.battery_share_pct} %` : "—"}</p>
            <p className="spa-kpi-label">Batteri</p>
          </div>
          <div className="spa-kpi">
            <p className="spa-kpi-value">{data.grid_share_pct != null ? `${data.grid_share_pct} %` : "—"}</p>
            <p className="spa-kpi-label">Nät</p>
          </div>
          <div className="spa-kpi">
            <p className="spa-kpi-value">
              {data.savings_sek != null ? formatSekAmount(data.savings_sek).label : "—"}
            </p>
            <p className="spa-kpi-label">EMIC-besparing</p>
          </div>
        </div>
      )}
    </section>
  );
}
