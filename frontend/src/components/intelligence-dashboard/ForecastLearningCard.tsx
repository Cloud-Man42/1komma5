"use client";

import { useEffect, useState } from "react";
import type { ForecastLearningSummary } from "@/lib/api";
import { fetchForecastLearningSummary } from "@/lib/api";
import { toOrePerKwh } from "@/lib/prices";

function kindLabel(kind: string): string {
  switch (kind) {
    case "import_price_sek_kwh":
      return "Elpris (inköp)";
    case "load_w":
      return "Hushållslast";
    case "solar_w":
      return "Solproduktion";
    default:
      return kind;
  }
}

function formatMae(kind: string, mae: number | null): string {
  if (mae == null) return "—";
  if (kind === "import_price_sek_kwh") {
    return `${Math.round(toOrePerKwh(mae))} öre/kWh`;
  }
  if (mae >= 1000) {
    return `${(mae / 1000).toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kW`;
  }
  return `${Math.round(mae).toLocaleString("sv-SE")} W`;
}

function formatBias(kind: string, bias: number | null): string {
  if (bias == null) return "—";
  const sign = bias > 0 ? "+" : "";
  if (kind === "import_price_sek_kwh") {
    return `${sign}${Math.round(toOrePerKwh(bias))} öre/kWh`;
  }
  if (Math.abs(bias) >= 1000) {
    return `${sign}${(bias / 1000).toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kW`;
  }
  return `${sign}${Math.round(bias).toLocaleString("sv-SE")} W`;
}

export function ForecastLearningCard({ slug }: { slug: string }) {
  const [summary, setSummary] = useState<ForecastLearningSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchForecastLearningSummary(slug)
      .then((data) => {
        if (active) {
          setSummary(data);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setSummary(null);
          setError(err.message);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [slug]);

  const hasSamples = summary?.metrics.some((m) => m.sample_count > 0) ?? false;

  return (
    <section className="idash-panel idash-forecast-learning-panel" data-testid="forecast-learning-card">
      <h2 className="idash-panel-title">PROGNOSLÄRANDE</h2>
      {loading ? (
        <p className="idash-muted">Laddar prognosmätning…</p>
      ) : error ? (
        <p className="idash-muted">Kunde inte hämta prognosdata.</p>
      ) : !hasSamples ? (
        <p className="idash-muted">
          Samlar in prognoser och utfall. Mätningar visas när tillräckligt med perioder har avslutats.
        </p>
      ) : (
        <div className="idash-forecast-learning-grid">
          {summary?.metrics
            .filter((m) => m.sample_count > 0)
            .map((metric) => (
              <div key={metric.kind} className="idash-forecast-learning-row">
                <span className="idash-forecast-learning-kind">{kindLabel(metric.kind)}</span>
                <dl className="idash-forecast-learning-stats">
                  <div>
                    <dt>MAE</dt>
                    <dd>{formatMae(metric.kind, metric.mae)}</dd>
                  </div>
                  <div>
                    <dt>BIAS</dt>
                    <dd>{formatBias(metric.kind, metric.bias)}</dd>
                  </div>
                  <div>
                    <dt>PROVER</dt>
                    <dd>{metric.sample_count}</dd>
                  </div>
                </dl>
              </div>
            ))}
        </div>
      )}
    </section>
  );
}
