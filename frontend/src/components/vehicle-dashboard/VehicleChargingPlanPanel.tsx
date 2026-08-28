import { formatIsoTime } from "./vehicleDashboardHelpers";

export function VehicleChargingPlanPanel({
  targetSocPct,
  departureTime,
  requiredEnergyKwh,
  planReasonSv,
  smartChargingState,
  onEditTargetSoc,
}: {
  targetSocPct: number | null;
  departureTime: string | null;
  requiredEnergyKwh: number | null;
  planReasonSv: string | null;
  smartChargingState: string | null;
  onEditTargetSoc: () => void;
}) {
  const centerLabel = departureTime
    ? `Avgång ${formatIsoTime(departureTime)}`
    : targetSocPct != null
      ? `Mål ${Math.round(targetSocPct)}%`
      : "Ingen plan";

  return (
    <section className="vdash-card" id="schema" data-testid="vehicle-charging-plan">
      <header className="vdash-card-header">
        <div>
          <h2>LADDPLAN</h2>
          <p className="vdash-card-sub">Optimera laddning med EMIC</p>
        </div>
      </header>
      <div className="vdash-donut-wrap">
        <div
          className="vdash-donut"
          aria-hidden="true"
          style={{
            background: `conic-gradient(
              #00E676 0deg ${targetSocPct ?? 50}deg,
              #38bdf8 ${targetSocPct ?? 50}deg 220deg,
              #a78bfa 220deg 360deg
            )`,
          }}
        >
          <div className="vdash-donut-center">
            <span className="vdash-donut-label">Smart laddning</span>
            <strong>{centerLabel}</strong>
          </div>
        </div>
        <ul className="vdash-donut-legend">
          <li><span className="vdash-dot vdash-dot-green" />Mål-SoC: {targetSocPct != null ? `${Math.round(targetSocPct)}%` : "—"}</li>
          <li><span className="vdash-dot vdash-dot-blue" />Behov: {requiredEnergyKwh != null ? `${requiredEnergyKwh.toFixed(1)} kWh` : "—"}</li>
          <li><span className="vdash-dot vdash-dot-purple" />Läge: {smartChargingState ?? "—"}</li>
        </ul>
      </div>
      {planReasonSv ? <p className="vdash-muted">{planReasonSv}</p> : null}
      <button type="button" className="vdash-card-btn" onClick={onEditTargetSoc}>
        Redigera mål-SoC
      </button>
    </section>
  );
}
