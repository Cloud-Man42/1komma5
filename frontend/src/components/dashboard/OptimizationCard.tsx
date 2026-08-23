import { DashboardOptimizationSection } from "@/lib/api";
import { formatPercent } from "@/lib/format";
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
          {optimization.solar_first != null && (
            <div>
              <dt>Energikälla</dt>
              <dd>{optimization.solar_first ? "Solel först" : "Nät vid billiga timmar"}</dd>
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
