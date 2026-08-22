import { DashboardTodaySection } from "@/lib/api";
import { formatEnergy, formatMoney } from "@/lib/format";
import { DashboardSection, MetricGroup, Metric } from "@/components/dashboard";

export function TodaySection({ today }: { today: DashboardTodaySection | null }) {
  if (!today) return null;

  if (today.unavailable_reason) {
    return (
      <DashboardSection title="Idag">
        <p className="muted">{today.unavailable_reason}</p>
      </DashboardSection>
    );
  }

  return (
    <DashboardSection title="Idag" subtitle="Dagens energi och kostnad">
      <div className="dashboard-surface">
        <MetricGroup>
          <Metric label="Producerat" value={formatEnergy(today.produced_kwh)} />
          <Metric label="Förbrukat" value={formatEnergy(today.consumed_kwh)} />
          <Metric label="Köpt från nät" value={formatEnergy(today.imported_kwh)} />
          <Metric label="Sålt till nät" value={formatEnergy(today.exported_kwh)} />
          <Metric label="Energikostnad" value={formatMoney(today.energy_cost_sek)} />
          <Metric
            label="Besparing"
            value={formatMoney(today.savings_sek)}
            hint="Jämfört med direkt nät-laddning/förbrukning"
          />
        </MetricGroup>
      </div>
    </DashboardSection>
  );
}
