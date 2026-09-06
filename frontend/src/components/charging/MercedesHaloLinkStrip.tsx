"use client";

import type { EnergyReasoning, EvBridgeStatus } from "@/lib/api";
import { formatEvCurrent } from "@/components/ev-dashboard/evDashboardHelpers";

function smartChargingStateLabel(state: string | null | undefined): string {
  switch (state) {
    case "charging":
      return "Laddar";
    case "waiting":
      return "Väntar";
    case "paused":
      return "Pausad";
    case "override":
      return "Manuell override";
    default:
      return state ?? "—";
  }
}

export function MercedesHaloLinkStrip({
  reasoning,
  bridge,
  testId = "mercedes-halo-link-strip",
}: {
  reasoning: EnergyReasoning | null;
  bridge?: EvBridgeStatus | null;
  testId?: string;
}) {
  if (!reasoning?.vehicle_linked && !bridge?.bridge_enabled) {
    return null;
  }

  const haloStatus =
    reasoning?.display_status_sv ??
    bridge?.display_status_sv ??
    smartChargingStateLabel(reasoning?.smart_charging_state ?? bridge?.smart_charging_state);
  const vehicleConnected = reasoning?.vehicle_connected ?? bridge?.vehicle_connected;
  const haloConnected = reasoning?.halo_connected ?? bridge?.halo_connected;
  const appliedCurrent = reasoning?.applied_current_a ?? bridge?.applied_current_a;

  return (
    <section className="evdash-mercedes-halo-strip" data-testid={testId}>
      {reasoning?.vehicle_linked ? (
        <article className="evdash-strip-card">
          <p className="evdash-chip-label">MERCEDES</p>
          <strong>{reasoning.vehicle_display_name ?? "Länkad bil"}</strong>
          <ul className="evdash-strip-meta">
            {reasoning.vehicle_soc_pct != null ? (
              <li>
                SOC {Math.round(reasoning.vehicle_soc_pct)}%
                {reasoning.vehicle_target_soc_pct != null
                  ? ` → ${Math.round(reasoning.vehicle_target_soc_pct)}%`
                  : ""}
              </li>
            ) : null}
            {reasoning.vehicle_departure_time ? (
              <li>Avfärd {reasoning.vehicle_departure_time}</li>
            ) : null}
            {reasoning.vehicle_required_energy_kwh != null ? (
              <li>Behöver ~{reasoning.vehicle_required_energy_kwh.toFixed(1)} kWh</li>
            ) : null}
          </ul>
        </article>
      ) : null}
      <article className="evdash-strip-card">
        <p className="evdash-chip-label">CHARGE AMPS HALO</p>
        <strong>{haloStatus}</strong>
        <ul className="evdash-strip-meta">
          <li>{haloConnected ? "Halo online" : "Halo offline"}</li>
          <li>{vehicleConnected ? "Bil ansluten" : "Ingen bil ansluten"}</li>
          {appliedCurrent != null ? <li>Ström {formatEvCurrent(appliedCurrent)}</li> : null}
          {reasoning?.decision_reason_sv ? <li>{reasoning.decision_reason_sv}</li> : null}
        </ul>
      </article>
    </section>
  );
}

/** @deprecated Use MercedesHaloLinkStrip */
export const EvMercedesHaloStrip = MercedesHaloLinkStrip;
