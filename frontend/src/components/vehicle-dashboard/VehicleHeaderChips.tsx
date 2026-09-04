import { formatPercent, formatKw } from "./vehicleDashboardHelpers";

type Props = {
  rangeKm: number | null;
  targetSocPct: number | null;
  isPluggedIn: boolean | null | undefined;
  isCharging: boolean | null | undefined;
  chargingPowerKw: number | null;
  freshnessLabel: string;
  locationTitle?: string | null;
  locationSubtitle?: string | null;
};

export function VehicleHeaderChips({
  rangeKm,
  targetSocPct,
  isPluggedIn,
  isCharging,
  chargingPowerKw,
  freshnessLabel,
  locationTitle,
  locationSubtitle,
}: Props) {
  return (
    <div className="vdash-chips-grid" data-testid="vehicle-header-chips">
      <div className="vdash-chip-card">
        <span className="vdash-chip-label">Räckvidd (est.)</span>
        <strong className="vdash-chip-value">
          {rangeKm != null ? `${Math.round(rangeKm)} km` : "—"}
        </strong>
        <p className="vdash-chip-meta">Från Mercedes me</p>
      </div>

      <div className="vdash-chip-card">
        <span className="vdash-chip-label">Mål-SoC</span>
        <strong className="vdash-chip-value">{formatPercent(targetSocPct)}</strong>
        <div className="vdash-temp-slider" aria-hidden="true">
          <span className="vdash-temp-track" style={{ width: `${targetSocPct ?? 0}%` }} />
        </div>
      </div>

      <div className="vdash-chip-card vdash-chip-status">
        <span className="vdash-chip-label">Laddkabel</span>
        <strong className={`vdash-chip-value ${isPluggedIn ? "vdash-chip-value-green" : ""}`.trim()}>
          {isPluggedIn == null ? "—" : isPluggedIn ? "Ansluten" : "Frånkopplad"}
        </strong>
      </div>

      <div className="vdash-chip-card vdash-chip-status">
        <span className="vdash-chip-label">{isCharging ? "Laddar" : "Datastatus"}</span>
        <strong className={`vdash-chip-value ${isCharging ? "vdash-chip-value-green" : ""}`.trim()}>
          {isCharging ? formatKw(chargingPowerKw) : freshnessLabel}
        </strong>
      </div>
      <div className="vdash-chip-card vdash-chip-status">
        <span className="vdash-chip-label">Position</span>
        <strong className="vdash-chip-value">
          {locationTitle ?? "—"}
        </strong>
        {locationSubtitle ? <p className="vdash-chip-meta">{locationSubtitle}</p> : null}
      </div>
    </div>
  );
}
