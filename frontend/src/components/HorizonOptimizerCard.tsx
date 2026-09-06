import type { HorizonOptimizerPlan } from "../lib/api";
import {
  energySourceLabelSv,
  formatSek,
  formatTimeWindow,
  loadTypeLabelSv,
} from "./intelligence-dashboard/advisorFormatters";

interface HorizonOptimizerCardProps {
  plan: HorizonOptimizerPlan;
}

export function HorizonOptimizerCard({ plan }: HorizonOptimizerCardProps) {
  return (
    <section className="idash-horizon-card" data-testid="horizon-optimizer-card">
      <header className="idash-horizon-header">
        <div>
          <h2>HORIZON OPTIMIZER</h2>
          <p className="idash-horizon-meta">
            {plan.horizon_hours}h horisont · {plan.horizon_blocks} block
          </p>
        </div>
        {plan.monitor_only ? (
          <span className="idash-advisor-badge">Endast övervakning</span>
        ) : null}
      </header>

      {plan.available ? (
        <>
          <div className="idash-horizon-summary">
            <strong>{plan.headline_sv ?? "Horizon-plan"}</strong>
            {plan.summary_sv ? <p>{plan.summary_sv}</p> : null}
            {plan.total_planned_savings_sek != null ? (
              <p className="idash-horizon-savings">
                Total planerad besparing:{" "}
                <strong>{formatSek(plan.total_planned_savings_sek)}</strong>
              </p>
            ) : null}
          </div>

          {plan.loads.length > 0 ? (
            <div className="idash-horizon-load-list">
              {plan.loads.map((load) => {
                const sourceLabel = energySourceLabelSv(load.expected_energy_source);
                return (
                  <article key={load.load_id} className="idash-horizon-load-card">
                    <div className="idash-horizon-load-head">
                      <strong>{load.name}</strong>
                      <span className="idash-horizon-load-type">{loadTypeLabelSv(load.load_type)}</span>
                    </div>
                    <p className="idash-horizon-load-window">
                      {formatTimeWindow(load.window_start, load.window_end, plan.timezone)}
                    </p>
                    <p className="idash-horizon-load-detail">
                      Besparing: <strong>{formatSek(load.savings_sek)}</strong>
                      {load.expected_energy_kwh != null
                        ? ` · ${load.expected_energy_kwh.toFixed(1)} kWh`
                        : null}
                      {sourceLabel ? ` · ${sourceLabel}` : null}
                    </p>
                    {load.explanation_sv ? (
                      <p className="idash-horizon-load-detail">{load.explanation_sv}</p>
                    ) : null}
                  </article>
                );
              })}
            </div>
          ) : null}

          {plan.battery?.available && plan.battery.headline_sv ? (
            <div className="idash-horizon-battery">
              <p className="idash-horizon-battery-label">BATTERI I PLANEN</p>
              <strong>{plan.battery.headline_sv}</strong>
              {plan.battery.reason_sv ? <p>{plan.battery.reason_sv}</p> : null}
            </div>
          ) : null}
        </>
      ) : (
        <p className="idash-horizon-empty">
          {plan.unavailable_reason_sv ?? "Horizon-plan är inte tillgänglig just nu."}
        </p>
      )}
    </section>
  );
}
