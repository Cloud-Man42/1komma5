"use client";

import { useEffect, useState } from "react";
import { SpaPlan, fetchSpaPlan } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

function formatLocalTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" });
}

export function SpaPlanCard({ siteSlug }: { siteSlug: string }) {
  const [plan, setPlan] = useState<SpaPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchSpaPlan(siteSlug)
      .then(setPlan)
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda plan"));
  }, [siteSlug]);

  if (error) return <p className="form-error">{error}</p>;
  if (!plan) return <p className="muted">Laddar energiplan…</p>;
  if (!plan.enabled) {
    return (
      <section className="card" data-testid="spa-plan-card">
        <h3>Smart energistyrning</h3>
        <p className="muted">Smartstyrning är inte aktiverad.</p>
      </section>
    );
  }

  const qualityLabel = plan.data_quality === "MEASURED" ? "Mätt" : "Beräknad";

  return (
    <section className="card" data-testid="spa-plan-card">
      <h3>Smart energistyrning</h3>
      {plan.dry_run && <p className="muted">Dry Run — inga kommandon skickas till spaet.</p>}

      <div className="spa-kpi-grid">
        <div className="spa-kpi">
          <p className="spa-kpi-value">{formatLocalTime(plan.next_cleaning_start)}</p>
          <p className="spa-kpi-label">Nästa cleaning</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">{plan.duration_hours != null ? `${plan.duration_hours} h` : "—"}</p>
          <p className="spa-kpi-label">Längd</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">{plan.planned_energy_source ?? "—"}</p>
          <p className="spa-kpi-label">Planerad energikälla</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">
            {plan.estimated_energy_kwh != null ? `${plan.estimated_energy_kwh.toFixed(1)} kWh` : "—"}
          </p>
          <p className="spa-kpi-label">Beräknad energi ({qualityLabel})</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">
            {plan.estimated_cost_sek != null ? formatSekAmount(plan.estimated_cost_sek).label : "—"}
          </p>
          <p className="spa-kpi-label">Beräknad kostnad ({qualityLabel})</p>
        </div>
        <div className="spa-kpi">
          <p className="spa-kpi-value">
            {plan.savings_sek != null ? formatSekAmount(plan.savings_sek).label : "—"}
          </p>
          <p className="spa-kpi-label">Besparing mot standardtid</p>
        </div>
      </div>

      {plan.fallback_from_solar_only && (
        <p className="form-warning">
          Cleaning kunde inte genomföras enbart med solel och körs nu för att uppfylla spaets säkerhetskrav.
        </p>
      )}

      {plan.daily_windows && plan.daily_windows.length > 1 && (
        <div className="spa-daily-windows">
          <p className="muted">Dagens plan ({plan.planned_starts ?? plan.daily_windows.length} starter)</p>
          <ul className="spa-cleaning-plan-list">
            {plan.daily_windows.map((window) => (
              <li key={`${window.start}-${window.end}`}>
                <span className="spa-cleaning-plan-time">
                  {formatLocalTime(window.start)}–{formatLocalTime(window.end)}
                </span>
                <span className="spa-cleaning-plan-duration">{window.duration_hours} h</span>
                <span className="spa-cleaning-plan-source">{window.energy_source_label_sv}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button type="button" className="btn-secondary" onClick={() => setExpanded((v) => !v)}>
        Varför valde EMIC denna tid?
      </button>
      {expanded && <p className="spa-explanation">{plan.explanation_sv || "Ingen förklaring tillgänglig."}</p>}
    </section>
  );
}
