"use client";

import { useEffect, useState } from "react";
import {
  fetchForecastLearningSummary,
  fetchSolarAccuracy,
  type ForecastLearningSummary,
  type SolarAccuracy,
} from "@/lib/api";

type Props = {
  slug: string;
};

function solarMetric(summary: ForecastLearningSummary | null) {
  return summary?.metrics.find((metric) => metric.kind === "solar_w") ?? null;
}

export function ForecastLearningLoopCard({ slug }: Props) {
  const [learning, setLearning] = useState<ForecastLearningSummary | null>(null);
  const [accuracy, setAccuracy] = useState<SolarAccuracy | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchForecastLearningSummary(slug), fetchSolarAccuracy(slug)])
      .then(([learningPayload, accuracyPayload]) => {
        if (cancelled) return;
        setLearning(learningPayload);
        setAccuracy(accuracyPayload);
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
      <section className="idash-panel" data-testid="forecast-learning-loop-card">
        <h2 className="idash-panel-title">CLOSED-LOOP LEARNING</h2>
        <p className="idash-muted">Kunde inte hämta closed-loop learning: {error}</p>
      </section>
    );
  }

  if (!learning) {
    return (
      <section className="idash-panel" data-testid="forecast-learning-loop-card">
        <h2 className="idash-panel-title">CLOSED-LOOP LEARNING</h2>
        <p className="idash-muted">Hämtar closed-loop learning…</p>
      </section>
    );
  }

  const metric = solarMetric(learning);
  const factor = accuracy?.correction_factor ?? 1;
  const recentBias =
    metric?.bias != null
      ? `${metric.bias >= 0 ? "+" : ""}${Math.round(metric.bias).toLocaleString("sv-SE")} W`
      : "—";
  const samples = metric?.sample_count ?? 0;
  const activeCorrection = factor !== 1;

  return (
    <section className="idash-panel" data-testid="forecast-learning-loop-card">
      <h2 className="idash-panel-title">CLOSED-LOOP LEARNING</h2>
      <dl className="idash-forecast-learning-stats">
        <div>
          <dt>SOL-BIAS</dt>
          <dd>{recentBias}</dd>
        </div>
        <div>
          <dt>PROVER</dt>
          <dd>{samples}</dd>
        </div>
        <div>
          <dt>SOL-KORRIGERING</dt>
          <dd>{activeCorrection ? `${factor.toFixed(3)}×` : "Nej (1.000×)"}</dd>
        </div>
      </dl>
      {learning.last_reconciled_at ? (
        <p className="idash-muted">
          Senast avstämd:{" "}
          {new Date(learning.last_reconciled_at).toLocaleString("sv-SE", {
            dateStyle: "short",
            timeStyle: "short",
          })}
        </p>
      ) : null}
    </section>
  );
}
