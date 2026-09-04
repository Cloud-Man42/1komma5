"use client";

import { useEffect, useState } from "react";
import type { EnergyControlAction } from "@/lib/api";
import { fetchEnergyControlRecent } from "@/lib/api";

function formatWhen(iso: string, timezone: string): string {
  return new Date(iso).toLocaleString("sv-SE", {
    timeZone: timezone,
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function EnergyControlTimelineCard({ slug, timezone }: { slug: string; timezone: string }) {
  const [actions, setActions] = useState<EnergyControlAction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchEnergyControlRecent(slug, 8)
      .then((data) => {
        if (active) {
          setActions(data.actions);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setActions([]);
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
    <section className="idash-panel" data-testid="energy-control-timeline-card">
      <h2 className="idash-panel-title">ENERGISTYRNING</h2>
      {loading ? (
        <p className="idash-muted">Laddar händelser…</p>
      ) : error ? (
        <p className="idash-muted">Kunde inte hämta styrningslogg.</p>
      ) : actions.length === 0 ? (
        <p className="idash-muted">Inga loggade styrningsåtgärder ännu.</p>
      ) : (
        <ol className="idash-timeline-list">
          {actions.map((action) => (
            <li key={action.id} className="idash-timeline-item">
              <div className="idash-timeline-head">
                <strong>{action.action}</strong>
                <span>{action.outcome}</span>
              </div>
              <p className="idash-muted">
                {formatWhen(action.recorded_at, timezone)} · {action.optimization_mode} · {action.target}
                {action.dry_run ? " · torrkörning" : ""}
              </p>
              {action.reason ? <p className="idash-timeline-reason">{action.reason}</p> : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
