"use client";

import { useEffect, useState } from "react";
import { SpaTimeline, fetchSpaTimeline } from "@/lib/api";

const SOURCE_LABELS: Record<string, string> = {
  SOLAR: "Solel",
  BATTERY: "Batteri",
  GRID: "Nät",
  MIXED: "Blandat",
};

export function SpaEnergyTimeline({ siteSlug }: { siteSlug: string }) {
  const [timeline, setTimeline] = useState<SpaTimeline | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSpaTimeline(siteSlug)
      .then(setTimeline)
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda tidslinje"));
  }, [siteSlug]);

  if (error) return <p className="form-error">{error}</p>;
  if (!timeline) return <p className="muted">Laddar energitidslinje…</p>;
  if (timeline.entries.length === 0) {
    return (
      <section className="card" data-testid="spa-energy-timeline">
        <h3>Energitidslinje</h3>
        <p className="muted">Ingen planerad aktivitet just nu.</p>
      </section>
    );
  }

  return (
    <section className="card" data-testid="spa-energy-timeline">
      <h3>Energitidslinje</h3>
      <ul className="spa-timeline-list">
        {timeline.entries.map((entry) => (
          <li key={entry.timestamp} className="spa-timeline-row">
            <span className="spa-timeline-time">{entry.hour_label}</span>
            <span className="spa-timeline-action">{entry.action_sv}</span>
            {entry.energy_source && (
              <span className="spa-timeline-source">{SOURCE_LABELS[entry.energy_source] ?? entry.energy_source}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
