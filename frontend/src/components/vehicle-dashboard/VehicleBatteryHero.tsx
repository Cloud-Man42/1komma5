import { formatKwh, formatPercent } from "./vehicleDashboardHelpers";

type Props = {
  socPct: number | null;
  energyKwh: number | null;
  capacityKwh: number;
  chargingPowerKw: number | null;
  targetSocPct: number | null;
  startedAt: string;
  isCharging: boolean;
};

export function VehicleBatteryHero({
  socPct,
  energyKwh,
  capacityKwh,
  chargingPowerKw,
  targetSocPct,
  startedAt,
  isCharging,
}: Props) {
  return (
    <section className="vdash-card vdash-battery-card" data-testid="vehicle-battery-card">
      <header className="vdash-card-header">
        <h2>BATTERI</h2>
      </header>
      <div className="vdash-battery-body">
        <div className="vdash-battery-main">
          <div className="vdash-battery-stats">
            <p className="vdash-battery-pct">{formatPercent(socPct)}</p>
            <p className="vdash-battery-kwh">
              {formatKwh(energyKwh)} / {formatKwh(capacityKwh)}
            </p>
            <div className="vdash-battery-bar" aria-hidden="true">
              <span style={{ width: `${socPct ?? 0}%` }} />
            </div>
          </div>
          <div className="vdash-battery-car">
            <div className="vdash-battery-brand">
              <svg viewBox="0 0 32 32" aria-hidden="true" className="vdash-mercedes-star">
                <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeWidth="1.2" />
                <path d="M16 4v24M6 12l20 8M26 12L6 20" fill="none" stroke="currentColor" strokeWidth="1.2" />
              </svg>
              <span>EQE</span>
            </div>
            <img src="/images/vehicle-eqe-profile.png" alt="" className="vdash-battery-car-img" />
          </div>
        </div>
        <footer className="vdash-battery-footer">
          <div className="vdash-battery-stat">
            <span className="vdash-stat-icon vdash-stat-icon-green" aria-hidden="true">⚡</span>
            <div>
              <span className="vdash-stat-label">Laddningseffekt</span>
              <strong>{chargingPowerKw != null ? `${chargingPowerKw.toFixed(1)} kW` : "—"}</strong>
            </div>
          </div>
          <div className="vdash-battery-stat">
            <span className="vdash-stat-icon vdash-stat-icon-green" aria-hidden="true">🔋</span>
            <div>
              <span className="vdash-stat-label">Laddning till</span>
              <strong>{formatPercent(targetSocPct)}</strong>
            </div>
          </div>
          <div className="vdash-battery-stat">
            <span className="vdash-stat-icon vdash-stat-icon-cyan" aria-hidden="true">🕐</span>
            <div>
              <span className="vdash-stat-label">Status</span>
              <strong>{isCharging ? "Laddar" : "Vilar"}</strong>
            </div>
          </div>
          <div className="vdash-battery-stat">
            <span className="vdash-stat-icon vdash-stat-icon-purple" aria-hidden="true">🕐</span>
            <div>
              <span className="vdash-stat-label">Startad</span>
              <strong>{startedAt}</strong>
            </div>
          </div>
        </footer>
      </div>
    </section>
  );
}
