"use client";

import { useState } from "react";
import type { MultiSiteAggregate, MultiSiteSiteEntry } from "@/lib/multiSiteApi";

export function OverviewEnergyFlow({
  aggregate,
  sites,
}: {
  aggregate: MultiSiteAggregate;
  sites: MultiSiteSiteEntry[];
}) {
  const [expanded, setExpanded] = useState(false);
  const fmt = (v: number | null | undefined) => (v == null ? "—" : `${v.toFixed(1)} kW`);

  return (
    <section className="ms-flow-card">
      <h2>Energiflöde (aggregerat)</h2>
      <div className="ms-flow-grid">
        <div>
          <span className="ms-kpi-label">Sol</span>
          <strong className="ms-kpi-value">{fmt(aggregate.solarPowerKw)}</strong>
        </div>
        <div>
          <span className="ms-kpi-label">Förbrukning</span>
          <strong className="ms-kpi-value">{fmt(aggregate.consumptionPowerKw)}</strong>
        </div>
        <div>
          <span className="ms-kpi-label">Batteri</span>
          <strong className="ms-kpi-value">
            {aggregate.batteryChargePowerKw
              ? `${fmt(aggregate.batteryChargePowerKw)} laddning`
              : aggregate.batteryDischargePowerKw
                ? `${fmt(aggregate.batteryDischargePowerKw)} urladdning`
                : "—"}
          </strong>
        </div>
        <div>
          <span className="ms-kpi-label">Nät (netto)</span>
          <strong className="ms-kpi-value">{fmt(aggregate.gridNetPowerKw)}</strong>
        </div>
      </div>
      <button type="button" className="ms-btn-ghost" onClick={() => setExpanded((v) => !v)}>
        {expanded ? "Dölj per anläggning" : "Visa per anläggning"}
      </button>
      {expanded ? (
        <ul className="ms-site-selector-list">
          {sites.map((site) => (
            <li key={site.slug}>
              {site.name}: sol {fmt(site.live.solarPowerKw)}, last {fmt(site.live.consumptionPowerKw)}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
