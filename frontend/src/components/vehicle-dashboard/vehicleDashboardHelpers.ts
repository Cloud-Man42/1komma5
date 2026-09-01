import type {
  EnergyReasoning,
  VehicleChargeSession,
  VehicleIntegrationStatus,
  VehicleListItem,
  VehicleValueEnvelope,
} from "@/lib/api";

/** Mercedes EQE 500 usable battery capacity (kWh). */
export const EQE_USABLE_KWH = 90.6;

export function formatKm(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value).toLocaleString("sv-SE")} km`;
}

export function formatKwh(value: number | null | undefined, digits = 1): string {
  if (value == null) return "—";
  return `${value.toFixed(digits)} kWh`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value)}%`;
}

export function formatKw(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)} kW`;
}

export function formatSek(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(2)} kr`;
}

export function formatIsoTime(iso: string | null | undefined, timezone = "Europe/Stockholm"): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    day: "numeric",
    month: "short",
    timeZone: timezone,
  });
}

export function formatSessionDuration(startIso: string | null, endIso: string | null): string {
  if (!startIso) return "—";
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  const minutes = Math.max(0, Math.round((end - start) / 60000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rem = minutes % 60;
  return rem > 0 ? `${hours} h ${rem} min` : `${hours} h`;
}

export function estimateCo2SavedKg(renewableKwh: number): number {
  return renewableKwh * 0.15;
}

export function totalRenewableKwh(session: VehicleChargeSession | null): number {
  if (!session) return 0;
  const src = session.energy_sources;
  return (src.solar_direct_kwh ?? 0) + (src.solar_battery_kwh ?? 0);
}

export function surplusLabel(session: VehicleChargeSession | null): string {
  if (session?.renewable_share_pct != null) {
    return `${Math.round(session.renewable_share_pct)}% förnybar`;
  }
  return "—";
}

export function chargingSubtitle(
  vehicle: VehicleListItem | null,
  session: VehicleChargeSession | null,
  reasoning: EnergyReasoning | null,
): string {
  if (reasoning?.decision_reason_sv) return reasoning.decision_reason_sv;
  if (vehicle?.freshness_label === "INAKTUELL" || vehicle?.freshness_label === "OFFLINE") {
    return "Ingen färsk fordonsdata från Mercedes me";
  }
  if (vehicle?.is_charging) {
    if (session && totalRenewableKwh(session) > 0) return "Laddar med överskott från solen";
    return "Laddning pågår";
  }
  if (vehicle?.is_plugged_in) return "Ansluten, laddar inte";
  return "Ingen aktiv laddning";
}

export function connectionLabel(state: string | null | undefined): string {
  switch (state) {
    case "CONNECTED":
      return "Uppkopplad";
    case "DEGRADED":
      return "Degraderad";
    case "BACKOFF":
      return "Backoff";
    case "DISCONNECTED":
      return "Frånkopplad";
    default:
      return state ?? "Okänd";
  }
}

export function healthLabelSv(health: string | null | undefined): string {
  switch (health) {
    case "HEALTHY":
      return "Utmärkt";
    case "DEGRADED":
      return "Nedsatt";
    case "UNHEALTHY":
      return "Problem";
    default:
      return health ?? "—";
  }
}

export function capabilityLabelSv(value: boolean | null | undefined): string {
  if (value === true) return "Tillgänglig";
  if (value === false) return "Ej tillgänglig";
  return "Okänd";
}

export function lastCompletedSession(sessions: VehicleChargeSession[]): VehicleChargeSession | null {
  return (
    sessions.find((s) => s.status !== "ACTIVE" && s.charging_stopped_at) ??
    sessions.find((s) => s.status !== "ACTIVE") ??
    null
  );
}

export function sessionEnergyKwh(session: VehicleChargeSession): number {
  const measured = session.halo_energy_kwh ?? 0;
  const estimated = session.estimated_battery_energy_delta_kwh ?? 0;
  if (measured > 0) return measured;
  if (estimated > 0) return estimated;
  return 0;
}

export function recentSessionEnergyBars(sessions: VehicleChargeSession[], count = 7): number[] {
  const values = sessions
    .slice(0, count)
    .map((s) => sessionEnergyKwh(s))
    .filter((v) => v > 0);
  if (values.length === 0) return [];
  const max = Math.max(...values);
  return values.map((v) => Math.round((v / max) * 100));
}

export function averageRenewableSharePct(sessions: VehicleChargeSession[]): number | null {
  const shares = sessions
    .map((s) => s.renewable_share_pct)
    .filter((v): v is number => v != null);
  if (shares.length === 0) return null;
  return shares.reduce((a, b) => a + b, 0) / shares.length;
}

/**
 * Pick the first target SoC worth showing.
 *
 * The EQE reports 0 % when it cannot read a charge limit at all, and a plain
 * `??` chain lets that 0 win over a real target from the session or the plan.
 * A target of 0 % is never a real goal, so treat it as unknown.
 */
export function resolveTargetSocPct(
  vehicle: VehicleListItem | null,
  session: VehicleChargeSession | null,
  reasoning: EnergyReasoning | null,
): number | null {
  const fromVehicle = vehicle?.capabilities?.can_read_target_soc
    ? vehicle?.target_soc_percent
    : null;
  for (const candidate of [fromVehicle, session?.target_soc, reasoning?.vehicle_target_soc_pct]) {
    if (candidate != null && candidate > 0) return candidate;
  }
  return null;
}

function envelopeNumber(envelope?: VehicleValueEnvelope | null): number | null {
  if (envelope?.value == null || envelope.quality === "UNAVAILABLE") return null;
  return typeof envelope.value === "number" ? envelope.value : null;
}

export function buildVehicleDisplay({
  vehicle,
  session,
  sessions,
  integration,
  reasoning,
  refreshIntervalSec,
  siteSlug,
}: {
  vehicle: VehicleListItem | null;
  session: VehicleChargeSession | null;
  sessions: VehicleChargeSession[];
  integration: VehicleIntegrationStatus | null;
  reasoning: EnergyReasoning | null;
  refreshIntervalSec: number;
  siteSlug: string;
}) {
  const soc = vehicle?.state_of_charge_percent ?? envelopeNumber(vehicle?.state_of_charge) ?? null;
  const capacity = EQE_USABLE_KWH;
  const energyKwh = soc != null ? (capacity * soc) / 100 : null;
  const completed = lastCompletedSession(sessions);
  const chargingPowerKw =
    vehicle?.charging_power_kw ??
    envelopeNumber(vehicle?.charging_power) ??
    vehicle?.halo_correlation?.vehicle_power_kw ??
    null;
  const isCharging =
    vehicle?.is_charging ??
    (chargingPowerKw != null && chargingPowerKw >= 0.3);
  const activeSession =
    session?.status === "ACTIVE" && (vehicle?.is_plugged_in === true || vehicle?.is_charging === true || isCharging)
      ? session
      : null;
  const renewableKwh = totalRenewableKwh(activeSession);
  const chargedKwh = activeSession ? sessionEnergyKwh(activeSession) : 0;

  return {
    siteSlug,
    displayName: vehicle?.display_name?.toUpperCase() ?? "MERCEDES EQE",
    manufacturer: vehicle?.manufacturer ?? "Mercedes-Benz",
    model: vehicle?.model ?? "EQE",
    maskedVin: vehicle?.masked_vin ?? "—",
    socPct: soc,
    energyKwh,
    capacityKwh: capacity,
    rangeKm: vehicle?.electric_range_km ?? envelopeNumber(vehicle?.electric_range) ?? null,
    targetSocPct: resolveTargetSocPct(vehicle, activeSession, reasoning),
    chargingPowerKw,
    isCharging,
    isPluggedIn: vehicle?.is_plugged_in,
    freshnessLabel: vehicle?.freshness_label ?? "—",
    dataQuality: vehicle?.data_quality ?? "—",
    startedAt: formatIsoTime(activeSession?.charging_started_at ?? activeSession?.connected_at),
    chargedTodayKwh: chargedKwh,
    costKr: activeSession?.actual_cost_sek ?? null,
    savingsKr: activeSession?.savings_sek ?? null,
    surplusLabel: surplusLabel(activeSession),
    co2SavedKg: estimateCo2SavedKg(renewableKwh),
    chargingSubtitle: chargingSubtitle(vehicle, activeSession, reasoning),
    vehicleId: vehicle?.id ?? null,
    capabilities: vehicle?.capabilities ?? null,
    halo: vehicle?.halo_correlation ?? null,
    integration,
    reasoning,
    sessions,
    sessionHistoryBars: recentSessionEnergyBars(sessions),
    avgRenewableSharePct: averageRenewableSharePct(sessions),
    lastCompletedSession: completed,
    lastChargeKwh: completed ? sessionEnergyKwh(completed) : null,
    lastChargeTime: formatIsoTime(completed?.charging_started_at ?? completed?.connected_at),
    lastChargeDuration: formatSessionDuration(
      completed?.charging_started_at ?? completed?.connected_at ?? null,
      completed?.charging_stopped_at ?? completed?.disconnected_at ?? null,
    ),
    totalSavingsKr: sessions.reduce((sum, s) => sum + (s.savings_sek ?? 0), 0),
    totalEnergyKwh: sessions.reduce((sum, s) => sum + sessionEnergyKwh(s), 0),
    departureTime: reasoning?.vehicle_departure_time ?? null,
    requiredEnergyKwh: reasoning?.vehicle_required_energy_kwh ?? null,
    smartChargingState: reasoning?.smart_charging_state ?? null,
    planReasonSv: reasoning?.decision_reason_sv ?? reasoning?.solar_plan_reason ?? null,
    connected: vehicle?.connection_state === "CONNECTED",
    connectionState: integration?.connection_state ?? vehicle?.connection_state ?? null,
    signalStrength: healthLabelSv(integration?.health),
    refreshIntervalSec,
    commandsEnabled: integration?.commands_enabled ?? false,
    integrationEnabled: integration?.enabled ?? false,
    canStopCharging: vehicle?.capabilities.can_stop_charging ?? false,
    canStartCharging: vehicle?.capabilities.can_start_charging ?? false,
    canSetTargetSoc: vehicle?.capabilities.can_set_target_soc ?? false,
    activeSession,
  };
}

export type VehicleDisplay = ReturnType<typeof buildVehicleDisplay>;
