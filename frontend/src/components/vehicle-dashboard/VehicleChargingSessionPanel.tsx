import type { VehicleChargeSession } from "@/lib/api";
import { formatPercent, formatSek, totalRenewableKwh } from "./vehicleDashboardHelpers";

type Props = {
  subtitle: string;
  session: VehicleChargeSession | null;
  chargingPowerKw: number | null;
  onStop: () => void;
  onStart: () => void;
  stopping: boolean;
  starting: boolean;
  canStop: boolean;
  canStart: boolean;
};

function chartPointsFromPower(powerKw: number | null): string {
  const base = powerKw ?? 0;
  const max = Math.max(base, 1);
  const points: string[] = [];
  for (let i = 0; i <= 12; i++) {
    const x = i * 8;
    const variance = Math.sin(i * 0.8) * 0.15 + 1;
    const y = 60 - (base * variance / max) * 34;
    points.push(`${x},${y.toFixed(1)}`);
  }
  return points.join(" ");
}

export function VehicleChargingSessionPanel({
  subtitle,
  session,
  chargingPowerKw,
  onStop,
  onStart,
  stopping,
  starting,
  canStop,
  canStart,
}: Props) {
  const chargedKwh =
    session?.halo_energy_kwh ?? session?.estimated_battery_energy_delta_kwh ?? 0;
  const costKr = session?.actual_cost_sek;
  const surplus =
    session?.renewable_share_pct != null
      ? `${Math.round(session.renewable_share_pct)}% förnybar`
      : "—";
  const co2 = totalRenewableKwh(session) * 0.15;
  const chartPoints = chartPointsFromPower(chargingPowerKw);

  return (
    <section className="vdash-card vdash-session-card" id="laddning" data-testid="vehicle-charging-session">
      <header className="vdash-card-header vdash-card-header-row">
        <div>
          <h2>LADDSESSION</h2>
          <p className="vdash-card-sub">{subtitle}</p>
        </div>
      </header>
      {session ? (
        <>
          <div className="vdash-session-chart-wrap">
            <svg viewBox="0 0 96 60" className="vdash-session-chart" aria-hidden="true">
              <defs>
                <linearGradient id="vdashSessionFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00E676" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#00E676" stopOpacity="0" />
                </linearGradient>
              </defs>
              <line x1="0" y1="20" x2="96" y2="20" stroke="rgba(148,163,184,0.25)" strokeDasharray="2 2" />
              <polygon points={`0,60 ${chartPoints} 96,60`} fill="url(#vdashSessionFill)" />
              <polyline points={chartPoints} fill="none" stroke="#00E676" strokeWidth="1.4" />
            </svg>
            <div className="vdash-session-stats">
              <span>Laddat: {chargedKwh.toFixed(1)} kWh</span>
              <span>SoC {formatPercent(session.start_soc)} → {formatPercent(session.end_soc)}</span>
              <span>Kostnad: {formatSek(costKr)} ({surplus})</span>
              <span>CO₂ besparing: {co2.toFixed(1)} kg</span>
            </div>
            <div className="vdash-session-sources">
              <span>Sol direkt: {(session.energy_sources.solar_direct_kwh ?? 0).toFixed(1)} kWh</span>
              <span>Sol via batteri: {(session.energy_sources.solar_battery_kwh ?? 0).toFixed(1)} kWh</span>
              <span>Nät: {(session.energy_sources.grid_direct_kwh ?? 0).toFixed(1)} kWh</span>
            </div>
            {(session.station_name || session.charger_operator || session.station_resolution_status) ? (
              <div className="vdash-session-station" data-testid="vehicle-session-station">
                {session.station_name || session.location_name ? (
                  <span>Station: {session.station_name ?? session.location_name}</span>
                ) : null}
                {session.charger_operator ? <span>Operatör: {session.charger_operator}</span> : null}
                {session.charging_type ? <span>{session.charging_type}{session.charging_power_avg_kw ? ` · ${session.charging_power_avg_kw.toFixed(1)} kW` : ""}</span> : null}
                {session.distance_from_vehicle_m != null ? <span>{Math.round(session.distance_from_vehicle_m)} m</span> : null}
                {session.detection_confidence ? <span>Confidence: {session.detection_confidence}</span> : null}
                {session.station_resolution_status === "MULTIPLE_CANDIDATES" && session.station_candidates?.length ? (
                  <ul>
                    {session.station_candidates.map((c) => (
                      <li key={c.provider_station_id ?? c.label}>{c.label}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
          <div className="vdash-session-actions">
            <button
              type="button"
              className="vdash-stop-btn"
              onClick={onStop}
              disabled={!canStop || stopping}
            >
              {stopping ? "Stoppar…" : "Stoppa laddning"}
            </button>
            <button
              type="button"
              className="vdash-start-btn"
              onClick={onStart}
              disabled={!canStart || starting}
            >
              {starting ? "Startar…" : "Starta laddning"}
            </button>
          </div>
        </>
      ) : (
        <p className="vdash-muted">Ingen aktiv laddsession.</p>
      )}
    </section>
  );
}
