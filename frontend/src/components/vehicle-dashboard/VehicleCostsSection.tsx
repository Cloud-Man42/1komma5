import type { VehicleChargeSession } from "@/lib/api";
import { formatSek, sessionEnergyKwh } from "./vehicleDashboardHelpers";
import { VehicleConsumptionPanel } from "./VehicleConsumptionPanel";

export function VehicleCostsSection({
  sessions,
  bars,
  avgRenewableSharePct,
  totalEnergyKwh,
  totalSavingsKr,
}: {
  sessions: VehicleChargeSession[];
  bars: number[];
  avgRenewableSharePct: number | null;
  totalEnergyKwh: number;
  totalSavingsKr: number;
}) {
  const totalCost = sessions.reduce((sum, s) => sum + (s.actual_cost_sek ?? 0), 0);
  const totalReference = sessions.reduce((sum, s) => sum + (s.reference_cost_sek ?? 0), 0);

  return (
    <section className="vdash-section" data-testid="vehicle-section-costs">
      <h2 className="vdash-section-title">Kostnad &amp; analys</h2>
      <div className="vdash-costs-summary">
        <div className="vdash-chip-card">
          <span className="vdash-chip-label">Total kostnad</span>
          <strong className="vdash-chip-value">{formatSek(totalCost)}</strong>
        </div>
        <div className="vdash-chip-card">
          <span className="vdash-chip-label">Referenskostnad</span>
          <strong className="vdash-chip-value">{formatSek(totalReference)}</strong>
        </div>
        <div className="vdash-chip-card">
          <span className="vdash-chip-label">Total besparing</span>
          <strong className="vdash-chip-value vdash-chip-value-green">{formatSek(totalSavingsKr)}</strong>
        </div>
        <div className="vdash-chip-card">
          <span className="vdash-chip-label">Total energi</span>
          <strong className="vdash-chip-value">{totalEnergyKwh.toFixed(1)} kWh</strong>
        </div>
      </div>
      <VehicleConsumptionPanel
        bars={bars}
        avgRenewableSharePct={avgRenewableSharePct}
        totalEnergyKwh={totalEnergyKwh}
      />
      {sessions.length > 0 ? (
        <div className="vdash-card">
          <header className="vdash-card-header">
            <h2>ENERGIKÄLLOR PER SESSION</h2>
          </header>
          <ul className="vdash-source-list">
            {sessions.slice(0, 10).map((session) => (
              <li key={session.id}>
                <span>{formatSek(session.actual_cost_sek)} · {sessionEnergyKwh(session).toFixed(1)} kWh</span>
                <span className="vdash-muted">
                  Sol {(session.energy_sources.solar_direct_kwh ?? 0).toFixed(1)} ·
                  Nät {(session.energy_sources.grid_direct_kwh ?? 0).toFixed(1)} kWh
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
