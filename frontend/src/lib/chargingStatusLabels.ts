/** Swedish display labels for smart charging status. */

const REASON_LABELS: Record<string, string> = {
  stable_grid_export: "Följer solöverskott",
  smart_solar_surplus: "Följer solöverskott",
  smart_wait_cheaper: "Pausad",
  smart_scheduled: "Laddar smart",
  cheap_now: "Laddar smart",
  solar_forecast_wait: "Väntar på solel (prognos)",
  solar_forecast_partial_grid: "Planerar delvis nätenergi",
  solar_forecast_wait_cheaper: "Väntar på billigare nät + solel",
  solar_forecast_grid_required: "Planerar nätenergi",
  solar_forecast_unavailable: "Ingen solprognos",
  temporary_grid_import: "Tillfälligt nätuttag",
  reduce_before_stop: "Minskar laddström",
  stop_delay: "Väntar på omstart",
  start_delay: "Väntar på mer sol",
  waiting_for_export: "Väntar på mer sol",
  cooldown: "Väntar på omstart",
  user_paused: "Pausad",
  no_vehicle_connected: "Väntar på bil",
  fault: "Fel",
  charger_offline: "Fel",
};

const STATE_LABELS: Record<string, string> = {
  PAUSED: "Pausad",
  WAITING_TO_START: "Väntar på omstart",
  STARTING: "Laddar smart",
  CHARGING_STABLE: "Laddar smart",
  REDUCING: "Minskar laddström",
  WAITING_TO_STOP: "Minskar laddström",
  STOPPING: "Pausad",
  COOLDOWN: "Väntar på omstart",
  FAULT: "Fel",
};

export function displayStatusSv(params: {
  state?: string | null;
  reason?: string | null;
  externallyLimited?: boolean;
}): string {
  if (params.externallyLimited) {
    return "Externt begränsad";
  }
  if (params.reason && params.reason in REASON_LABELS) {
    return REASON_LABELS[params.reason];
  }
  if (params.state && params.state in STATE_LABELS) {
    return STATE_LABELS[params.state];
  }
  return "Laddar smart";
}
