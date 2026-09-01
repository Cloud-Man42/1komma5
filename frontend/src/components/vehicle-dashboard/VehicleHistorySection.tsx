import type { VehicleChargeSession } from "@/lib/api";
import {
  formatIsoTime,
  formatPercent,
  formatSek,
  formatSessionDuration,
  sessionEnergyEstimated,
  sessionEnergyKwh,
  sessionLocationSubtitle,
  sessionLocationTitle,
} from "./vehicleDashboardHelpers";

function sessionTypeLabel(session: VehicleChargeSession): string {
  if (session.home_charging) return "Hemma";
  return "Borta";
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
      <ul className="vdash-history-list">
        {sessions.map((session) => {
          const energy = sessionEnergyKwh(session);
          const estimated = sessionEnergyEstimated(session);
          const startedAt = session.charging_started_at ?? session.connected_at;
          const endedAt = session.charging_stopped_at ?? session.disconnected_at;
          const subtitle = sessionLocationSubtitle(session);
          const cost = session.charging_cost_sek ?? session.actual_cost_sek;
          const savings = session.savings_sek;
          const showTechnical =
            session.identification_method ||
            session.station_provider ||
            session.detection_confidence;

          return (
            <li key={session.id} className="vdash-history-item" data-testid="vehicle-history-item">
              <div className="vdash-history-head">
                <div className="vdash-history-title-block">
                  <strong className="vdash-history-location">{sessionLocationTitle(session)}</strong>
                  {subtitle ? <span className="vdash-history-meta">{subtitle}</span> : null}
                </div>
                <div className="vdash-history-badges">
                  <span className={`vdash-history-badge ${session.home_charging ? "vdash-history-badge-home" : "vdash-history-badge-away"}`}>
                    {sessionTypeLabel(session)}
                  </span>
                  <time className="vdash-history-date" dateTime={session.connected_at}>
                    {formatIsoTime(session.connected_at)}
                  </time>
                </div>
              </div>

              <dl className="vdash-history-stats">
                <div>
                  <dt>Batteri</dt>
                  <dd>
                    {formatPercent(session.start_soc)} → {formatPercent(session.end_soc)}
                  </dd>
                </div>
                <div>
                  <dt>Energi</dt>
                  <dd>
                    {energy > 0 ? `${energy.toFixed(1)} kWh` : "—"}
                    {estimated && energy > 0 ? <span className="vdash-history-est"> est.</span> : null}
                  </dd>
                </div>
                <div>
                  <dt>Kostnad</dt>
                  <dd>{formatSek(cost)}</dd>
                </div>
                <div>
                  <dt>Tid</dt>
                  <dd>{formatSessionDuration(startedAt, endedAt)}</dd>
                </div>
              </dl>

              <div className="vdash-history-foot">
                <span>
                  {formatIsoTime(startedAt)} – {formatIsoTime(endedAt)}
                </span>
                {session.charging_power_avg_kw != null ? (
                  <span>{session.charging_power_avg_kw.toFixed(1)} kW snitt</span>
                ) : null}
                {savings != null && savings > 0 ? (
                  <span className="vdash-history-savings">Sparade {formatSek(savings)}</span>
                ) : null}
              </div>

              {showTechnical ? (
                <details className="vdash-history-details">
                  <summary>Teknisk info</summary>
                  <dl className="vdash-history-details-grid">
                    {session.identification_method ? (
                      <>
                        <dt>Identifiering</dt>
                        <dd>{session.identification_method.replaceAll("_", " ")}</dd>
                      </>
                    ) : null}
                    {session.station_provider ?? session.station_provider_id ? (
                      <>
                        <dt>Källa</dt>
                        <dd>{session.station_provider ?? session.station_provider_id}</dd>
                      </>
                    ) : null}
                    {session.detection_confidence ? (
                      <>
                        <dt>Tillförlitlighet</dt>
                        <dd>
                          {session.detection_confidence.replaceAll("_", " ")}
                          {session.station_confidence != null ? ` (${session.station_confidence})` : ""}
                        </dd>
                      </>
                    ) : null}
                    {session.energy_source ?? session.energy_quality ? (
                      <>
                        <dt>Energi källa</dt>
                        <dd>{session.energy_source ?? session.energy_quality}</dd>
                      </>
                    ) : null}
                  </dl>
                </details>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
