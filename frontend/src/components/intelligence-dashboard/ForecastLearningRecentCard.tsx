"use client";

import { useEffect, useState } from "react";
import type { ForecastSnapshot } from "@/lib/api";
import { fetchForecastLearningRecent } from "@/lib/api";

function formatWhen(iso: string, timezone: string): string {
  return new Date(iso).toLocaleString("sv-SE", {
    timeZone: timezone,
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ForecastLearningRecentCard({ slug, timezone }: { slug: string; timezone: string }) {
  const [snapshots, setSnapshots] = useState<ForecastSnapshot[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchForecastLearningRecent(slug, undefined, 7)
      .then((data) => {
        if (active) {
          setSnapshots(data.snapshots);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setSnapshots([]);
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

  return (
    <section className="idash-panel idash-forecast-recent-panel" data-testid="forecast-learning-recent-card">
      <h2 className="idash-panel-title">SENASTE PROGNOSJÄMFÖRELSER</h2>
      {loading ? (
        <p className="idash-muted">Laddar jämförelser…</p>
      ) : error ? (
        <p className="idash-muted">Kunde inte hämta prognosjämförelser.</p>
      ) : snapshots.length === 0 ? (
        <p className="idash-muted">Inga avslutade prognosperioder att visa ännu.</p>
      ) : (
        <ul className="idash-forecast-recent-list">
          {snapshots.map((snapshot) => (
            <li key={`${snapshot.kind}-${snapshot.forecast_recorded_at}`}>
              <strong>{snapshot.kind}</strong>
              <span className="idash-muted">{formatWhen(snapshot.forecast_recorded_at, timezone)}</span>
              <span>
                {snapshot.actual_value != null
                  ? `utfall ${Math.round(snapshot.actual_value)}`
                  : "väntar på utfall"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
