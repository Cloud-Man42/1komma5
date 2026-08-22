import { DashboardOptimizationSection } from "@/lib/api";
import { formatEnergy, formatPercent } from "@/lib/format";
import { DashboardSection } from "@/components/dashboard";

export function OptimizationCard({
  optimization,
}: {
  optimization: DashboardOptimizationSection | null;
}) {
  if (!optimization) return null;

  return (
    <DashboardSection title="EMIC-optimering" subtitle="Vad systemet gör just nu">
      <div className="dashboard-surface">
        <p className="detail-card-value">{optimization.strategy_sv ?? "—"}</p>
        {optimization.explanation_sv && (
          <p className="detail-card-meta">
            <strong>Varför?</strong> {optimization.explanation_sv}
          </p>
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
