import { DashboardOptimizationSection } from "@/lib/api";
import { formatEnergy, formatPercent } from "@/lib/format";
import { DashboardSection } from "@/components/dashboard";

export function OptimizationCard({
  optimization,
}: {
  optimization: DashboardOptimizationSection | null;
}) {
  if (!optimization) return null;

  const steps = optimization.reasoning_steps ?? [];

  return (
    <DashboardSection title="EMIC-optimering" subtitle="Vad systemet gör just nu">
      <div className="dashboard-surface">
        <p className="detail-card-value">{optimization.strategy_sv ?? "—"}</p>
        {optimization.explanation_sv && (
          <p className="detail-card-meta">{optimization.explanation_sv}</p>
        )}
        {steps.length > 0 && (
          <div style={{ marginTop: "var(--space-4)" }}>
            <p className="detail-card-meta">
              <strong>Så resonerar EMIC</strong>
            </p>
            <ol className="reasoning-steps" data-testid="optimization-reasoning-steps">
              {steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        )}
        <dl className="metrics" style={{ marginTop: "var(--space-4)" }}>
          {optimization.reserved_solar_kwh != null && (
            <div>
              <dt>Reserverad solel</dt>
              <dd>{formatEnergy(optimization.reserved_solar_kwh)}</dd>
            </div>
          )}
          {optimization.planned_grid_kwh != null && (
            <div>
              <dt>Planerad nätenergi</dt>
              <dd>{formatEnergy(optimization.planned_grid_kwh)}</dd>
            </div>
          )}
          {optimization.ev_need_kwh != null && (
            <div>
              <dt>EV-behov</dt>
              <dd>{formatEnergy(optimization.ev_need_kwh)}</dd>
            </div>
          )}
          {optimization.battery_soc_pct != null && (
            <div>
              <dt>Batteri</dt>
              <dd>{formatPercent(optimization.battery_soc_pct)}</dd>
            </div>
          )}
        </dl>
      </div>
    </DashboardSection>
  );
}
