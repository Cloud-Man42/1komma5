import type { VehicleChargeSession } from "@/lib/api";
import {
  formatIsoTime,
  formatPercent,
  formatSek,
  formatSessionDuration,
  sessionEnergyKwh,
} from "./vehicleDashboardHelpers";

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
      <ul className="vdash-history-list">
        {sessions.map((session) => (
          <li key={session.id} className="vdash-history-item">
            <div className="vdash-history-head">
              <strong>{session.status === "ACTIVE" ? "Pågår" : "Avslutad"}</strong>
              <span>{formatIsoTime(session.charging_started_at ?? session.connected_at)}</span>
            </div>
            <dl className="vdash-history-stats">
              <div><dt>Energi</dt><dd>{sessionEnergyKwh(session).toFixed(1)} kWh</dd></div>
              <div>
                <dt>Varaktighet</dt>
                <dd>
                  {formatSessionDuration(
                    session.charging_started_at ?? session.connected_at,
                    session.charging_stopped_at ?? session.disconnected_at,
                  )}
                </dd>
              </div>
              <div><dt>SoC</dt><dd>{formatPercent(session.start_soc)} → {formatPercent(session.end_soc)}</dd></div>
              <div><dt>Förnybar</dt><dd>{session.renewable_share_pct != null ? `${Math.round(session.renewable_share_pct)}%` : "—"}</dd></div>
              <div><dt>Kostnad</dt><dd>{formatSek(session.actual_cost_sek)}</dd></div>
              <div><dt>Besparing</dt><dd>{formatSek(session.savings_sek)}</dd></div>
            </dl>
          </li>
        ))}
      </ul>
    </section>
  );
}
