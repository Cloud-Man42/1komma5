export type PiConnectionState = "CONNECTED" | "RECONNECTING" | "OFFLINE";

/** Mirrors `DisplaySectionMeta` in `backend/app/schemas_display.py`. */
export interface DisplaySectionMeta {
  available: boolean;
  unavailable_reason?: string | null;
  stale?: boolean;
}

export interface DisplayOverview {
  generated_at: string;
  site: { slug: string; name: string; timezone: string };
  freshness: {
    updated_at: string | null;
    data_age_seconds: number | null;
    stale: boolean;
    connection_state: string;
  };
  live: {
    solar_power_kw: number | null;
    house_power_kw: number | null;
    grid_net_power_kw: number | null;
    grid_direction: string | null;
    grid_direction_sv: string | null;
    battery_soc_pct: number | null;
    battery_power_kw: number | null;
    battery_state_sv: string | null;
    battery_stored_kwh: number | null;
    battery_capacity_kwh: number | null;
    solar_surplus_kw: number | null;
    produced_today_kwh: number | null;
    consumed_today_kwh: number | null;
    imported_today_kwh: number | null;
    exported_today_kwh: number | null;
    self_consumption_pct: number | null;
    self_sufficiency_pct: number | null;
    battery_soh_pct: number | null;
  };
  sparklines: Record<string, { points: { timestamp: string; value: number }[] }>;
  weather: DisplaySectionMeta & {
    temperature_c?: number | null;
    label_sv?: string | null;
    icon?: string | null;
  };
  price: DisplaySectionMeta & {
    tier?: string | null;
    tier_label_sv?: string | null;
    current_ore_kwh?: number | null;
  };
  flow: DisplaySectionMeta & {
    nodes: { key: string; label_sv: string; power_kw: number | null; status_sv?: string | null }[];
  };
  vehicle: DisplaySectionMeta & {
    display_name?: string | null;
    model?: string | null;
    status_sv?: string | null;
    soc_pct?: number | null;
    range_km?: number | null;
    charging_mode_sv?: string | null;
    ready_by?: string | null;
    cost_today_sek?: number | null;
  };
  charger: DisplaySectionMeta & {
    name?: string | null;
    status_sv?: string | null;
    power_w?: number | null;
    available_current_a?: number | null;
    smart_charging_active?: boolean | null;
    ready_by?: string | null;
    price_tier_label_sv?: string | null;
  };
  spa: DisplaySectionMeta & {
    water_temperature_c?: number | null;
    filter_status_sv?: string | null;
    next_cleaning_at?: string | null;
    consumption_today_kwh?: number | null;
    cost_today_sek?: number | null;
    power_w?: number | null;
  };
  economy: DisplaySectionMeta & {
    total_savings_sek?: number | null;
    total_savings_change_pct?: number | null;
    total_cost_sek?: number | null;
    total_cost_change_pct?: number | null;
    net_sek?: number | null;
    net_change_pct?: number | null;
    daily: { day: number; savings_sek: number; cost_sek: number; net_sek: number }[];
  };
  highlights: DisplaySectionMeta & {
    items: { label_sv: string; value: string; detail_sv?: string | null }[];
  };
  system_status: {
    status_sv: string;
    detail_sv: string;
    healthy: boolean;
  };
}

/**
 * Authentication rides on the request rather than on this call: the Pi's local
 * proxy injects a bearer header, while a browser enrolled through
 * `/api/v1/display/enroll` sends an HttpOnly cookie. Hence the relative URL and
 * the explicit credentials — both keep the request same-origin.
 */
export async function fetchDisplayOverview(slug: string): Promise<DisplayOverview> {
  const response = await fetch(`/api/v1/display/overview/${slug}`, {
    cache: "no-store",
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(`Display overview failed: ${response.status}`);
  }
  return response.json() as Promise<DisplayOverview>;
}
