import type { VehicleChargeSession } from "@/lib/api";
import {
  formatIsoTime,
  formatPercent,
  formatSek,
  formatSessionDuration,
  sessionEnergyKwh,
} from "./vehicleDashboardHelpers";

function formatConfidence(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replace("_", " ");
}

export function VehicleHistorySection({ sessions }: { sessions: VehicleChargeSession[] }) {
  if (sessions.length === 0) {
    return (
      <section className="vdash-section" data-testid="vehicle-section-history">
        <h2 className="vdash-section-title">Laddhistorik</h2>
        <p className="vdash-muted">Ingen laddhistorik registrerad ännu.</p>
      </section>
    );
  }

  return (
    <section className="vdash-section" data-testid="vehicle-section-history">
      <h2 className="vdash-section-title">Laddhistorik</h2>
      <p className="vdash-section-sub">{sessions.length} sessioner</p>
      <div className="vdash-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Datum</th>
              <th>Plats</th>
              <th>Station</th>
              <th>Operatör</th>
              <th>Typ</th>
              <th>Källa</th>
              <th>Confidence</th>
              <th>Start</th>
              <th>Slut</th>
              <th>SoC</th>
              <th>Energi</th>
              <th>Kostnad</th>
              <th>Effekt</th>
              <th>Källa</th>
              <th>Energi källa</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => {
              const energy = sessionEnergyKwh(session);
              const estimated = session.energy_quality === "ESTIMATED" || session.vehicle_data_quality === "STALE";
              return (
                <tr key={session.id}>
                  <td>{formatIsoTime(session.connected_at)}</td>
                  <td>{session.location_name ?? (session.home_charging ? "Hemma" : "—")}</td>
                  <td>{session.station_name ?? "—"}</td>
                  <td>{session.charger_operator ?? "—"}</td>
                  <td>{session.charging_type ?? "—"}</td>
                  <td>{session.station_provider ?? session.station_provider_id ?? "—"}</td>
                  <td>{formatConfidence(session.detection_confidence)}{session.station_confidence != null ? ` (${session.station_confidence})` : ""}</td>
                  <td>{formatIsoTime(session.charging_started_at ?? session.connected_at)}</td>
                  <td>{formatIsoTime(session.charging_stopped_at ?? session.disconnected_at)}</td>
                  <td>{formatPercent(session.start_soc)} → {formatPercent(session.end_soc)}</td>
                  <td>{energy.toFixed(1)} kWh{estimated ? " (est.)" : ""}</td>
                  <td>{formatSek(session.charging_cost_sek ?? session.actual_cost_sek)}</td>
                  <td>{session.charging_power_avg_kw != null ? `${session.charging_power_avg_kw.toFixed(1)} kW` : "—"}</td>
                  <td>{session.identification_method ?? "—"}</td>
                  <td>{session.energy_source ?? session.energy_quality ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
