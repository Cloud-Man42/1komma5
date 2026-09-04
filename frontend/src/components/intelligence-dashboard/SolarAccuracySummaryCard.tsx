"use client";

import { useEffect, useState } from "react";
import { fetchSolarAccuracy, type SolarAccuracy } from "@/lib/api";

type Props = {
  slug: string;
};

export function SolarAccuracySummaryCard({ slug }: Props) {
  const [data, setData] = useState<SolarAccuracy | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSolarAccuracy(slug)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (error) {
    return (
      <section className="idash-panel" data-testid="solar-accuracy-summary-card">
        <h2 className="idash-panel-title">SOLPROGNOS-NOGGRANNHET</h2>
        <p className="idash-muted">Kunde inte hämta solprognos-noggrannhet: {error}</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="idash-panel" data-testid="solar-accuracy-summary-card">
        <h2 className="idash-panel-title">SOLPROGNOS-NOGGRANNHET</h2>
        <p className="idash-muted">Hämtar solprognos-noggrannhet…</p>
      </section>
    );
  }

  const mape = data.mape_7d_pct != null ? `${data.mape_7d_pct.toFixed(1)} %` : "—";
  const bias = data.bias_pct_30d != null ? `${data.bias_pct_30d.toFixed(1)} %` : "—";

  return (
    <section className="idash-panel" data-testid="solar-accuracy-summary-card">
      <h2 className="idash-panel-title">SOLPROGNOS-NOGGRANNHET</h2>
      <dl className="idash-forecast-learning-stats">
        <div>
          <dt>MAPE (7d)</dt>
          <dd>{mape}</dd>
        </div>
        <div>
          <dt>BIAS (30d)</dt>
          <dd>{bias}</dd>
        </div>
        <div>
          <dt>KORRIGERING</dt>
          <dd>{data.correction_factor.toFixed(3)}×</dd>
        </div>
      </dl>
    </section>
  );
}
