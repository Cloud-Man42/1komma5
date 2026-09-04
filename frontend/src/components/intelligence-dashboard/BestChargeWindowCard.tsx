"use client";

import { useEffect, useState } from "react";
import type { EnergyStrategyCurrent, EvRecommendation } from "@/lib/api";
import { fetchEnergyStrategyCurrent } from "@/lib/api";
import { toOrePerKwh } from "@/lib/prices";

function formatWindow(rec: EvRecommendation, timezone: string): string {
  const start = new Date(rec.window_start).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
  const end = new Date(rec.window_end).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
  return `${start}–${end}`;
}

export function BestChargeWindowCard({ slug, timezone }: { slug: string; timezone: string }) {
  const [data, setData] = useState<EnergyStrategyCurrent | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchEnergyStrategyCurrent(slug)
      .then((payload) => {
        if (!active) return;
        setData(payload);
        setError(null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setData(null);
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [slug]);

  const recommendation = data?.ev_recommendations?.[0] ?? null;

  return (
    <section className="idash-panel" data-testid="best-charge-window-card">
      <h2 className="idash-panel-title">Bästa laddfönster</h2>
      {error && !data ? <p className="muted">Laddfönster otillgängligt.</p> : null}
      {!data && !error ? <p className="muted">Hämtar laddfönster…</p> : null}
      {recommendation ? (
        <>
          <p className="idash-charge-window-headline">
            {formatWindow(recommendation, timezone)} · {Math.round(toOrePerKwh(recommendation.avg_import_sek_kwh))} öre/kWh
          </p>
          <p className="muted">{recommendation.reason_sv}</p>
          {recommendation.estimated_saving_sek != null ? (
            <p className="idash-charge-window-saving">
              Uppskattad besparing: {recommendation.estimated_saving_sek.toFixed(2)} kr
            </p>
          ) : null}
        </>
      ) : data ? (
        <p className="muted">Inget rekommenderat laddfönster just nu.</p>
      ) : null}
    </section>
  );
}
