export interface Reading {
  recorded_at: string;
  solar_production_w: number;
  consumption_w: number;
  grid_import_w: number;
  grid_export_w: number;
  battery_soc_pct: number;
  battery_power_w: number;
}

export interface Site {
  slug: string;
  name: string;
  timezone: string;
  external_system_id?: string | null;
  fallback_purchase_price_sek_kwh: number;
  export_compensation_sek_kwh: number;
  main_fuse_a?: number | null;
  safety_margin_a?: number;
  latest_reading: Reading | null;
}

export interface DashboardSectionMeta {
  unavailable_reason?: string | null;
}

export interface DashboardSiteSection {
  slug: string;
  name: string;
  timezone: string;
}

export interface DashboardFreshnessSection {
  updated_at: string | null;
  data_age_seconds: number | null;
  stale: boolean;
}

export interface DashboardLiveSection extends DashboardSectionMeta {
  solar_production_w: number | null;
  consumption_w: number | null;
  grid_import_w: number | null;
  grid_export_w: number | null;
  battery_soc_pct: number | null;
  battery_power_w: number | null;
  battery_direction: "charging" | "discharging" | "idle" | null;
  ev_power_w: number | null;
}

export interface DashboardTodaySection extends DashboardSectionMeta {
  produced_kwh: number | null;
  consumed_kwh: number | null;
  imported_kwh: number | null;
  exported_kwh: number | null;
  energy_cost_sek: number | null;
  savings_sek: number | null;
}

export interface DashboardEvSection extends DashboardSectionMeta {
  available: boolean;
  charging: boolean;
  charging_mode: string | null;
  display_status_sv: string | null;
  power_w: number | null;
  session_energy_kwh: number | null;
  solar_share_pct: number | null;
  estimated_cost_sek: number | null;
  next_planned_charge_at: string | null;
}

export interface DashboardVehicleSection extends DashboardSectionMeta {
  available: boolean;
  display_name: string | null;
  mode: "parked" | "charging" | string;
  state_of_charge_percent: number | null;
  electric_range_km: number | null;
  is_plugged_in: boolean | null;
  is_charging: boolean | null;
  charging_power_kw: number | null;
  location_name: string | null;
  charging_type: string | null;
  session_energy_kwh: number | null;
  data_quality: string | null;
  freshness_label: string | null;
}

export interface DashboardSolarSection extends DashboardSectionMeta {
  expected_today_kwh: number | null;
  remaining_kwh: number | null;
  peak_power_w: number | null;
  peak_at: string | null;
  confidence_pct: number | null;
  inverter_max_power_kw: number | null;
}

export interface DashboardPriceSection extends DashboardSectionMeta {
  current_eur_kwh: number | null;
  lowest_eur_kwh: number | null;
  highest_eur_kwh: number | null;
  tier: string | null;
}

export interface DashboardOptimizationSection extends DashboardSectionMeta {
  strategy_sv: string | null;
  explanation_sv: string | null;
  reasoning_steps: string[];
  solar_first: boolean | null;
  battery_soc_pct: number | null;
}

export interface DashboardAlert {
  severity: string;
  message_sv: string;
}

export interface SiteDashboard {
  site: DashboardSiteSection;
  freshness: DashboardFreshnessSection;
  live: DashboardLiveSection | null;
  today: DashboardTodaySection | null;
  ev: DashboardEvSection | null;
  vehicle: DashboardVehicleSection | null;
  solar: DashboardSolarSection | null;
  price: DashboardPriceSection | null;
  optimization: DashboardOptimizationSection | null;
  alerts: DashboardAlert[];
  spa_integration_enabled: boolean;
  vehicle_integration_enabled: boolean;
}

export interface SiteEnergyConfig {
  site_slug: string;
  load_includes_ev_charger: boolean | null;
  inverter_display_name: string;
  physical_ev_charger_label: string;
  ev_vehicle_label: string;
}

export interface EvCharger {
  id: number;
  site_slug: string;
  name: string;
  manufacturer: string;
  model: string;
  control_source: "chargeamp" | string;
  heartbeat_ev_id: string | null;
  heartbeat_charger_id: string | null;
  chargeamp_charger_id: string | null;
  bridge_enabled: boolean;
  max_current_a: number;
  min_current_a: number;
  phases: number;
  nominal_voltage_v: number;
  max_power_w: number | null;
  max_grid_import_w: number | null;
  update_interval_seconds: number;
  min_change_interval_seconds: number;
  current_hysteresis_a: number;
  stale_timeout_seconds: number;
  chargeamps_api_key_configured: boolean;
  last_applied_current_a: number | null;
  last_bridge_run_at: string | null;
  last_heartbeat_data_at: string | null;
  override_until: string | null;
  override_active: boolean;
  charging_mode: string | null;
  target_soc_pct: number | null;
  manual_soc_pct: number | null;
  departure_time: string | null;
  power_w: number | null;
  available_modes: string[];
  deadline_at?: string | null;
  solar_start_threshold_w?: number;
  solar_stop_threshold_w?: number;
  solar_start_delay_seconds?: number;
  solar_stop_delay_seconds?: number;
  last_charging_action?: string | null;
  last_charging_reason?: string | null;
  last_charger_error_code?: string | null;
  last_halo_connected?: boolean | null;
  last_vehicle_connected?: boolean | null;
  smart_charging_state?: string | null;
  last_requested_current_a?: number | null;
  last_configured_current_a?: number | null;
  last_actual_charging_current_a?: number | null;
  last_actual_power_w?: number | null;
  externally_limited?: boolean | null;
  start_delay_seconds?: number;
  stop_delay_seconds?: number;
  minimum_run_time_seconds?: number;
  minimum_off_time_seconds?: number;
  temporary_grid_import_allowance_w?: number;
  temporary_grid_import_seconds?: number;
  grid_deadband_w?: number;
  minimum_current_change_interval_seconds?: number;
  max_current_increase_per_step_a?: number;
  max_current_decrease_per_step_a?: number;
  max_automatic_starts_per_hour?: number;
  virtual_evse_enabled?: boolean;
  semp_device_id?: string | null;
  manufacturer_id?: string | null;
  model_id?: string | null;
  integration_method?: string | null;
  external_charger_id?: string | null;
  connection_settings?: Record<string, unknown>;
  connection_status?: string;
  last_connection_at?: string | null;
  last_connection_test_at?: string | null;
}

export interface ChargerManufacturer {
  id: string;
  name: string;
  model_count: number;
}

export interface ChargerCatalogModel {
  id: string;
  manufacturer_id: string;
  name: string;
  status: string;
  supported_protocols: string[];
  integration_methods: string[];
  documentation_url?: string | null;
  capabilities: Record<string, boolean>;
}

export interface ChargerIntegrationMethod {
  id: string;
  label: string;
  protocol: string;
  connection_type: string;
  recommended: boolean;
  priority: number;
  implementation_status: string;
  cloud_dependent: boolean;
  documentation_url?: string | null;
  credential_fields: Array<Record<string, unknown>>;
  connection_fields: Array<Record<string, unknown>>;
}

export interface ChargerModelDetail {
  model: ChargerCatalogModel;
  integration_methods: ChargerIntegrationMethod[];
}

export interface ChargerFeatureMatrixRow {
  manufacturer: string;
  model: string;
  support: string;
  start_stop: boolean;
  current: boolean;
  energy: boolean;
  session: boolean;
  smart_charging: boolean;
}

export interface EnergyBalanceHistory {
  items: EnergyBalanceSnapshot[];
  total: number;
}

export interface ChargerConnectionTestResult {
  success: boolean;
  status: string;
  message: string;
  model_mismatch?: boolean;
  detected_device?: Record<string, string | null> | null;
  capabilities?: Record<string, unknown> | null;
}

export interface EvBridgeStatus {
  charger_id: number;
  bridge_enabled: boolean;
  charging_mode: string;
  active_policy: string;
  ev_target_power_w: number | null;
  requested_current_a: number | null;
  applied_current_a: number | null;
  previous_current_a: number | null;
  configured_current_a?: number | null;
  actual_charging_current_a?: number | null;
  actual_power_w?: number | null;
  smart_charging_state?: string | null;
  externally_limited?: boolean;
  display_status_sv?: string | null;
  fuse_headroom_a?: number | null;
  last_heartbeat_data_at: string | null;
  last_bridge_run_at: string | null;
  halo_connected: boolean | null;
  vehicle_connected: boolean | null;
  decision_reason: string | null;
  discovery_hints: string[];
  stale: boolean;
  override_active: boolean;
  override_until: string | null;
  last_error_code?: string | null;
  last_charging_action?: string | null;
  phase_current_l1_a?: number | null;
  phase_current_l2_a?: number | null;
  phase_current_l3_a?: number | null;
  sungrow_fresh?: boolean | null;
  sungrow_telemetry_age_seconds?: number | null;
  energy_balance_status?: string | null;
  energy_balance_alignment_delta_seconds?: number | null;
  energy_balance_flags?: string[];
}

export interface EnergyBalanceSnapshot {
  charger_id: number;
  recorded_at: string | null;
  status: string;
  flags: string[];
  inverter_display_name: string;
  sungrow_pv_power_w: number | null;
  sungrow_load_power_w: number | null;
  sungrow_grid_import_w: number | null;
  sungrow_grid_export_w: number | null;
  sungrow_battery_charge_w: number | null;
  sungrow_battery_discharge_w: number | null;
  sungrow_battery_soc_pct: number | null;
  sungrow_fresh: boolean | null;
  sungrow_telemetry_age_seconds: number | null;
  halo_power_w: number | null;
  virtual_evse_reported_power_w: number | null;
  heartbeat_observed_ev_power_w: number | null;
  heartbeat_home_consumption_w: number | null;
  non_ev_house_load_w: number | null;
  non_ev_house_load_reason: string | null;
  residual_w: number | null;
  alignment_delta_seconds: number | null;
  energy_flow_line: string | null;
}

export interface VirtualEvseStatus {
  charger_id: number;
  virtual_evse_enabled: boolean;
  semp_device_id: string | null;
  status: string | null;
  reported_power_w: number | null;
  halo_power_w: number | null;
  heartbeat_observed_ev_power_w: number | null;
  heartbeat_detected: boolean;
  vehicle_connected: boolean | null;
  stale: boolean;
  physical_charger_label: string;
  ev_vehicle_label: string;
}

export interface EnergyReasoning {
  charger_id: number;
  bridge_enabled: boolean;
  charging_active: boolean;
  charging_mode: string;
  heartbeat_charging_mode: string | null;
  ev_charge_from_grid_recommended: boolean;
  ev_target_power_w: number | null;
  pv_power_w: number | null;
  grid_import_w: number | null;
  grid_export_w: number | null;
  home_consumption_w: number | null;
  battery_soc_pct: number | null;
  ev_actual_power_w: number | null;
  current_price_eur_kwh: number | null;
  price_average_eur_kwh: number | null;
  price_tier: "green" | "normal" | "red" | "unknown" | string;
  price_would_charge: boolean;
  price_reason: string;
  smart_charging_state: string | null;
  decision_reason: string | null;
  decision_reason_sv: string | null;
  display_status_sv: string | null;
  requested_current_a: number | null;
  applied_current_a: number | null;
  vehicle_connected: boolean | null;
  halo_connected: boolean | null;
  solar_plan_available: boolean;
  solar_plan_reason: string | null;
  solar_first: boolean;
  active_optimizations: string[];
  energy_flow_line: string | null;
  energy_balance_status: string | null;
  reasoning_steps: string[];
  vehicle_linked: boolean;
  vehicle_display_name: string | null;
  vehicle_soc_pct: number | null;
  vehicle_target_soc_pct: number | null;
  vehicle_required_energy_kwh: number | null;
  vehicle_departure_time: string | null;
  vehicle_energy_quality: string | null;
}

export interface EvSolarChargingPlan {
  available: boolean;
  expected_usable_solar_kwh: number | null;
  planning_solar_kwh: number | null;
  solar_first: boolean;
  quality: string | null;
  confidence: number | null;
  expected_solar_window_start: string | null;
  expected_solar_window_end: string | null;
  cheapest_grid_window: string | null;
  explanation_sv: string | null;
  reason_code: string | null;
}

export interface EvChargingSavings {
  charger_id: number;
  period_from: string;
  period_to: string;
  energy_kwh: number;
  actual_cost_sek: number;
  baseline_cost_sek: number;
  savings_sek: number;
  savings_ore: number;
  savings_pct: number;
  charging_intervals: number;
  period_avg_price_kwh: number | null;
  has_data: boolean;
}

export interface EvEnergySources {
  solar_direct_kwh: number;
  solar_battery_kwh: number;
  grid_battery_kwh: number;
  grid_direct_kwh: number;
}

export interface EvChargingInterval {
  id: number;
  start_time: string;
  end_time: string;
  charged_energy_kwh: number;
  average_charging_power_w: number | null;
  electricity_price_sek_kwh: number | null;
  energy_sources: EvEnergySources;
  actual_cost_sek: number;
  reference_cost_sek: number | null;
  savings_sek: number | null;
  confidence: number | null;
  data_quality: string | null;
}

export interface EvChargingSession {
  id: number;
  charger_id: number;
  started_at: string;
  ended_at: string | null;
  status: string;
  total_energy_kwh: number | null;
  energy_sources: EvEnergySources;
  actual_cost_sek: number | null;
  reference_cost_sek: number | null;
  savings_sek: number | null;
  smart_charging_savings_sek: number | null;
  solar_contribution_sek: number | null;
  renewable_share_pct: number | null;
  grid_share_pct: number | null;
  average_cost_sek_per_kwh: number | null;
  energy_quality: string | null;
  cost_quality: string | null;
  attribution_quality: string | null;
  savings_baseline: string;
  calculation_version: string;
  reconciliation_delta_kwh: number | null;
  intervals: EvChargingInterval[];
}

export interface EvChargingStats {
  period: string;
  period_from: string;
  period_to: string;
  total_energy_kwh: number;
  actual_cost_sek: number;
  reference_cost_sek: number | null;
  savings_sek: number | null;
  average_cost_sek_per_kwh: number | null;
  energy_sources: EvEnergySources;
  renewable_share_percent: number;
  grid_share_percent: number;
  smart_charging_savings_sek: number | null;
  solar_contribution_sek: number;
  session_count: number;
  savings_baseline: string;
}

export interface AggregatedReading extends Reading {
  bucket_start: string;
}

export interface HistoryResponse {
  slug: string;
  bucket_minutes: number;
  readings: (Reading | AggregatedReading)[];
}

export type PeakPeriod = "day" | "month" | "year";

export interface PeakReading {
  period_start: string;
  solar_production_w: number;
  consumption_w: number;
  battery_charge_w: number;
  battery_discharge_w: number;
}

export interface PeaksResponse {
  slug: string;
  timezone: string;
  period: PeakPeriod;
  peaks: PeakReading[];
}

export interface FinancialStat {
  period_start: string;
  solar_self_consumed_kwh: number;
  battery_self_consumed_kwh: number;
  exported_kwh: number;
  imported_kwh: number;
  solar_savings_sek: number;
  battery_savings_sek: number;
  export_revenue_sek: number;
  grid_import_cost_sek: number;
  market_priced_fraction: number;
  energy_sale_revenue_sek?: number;
  grid_benefit_revenue_sek?: number;
  tax_credit_sek?: number;
  effective_sell_price_sek_kwh?: number | null;
  export_spot_priced_fraction?: number;
  uncontracted_exported_kwh?: number;
}

export type ExportPricingMode = "spot" | "feed_in" | "flat";

export interface FinancialStatsResponse {
  slug: string;
  timezone: string;
  period: PeakPeriod;
  fallback_purchase_price_sek_kwh: number;
  export_compensation_sek_kwh: number;
  sell_pricing_mode?: ExportPricingMode;
  sell_contract_start_date?: string | null;
  stats: FinancialStat[];
}

export interface ForecastValues {
  solar_self_consumed_kwh: number;
  battery_self_consumed_kwh: number;
  exported_kwh: number;
  imported_kwh: number;
  solar_savings_sek: number;
  battery_savings_sek: number;
  export_revenue_sek: number;
  grid_import_cost_sek: number;
  net_sek: number;
}

export interface MonthlyForecast {
  month: string;
  actual: ForecastValues;
  forecast: ForecastValues;
  total: ForecastValues;
}

export interface YearForecastResponse {
  slug: string;
  timezone: string;
  year: number;
  observed_days: number;
  confidence: "very_low" | "low" | "medium" | "high";
  uncertainty_pct: number;
  import_baseline_year: number | null;
  import_baseline_source: string | null;
  import_baseline_estimated: boolean;
  import_baseline_kwh: number | null;
  fallback_purchase_price_sek_kwh: number;
  export_compensation_sek_kwh: number;
  actual: ForecastValues;
  forecast: ForecastValues;
  total: ForecastValues;
  months: MonthlyForecast[];
}

export interface MarketPricePoint {
  timestamp: string;
  spot_eur_kwh: number;
  all_in_eur_kwh: number | null;
}

export interface MarketPricesResponse {
  slug: string;
  timezone: string;
  resolution: string;
  current_price_eur_kwh: number | null;
  average_all_in_eur_kwh: number | null;
  highest_all_in_eur_kwh: number | null;
  lowest_all_in_eur_kwh: number | null;
  points: MarketPricePoint[];
}

export interface SiteHeartbeatMapping {
  slug: string;
  name: string;
  external_system_id: string | null;
}

export interface HeartbeatConfig {
  connection_type: "mock" | "cloud" | "local";
  connection_type_label: string;
  host: string;
  port: number;
  use_tls: boolean;
  api_path: string;
  poll_interval_seconds: number;
  dashboard_refresh_seconds: number;
  api_url: string | null;
  username: string;
  password_configured: boolean;
  api_token_configured: boolean;
  connection_mode: string;
  contacting_component: string;
  implementation_status: string;
  notes: string[];
  sites: SiteHeartbeatMapping[];
  updated_at: string | null;
}

export interface HeartbeatConfigUpdate {
  connection_type: "mock" | "cloud" | "local";
  host: string;
  port: number;
  use_tls: boolean;
  api_path: string;
  poll_interval_seconds: number;
  dashboard_refresh_seconds: number;
  username: string;
  password?: string;
  api_token?: string;
  sites: { slug: string; external_system_id: string | null }[];
}

export interface ChargeAmpsConfig {
  provider: string;
  effective_provider: string;
  mock: boolean;
  api_key_configured: boolean;
  env_api_key_configured: boolean;
  charger_api_keys_configured: number;
  email_configured: boolean;
  password_configured: boolean;
  ready: boolean;
  notes: string[];
}

export interface ChargerReadinessIssue {
  site_slug: string;
  charger_id: number;
  charger_name: string;
  code: string;
  message: string;
}

export interface ChargingReadiness {
  ready: boolean;
  chargeamps_ready: boolean;
  active_bridge_chargers: number;
  issues: ChargerReadinessIssue[];
  notes: string[];
}

export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") return "";
  return "http://localhost:8000";
}

const PERF_DEBUG = process.env.NEXT_PUBLIC_PERFORMANCE_DEBUG === "1";
const recentFetches = new Map<string, number>();

async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url = typeof input === "string" ? input : input.toString();
  if (PERF_DEBUG && typeof window !== "undefined") {
    const now = Date.now();
    const last = recentFetches.get(url);
    if (last && now - last < 2000) {
      console.warn("[perf] duplicate fetch within 2s:", url);
    }
    recentFetches.set(url, now);
  }
  return fetch(input, init);
}

export async function readApiError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // keep raw text
  }
  return text || `HTTP ${res.status}`;
}

export async function fetchSites(): Promise<Site[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch sites: ${res.status}`);
  return res.json();
}

export async function fetchSiteHistory(
  slug: string,
  bucket = 5,
  hours = 24,
): Promise<HistoryResponse> {
  const to = new Date();
  const from = new Date(to.getTime() - hours * 60 * 60 * 1000);
  const params = new URLSearchParams({
    from: from.toISOString(),
    to: to.toISOString(),
    bucket: String(bucket),
  });
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/readings?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`);
  return res.json();
}

export async function fetchSitePeaks(
  slug: string,
  period: PeakPeriod,
  year?: number,
): Promise<PeaksResponse> {
  const params = new URLSearchParams({ period });
  if (year !== undefined) params.set("year", String(year));
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/peaks?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch peak values: ${res.status}`);
  return res.json();
}

export async function fetchFinancialStats(
  slug: string,
  period: PeakPeriod,
  year?: number,
): Promise<FinancialStatsResponse> {
  const params = new URLSearchParams({ period });
  if (year !== undefined) params.set("year", String(year));
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/financial-stats?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch financial statistics: ${res.status}`);
  return res.json();
}

export async function fetchYearForecast(
  slug: string,
  year: number,
): Promise<YearForecastResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/forecast?year=${year}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch forecast: ${res.status}`);
  return res.json();
}

export async function fetchMarketPrices(
  slug: string,
  hours = 24,
  timezone = "Europe/Stockholm",
): Promise<MarketPricesResponse> {
  const now = new Date();
  let from: Date;
  let to: Date;
  if (hours > 48) {
    // Long-range history (e.g. economy dashboard month view).
    from = new Date(now.getTime() - hours * 60 * 60 * 1000);
    to = new Date(now.getTime() + 2 * 60 * 60 * 1000);
  } else {
    const { intradayMarketPriceWindow } = await import("@/lib/marketPriceWindow");
    ({ from, to } = intradayMarketPriceWindow(now, timezone));
  }
  const params = new URLSearchParams({
    from: from.toISOString(),
    to: to.toISOString(),
    resolution: "1h",
  });
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/market-prices?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Failed to fetch market prices: ${res.status}`);
  }
  return res.json();
}

export async function fetchHeartbeatConfig(): Promise<HeartbeatConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/system/heartbeat-config`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch heartbeat config: ${res.status}`);
  return res.json();
}

export async function saveHeartbeatConfig(payload: HeartbeatConfigUpdate): Promise<HeartbeatConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/system/heartbeat-config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Failed to save heartbeat config: ${res.status}`);
  }
  return res.json();
}

export async function fetchChargeAmpsConfig(): Promise<ChargeAmpsConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/system/chargeamps-config`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch Charge Amps config: ${res.status}`);
  return res.json();
}

export async function fetchChargingReadiness(): Promise<ChargingReadiness> {
  const res = await fetch(`${getApiBaseUrl()}/api/system/charging-readiness`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch charging readiness: ${res.status}`);
  return res.json();
}

export async function createSite(payload: {
  slug: string;
  name: string;
  timezone: string;
  external_system_id?: string | null;
  fallback_purchase_price_sek_kwh?: number;
  export_compensation_sek_kwh?: number;
}): Promise<Site> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateSite(
  slug: string,
  payload: {
    name?: string;
    timezone?: string;
    external_system_id?: string | null;
    fallback_purchase_price_sek_kwh?: number;
    export_compensation_sek_kwh?: number;
    main_fuse_a?: number | null;
    safety_margin_a?: number;
  },
): Promise<Site> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteSite(slug: string): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

export async function fetchEvChargers(slug: string): Promise<EvCharger[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/ev-chargers`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createEvCharger(
  slug: string,
  payload: {
    name: string;
    manufacturer?: string;
    model?: string;
    manufacturer_id?: string;
    model_id?: string;
    integration_method?: string;
    external_charger_id?: string | null;
    connection_settings?: Record<string, unknown>;
    heartbeat_ev_id?: string | null;
    heartbeat_charger_id?: string | null;
    chargeamp_charger_id?: string | null;
    chargeamps_api_key?: string | null;
    bridge_enabled?: boolean;
    max_current_a?: number;
    min_current_a?: number;
    phases?: number;
    nominal_voltage_v?: number;
    max_power_w?: number | null;
    max_grid_import_w?: number | null;
    update_interval_seconds?: number;
    min_change_interval_seconds?: number;
    current_hysteresis_a?: number;
    stale_timeout_seconds?: number;
    solar_start_threshold_w?: number;
    solar_stop_threshold_w?: number;
    solar_start_delay_seconds?: number;
    solar_stop_delay_seconds?: number;
  },
): Promise<EvCharger> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/ev-chargers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateEvCharger(
  slug: string,
  chargerId: number,
  payload: Record<string, unknown>,
): Promise<EvCharger> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteEvCharger(slug: string, chargerId: number): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function syncEvChargers(slug: string): Promise<EvCharger[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/sync`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchChargerManufacturers(): Promise<ChargerManufacturer[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/chargers/manufacturers`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchChargerModels(manufacturerId: string): Promise<ChargerCatalogModel[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/chargers/manufacturers/${manufacturerId}/models`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchChargerModelDetail(
  manufacturerId: string,
  modelId: string,
): Promise<ChargerModelDetail> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/chargers/manufacturers/${manufacturerId}/models/${modelId}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchChargerManufacturer(manufacturerId: string): Promise<ChargerManufacturer> {
  const res = await fetch(`${getApiBaseUrl()}/api/chargers/manufacturers/${manufacturerId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchChargerFeatureMatrix(): Promise<ChargerFeatureMatrixRow[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/chargers/feature-matrix`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchChargerIntegrationMethods(): Promise<ChargerIntegrationMethod[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/chargers/integration-methods`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function testEvChargerConnectionDraft(
  slug: string,
  payload: {
    manufacturer_id: string;
    model_id: string;
    integration_method: string;
    chargeamp_charger_id?: string | null;
    external_charger_id?: string | null;
    chargeamps_api_key?: string | null;
    connection_settings?: Record<string, unknown>;
  },
): Promise<ChargerConnectionTestResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/test-connection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function testEvChargerConnection(
  slug: string,
  chargerId: number,
): Promise<ChargerConnectionTestResult> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/test-connection`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function controlEvCharger(
  slug: string,
  chargerId: number,
  payload: {
    charging_mode?: string;
    target_soc_pct?: number;
    manual_soc_pct?: number;
    departure_time?: string;
    deadline_at?: string | null;
    clear_deadline_at?: boolean;
  },
): Promise<EvCharger> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/control`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const OVERRIDE_HOURS = [4, 8, 12, 24] as const;

export async function setEvChargerOverride(
  slug: string,
  chargerId: number,
  payload: { hours?: number; clear?: boolean },
): Promise<EvCharger> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/override`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEvBridgeStatus(
  slug: string,
  chargerId: number,
): Promise<EvBridgeStatus> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/bridge-status`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEnergyBalance(
  slug: string,
  chargerId: number,
): Promise<EnergyBalanceSnapshot> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/energy-balance`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/** The API rejects anything larger. Asking for 288 returned 422, and the caller
 *  swallowed it, so the charging power charts sat empty at 0.0 kW. */
export const ENERGY_BALANCE_HISTORY_MAX_LIMIT = 200;

export async function fetchEnergyBalanceHistory(
  slug: string,
  chargerId: number,
  limit = 50,
  offset = 0,
): Promise<EnergyBalanceHistory> {
  const params = new URLSearchParams({
    limit: String(Math.min(limit, ENERGY_BALANCE_HISTORY_MAX_LIMIT)),
    offset: String(offset),
  });
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/energy-balance/history?${params}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEnergyReasoning(
  slug: string,
  chargerId: number,
): Promise<EnergyReasoning> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/energy-reasoning`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchVirtualEvseStatus(
  slug: string,
  chargerId: number,
): Promise<VirtualEvseStatus> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/virtual-evse/status`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSiteEnergyConfig(slug: string): Promise<SiteEnergyConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/energy-config`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateSiteEnergyConfig(
  slug: string,
  payload: {
    load_includes_ev_charger?: boolean | null;
    clear_load_includes_ev_charger?: boolean;
    inverter_display_name?: string;
    physical_ev_charger_label?: string;
    ev_vehicle_label?: string;
  },
): Promise<SiteEnergyConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/energy-config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEvSolarChargingPlan(
  slug: string,
  chargerId: number,
): Promise<EvSolarChargingPlan> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/solar-charging-plan`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEvChargerSavings(
  slug: string,
  chargerId: number,
  days = 30,
): Promise<EvChargingSavings> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/savings?days=${days}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEvChargingStats(
  slug: string,
  chargerId: number,
  period = "month",
): Promise<EvChargingStats> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/stats?period=${period}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEvChargingSessions(
  slug: string,
  chargerId: number,
  limit = 20,
): Promise<EvChargingSession[]> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/sessions?limit=${limit}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEvChargingSession(
  slug: string,
  chargerId: number,
  sessionId: number,
): Promise<EvChargingSession> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/sessions/${sessionId}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchCurrentEvSession(
  slug: string,
  chargerId: number,
): Promise<EvChargingSession | null> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/ev-chargers/${chargerId}/sessions/current`,
    { cache: "no-store" },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await res.text());
  const body = await res.json();
  return body ?? null;
}

export function formatWatts(w: number): string {
  if (Math.abs(w) >= 1000) return `${(w / 1000).toFixed(1)} kW`;
  return `${Math.round(w)} W`;
}

export interface SolarForecastPoint {
  timestamp: string;
  baseline_power_w: number;
  corrected_power_w: number;
  expected_energy_kwh: number;
  lower_bound_power_w: number;
  upper_bound_power_w: number;
  confidence: number;
  correction_factor: number;
}

export interface SolarForecast {
  site_id: number;
  generated_at: string;
  model_version: string;
  quality: "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT_DATA";
  weather_source: string;
  expected_today_kwh: number;
  remaining_today_kwh: number;
  expected_tomorrow_kwh: number | null;
  peak_power_w: number;
  peak_time: string | null;
  confidence: number;
  lower_today_kwh: number;
  upper_today_kwh: number;
  weather_summary: string;
  actual_today_kwh: number;
  forecast_so_far_kwh: number;
  remaining_vs_expected_kwh: number;
  raw_forecast_today_kwh?: number;
  raw_forecast_so_far_kwh?: number;
  raw_forecast_tomorrow_kwh?: number | null;
  corrected_forecast_today_kwh?: number;
  corrected_forecast_tomorrow_kwh?: number | null;
  correction_factor?: number;
  model_state?: string;
  confidence_score?: number | null;
  confidence_label?: string | null;
  historical_samples?: number;
  production_days_observed?: number;
  points: SolarForecastPoint[];
}

export interface SolarSiteConfig {
  site_slug: string;
  latitude: number | null;
  longitude: number | null;
  installed_peak_power_kw: number | null;
  azimuth_deg: number | null;
  tilt_deg: number | null;
  inverter_max_power_kw: number | null;
  system_loss_percent: number;
  enabled: boolean;
  tilt_estimated: boolean;
  azimuth_estimated: boolean;
  complete: boolean;
  solar_intelligence_enabled?: boolean;
}

export interface SolarAccuracy {
  site_slug: string;
  model_version: string;
  model_state: string;
  mape_7d_pct: number | null;
  mape_30d_pct: number | null;
  mape_7d_valid_days: number;
  mape_30d_valid_days: number;
  mae_kwh_7d: number | null;
  mae_kwh_30d: number | null;
  bias_pct_30d: number | null;
  sample_count_30d: number;
  historical_samples: number;
  production_days_observed: number;
  correction_factor: number;
  confidence_score: number | null;
  confidence_label: string | null;
  metrics_insufficient: boolean;
  raw_mae_30d: number | null;
  corrected_mae_30d: number | null;
  improvement_pct_30d: number | null;
  wape_7d_pct: number | null;
  wape_30d_pct: number | null;
  rmse_kwh_7d: number | null;
  rmse_kwh_30d: number | null;
  r2_30d: number | null;
  insufficient_reason: string | null;
  min_samples_for_calibrated: number;
}

export interface SolarForecastObservation {
  forecast_date: string;
  forecast_kwh_raw: number | null;
  forecast_kwh_corrected: number | null;
  actual_kwh: number | null;
  absolute_error_kwh: number | null;
  raw_absolute_error_kwh: number | null;
  percentage_error: number | null;
  data_completeness_pct: number | null;
  correction_factor_used: number | null;
  weather_condition_bucket: string | null;
  training_eligible: boolean;
  exclusion_reason: string | null;
  model_version: string;
}

export interface SolarDiagnostics {
  site_slug: string;
  observations: SolarForecastObservation[];
}

export async function fetchSolarForecast(slug: string): Promise<SolarForecast> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/forecast`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSolarConfig(slug: string): Promise<SolarSiteConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/config`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function updateSolarConfig(
  slug: string,
  payload: Partial<SolarSiteConfig> & { enabled: boolean },
): Promise<SolarSiteConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSolarAccuracy(slug: string): Promise<SolarAccuracy> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/accuracy`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSolarDiagnostics(slug: string, limit = 60): Promise<SolarDiagnostics> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/solar/diagnostics?limit=${limit}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSolarProviderStatus(
  slug: string,
): Promise<{ providers: Array<{ provider: string; status: string }> }> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/provider-status`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  const data = await res.json();
  return { providers: data.providers ?? [] };
}

export async function fetchSolarModelMetrics(
  slug: string,
): Promise<{ model_version: string | null; wape: number | null } | null> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/model/metrics`, { cache: "no-store" });
  if (!res.ok) return null;
  const data = await res.json();
  return { model_version: data.model_version ?? null, wape: data.wape ?? null };
}

export interface SolarWeatherHour {
  timestamp: string;
  temperature_c: number | null;
  cloud_cover_pct: number | null;
  wind_speed_ms: number | null;
  relative_humidity_pct: number | null;
  precipitation_mm: number | null;
  ghi_wm2: number | null;
  weather_code: number | null;
  condition_sv: string;
  condition_icon: string;
  forecast_power_w?: number | null;
}

export interface SolarWeather {
  site_slug: string;
  provider: string;
  source: string;
  fetched_at: string;
  cache_age_minutes: number;
  sunrise: string | null;
  sunset: string | null;
  current: SolarWeatherHour | null;
  solar_impact_sv: string;
  hours: SolarWeatherHour[];
}

export async function fetchSolarWeather(slug: string): Promise<SolarWeather> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/weather`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface DmiForecastPoint {
  timestamp: string;
  ghi_wm2: number | null;
  dhi_wm2: number | null;
  temperature_c: number | null;
  cloud_cover_pct: number | null;
  precipitation_mm: number | null;
  humidity_pct: number | null;
  wind_speed_ms: number | null;
}

export interface DmiForecast {
  site_slug: string;
  provider: string;
  country_code: string;
  points: DmiForecastPoint[];
}

export async function fetchDmiForecast(slug: string): Promise<DmiForecast> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/dmi/forecast`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface SolarPerformanceDay {
  date: string;
  actual_kwh: number | null;
  expected_kwh: number | null;
  performance_ratio: number | null;
  anomaly_flag: boolean;
}

export interface SolarPerformance {
  site_slug: string;
  days: SolarPerformanceDay[];
  headline_ratio: number | null;
  today_deviation_pct: number | null;
  week_avg: number | null;
  month_avg: number | null;
  quarter_avg: number | null;
  ytd_avg: number | null;
  raw_forecast_so_far_kwh: number | null;
  actual_today_kwh: number | null;
}

export async function fetchSolarPerformance(slug: string): Promise<SolarPerformance> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/solar/performance`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export function isAggregated(
  reading: Reading | AggregatedReading,
): reading is AggregatedReading {
  return "bucket_start" in reading;
}

export interface SpaStatus {
  consumer_id: number;
  site_slug: string;
  online: boolean;
  water_temperature_c: number | null;
  set_temperature_c: number | null;
  heater_active: boolean;
  pump_label: string;
  filter_status: string | null;
  filter_cycle_active?: boolean;
  errors: string[];
  current_power_w: number | null;
  power_breakdown: Record<string, number>;
  power_note_sv: string;
  last_updated: string | null;
  data_source: string;
  data_quality: string;
  integration_enabled: boolean;
}

export interface SpaEnergyPeriod {
  period: string;
  energy_kwh: number;
  actual_cost_sek: number;
  reference_cost_sek: number | null;
  savings_sek: number | null;
  savings_pct: number | null;
  own_energy_pct: number | null;
  solar_direct_kwh: number;
  solar_battery_kwh: number;
  grid_battery_kwh: number;
  grid_direct_kwh: number;
  unknown_kwh: number;
  solar_kwh: number;
  battery_kwh: number;
  grid_kwh: number;
  grid_cost_sek: number;
  solar_value_sek: number;
  battery_value_sek: number;
  max_power_w: number | null;
  avg_power_w: number | null;
  heater_runtime_hours: number;
  pump_runtime_hours: number;
  avg_cost_sek_kwh: number | null;
  has_data: boolean;
}

export interface SpaEnergyBreakdownRow {
  period_start: string;
  period_label: string;
  energy_kwh: number;
  solar_kwh: number;
  battery_kwh: number;
  grid_kwh: number;
  grid_cost_sek: number;
  solar_value_sek: number;
  battery_value_sek: number;
  savings_sek: number | null;
}

export interface SpaEnergyBreakdown {
  period: string;
  granularity: string;
  rows: SpaEnergyBreakdownRow[];
  total: SpaEnergyPeriod;
}

export interface SpaHistoryPoint {
  timestamp: string;
  period_label?: string | null;
  power_w: number | null;
  energy_kwh: number | null;
  cost_sek: number | null;
  solar_kwh?: number | null;
  battery_kwh?: number | null;
  grid_kwh?: number | null;
  grid_cost_sek?: number | null;
  solar_value_sek?: number | null;
  battery_value_sek?: number | null;
  temperature_c: number | null;
  price_sek_kwh: number | null;
}

export interface SpaHistory {
  period: string;
  points: SpaHistoryPoint[];
}

export interface SpaHealth {
  consumer_id: number;
  api_status: string;
  spa_status: string;
  polling_status: string;
  database_status: string;
  last_success_at: string | null;
  last_sample_at: string | null;
  samples_last_24h: number;
  samples_with_power_24h: number;
  sample_energy_kwh_24h: number;
  intervals_last_24h: number;
  data_quality: string;
  measured_pct: number | null;
  calculated_pct: number | null;
  estimated_pct: number | null;
  missing_pct: number | null;
  last_error: string | null;
  actuator_state: string | null;
  integration_degraded: boolean;
  integration_degraded_message_sv: string;
}

export interface SpaConfig {
  consumer_id: number;
  integration_enabled: boolean;
  api_base_url: string;
  masked_api_key: string;
  external_spa_id: string;
  poll_interval_seconds: number;
  energy_collection_enabled: boolean;
  cost_calculation_enabled: boolean;
  timezone: string;
}

export interface SpaConnectionTest {
  success: boolean;
  spa_found: boolean;
  spa_online: boolean;
  message: string;
  last_update: string | null;
  masked_api_key: string;
}

export async function fetchSpaStatus(slug: string): Promise<SpaStatus> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/status`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSpaEnergyPeriod(slug: string, period: string): Promise<SpaEnergyPeriod> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/energy/${period}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSpaEnergyBreakdown(slug: string, period: string): Promise<SpaEnergyBreakdown> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/energy/breakdown?period=${period}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSpaHistory(slug: string, period: string): Promise<SpaHistory> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/history?period=${period}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSpaHealth(slug: string): Promise<SpaHealth> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSpaConfig(slug: string): Promise<SpaConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/config`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateSpaConfig(slug: string, payload: Record<string, unknown>): Promise<SpaConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function testSpaConnection(slug: string): Promise<SpaConnectionTest> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/test-connection`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSpaReadiness(): Promise<{ enabled: boolean; configured_sites: number; online_sites: number; error_sites: number }> {
  const res = await fetch(`${getApiBaseUrl()}/api/system/integrations/spa-readiness`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface SpaControlConfig {
  consumer_id: number;
  smart_control_enabled: boolean;
  strategy: string;
  dry_run: boolean;
  shadow_mode: boolean;
  shadow_mode_until: string | null;
  min_cleaning_hours_per_day: number;
  allowed_window_start: string;
  allowed_window_end: string;
  prefer_solar: boolean;
  allow_battery: boolean;
  min_battery_soc_pct: number;
  min_run_minutes: number;
  min_stop_minutes: number;
  max_starts_per_day: number;
  filter_cycles_per_day: number;
  filter_duration_minutes: number;
  minimum_cycle_separation_minutes: number;
  filter_optimization_enabled: boolean;
  safety_floor_frequency_per_day: number;
  safety_floor_duration_hours: number;
  smart_preheat_enabled: boolean;
  normal_temperature_c: number;
  max_preheat_temperature_c: number;
  min_comfort_temperature_c: number;
  load_priority: number;
  fixed_schedule_start: string | null;
  fixed_schedule_end: string | null;
}

export interface SpaCleaningWindow {
  start: string;
  end: string;
  duration_hours: number;
  energy_source_label_sv: string;
  solar_share_pct: number | null;
}

export interface SpaPlan {
  enabled: boolean;
  consumer_id: number | null;
  load_id: string;
  strategy: string | null;
  next_cleaning_start: string | null;
  next_cleaning_end: string | null;
  duration_hours: number | null;
  planned_energy_source: string | null;
  estimated_energy_kwh: number | null;
  estimated_cost_sek: number | null;
  baseline_cost_sek: number | null;
  savings_sek: number | null;
  explanation_sv: string;
  reason: string | null;
  reason_sv: string | null;
  fallback_from_solar_only: boolean;
  dry_run: boolean;
  data_quality: string;
  blocks: Array<{
    timestamp: string;
    score: number;
    solar_forecast_w: number;
    house_load_forecast_w: number;
    available_surplus_w: number;
    marginal_cost_sek_kwh: number;
    expected_energy_source: string;
    price_estimated: boolean;
  }>;
  daily_windows: SpaCleaningWindow[];
  daily_target_hours: number | null;
  daily_completed_hours: number | null;
  daily_progress_pct: number | null;
  planned_starts: number | null;
  max_starts_per_day: number | null;
  starts_used_today: number | null;
  config_summary_sv: string | null;
  config_validation_warning_sv: string | null;
  filter_control_source_sv?: string | null;
  timing_optimization_source_sv?: string | null;
  filter_policy_summary_sv?: string | null;
  optimization_hint_sv?: string | null;
  cycles_planned?: number | null;
  cycles_completed_today?: number | null;
  hours_planned?: number | null;
  next_cycle_starts_in_minutes?: number | null;
  remaining_cycles_today?: number | null;
}

export interface SpaTimelineEntry {
  timestamp: string;
  hour_label: string;
  action: string;
  action_sv: string;
  load_id: string | null;
  energy_source: string | null;
}

export interface SpaTimeline {
  entries: SpaTimelineEntry[];
}

export interface SpaEnergyEvent {
  id: number;
  timestamp: string;
  event_type: string;
  start_time: string | null;
  stop_time: string | null;
  runtime_seconds: number | null;
  estimated_kwh: number | null;
  actual_kwh: number | null;
  estimated_cost: number | null;
  actual_cost: number | null;
  solar_share: number | null;
  battery_share: number | null;
  grid_share: number | null;
  reason: string;
  reason_sv: string;
  strategy: string;
  decision_score: number | null;
  manual_override: boolean;
  dry_run: boolean;
  data_quality: string;
}

export interface SpaEconomics {
  period: string;
  energy_kwh: number;
  cost_sek: number;
  baseline_cost_sek: number | null;
  savings_sek: number | null;
  solar_share_pct: number | null;
  battery_share_pct: number | null;
  grid_share_pct: number | null;
  data_quality: string;
}

export interface SpaShadow {
  shadow_mode_active: boolean;
  total_actual_cost_sek: number;
  total_optimized_cost_sek: number;
  total_potential_saving_sek: number;
  days: Array<{
    date_label: string;
    actual_cost_sek: number;
    optimized_cost_sek: number;
    potential_saving_sek: number;
  }>;
  integration_degraded?: boolean;
  integration_degraded_message_sv?: string;
}

export async function fetchSpaControlConfig(slug: string): Promise<SpaControlConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/control/config`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function updateSpaControlConfig(slug: string, payload: Partial<SpaControlConfig>): Promise<SpaControlConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/control/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSpaPlan(slug: string): Promise<SpaPlan> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/plan`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSpaTimeline(slug: string): Promise<SpaTimeline> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/timeline`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSpaEvents(slug: string, limit = 50): Promise<{ events: SpaEnergyEvent[]; total: number }> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/events?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSpaEconomics(slug: string, period: string): Promise<SpaEconomics> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/economics?period=${period}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSpaShadow(slug: string): Promise<SpaShadow> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/shadow`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function runSpaCleaningNow(slug: string): Promise<{ success: boolean; message: string; dry_run: boolean }> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/spa/cleaning/run-now`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface EnergyOrchestrationLoad {
  load_id: string;
  name: string;
  load_type: string;
  priority: number;
  strategy: string;
  window_start: string | null;
  window_end: string | null;
  expected_energy_kwh: number | null;
  expected_cost_sek: number | null;
  expected_energy_source: string | null;
  reason_sv: string | null;
  explanation_sv: string | null;
  dry_run: boolean;
}

export interface EnergyOrchestration {
  site_slug: string;
  loads: EnergyOrchestrationLoad[];
}

export async function fetchEnergyOrchestration(slug: string): Promise<EnergyOrchestration> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/energy/orchestration`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function updateEnergyOrchestrationPriorities(
  slug: string,
  loads: Array<{ load_id: string; priority: number }>,
): Promise<EnergyOrchestration> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/energy/orchestration/priorities`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ loads }),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface VehicleCapabilities {
  can_read_soc: boolean | null;
  can_read_range: boolean | null;
  can_read_charging_state: boolean | null;
  can_read_charging_power: boolean | null;
  can_read_target_soc: boolean | null;
  can_read_departure_time: boolean | null;
  can_set_target_soc: boolean | null;
  can_start_charging: boolean | null;
  can_stop_charging: boolean | null;
}

export interface VehicleHaloCorrelation {
  charger_id: number | null;
  confidence: number;
  status: string;
  plugged_agreement: boolean | null;
  charging_agreement: boolean | null;
  power_delta_kw: number | null;
  vehicle_power_kw: number | null;
  halo_power_kw: number | null;
  notes: string;
  updated_at: string | null;
}

export interface VehicleValueEnvelope {
  value: number | boolean | string | null;
  source_timestamp: string | null;
  received_timestamp: string | null;
  age_seconds: number | null;
  quality: string;
}

export interface VehicleListItem {
  id: number;
  site_id: number;
  provider: string;
  display_name: string;
  manufacturer: string;
  model: string;
  masked_vin: string | null;
  enabled: boolean;
  connection_state: string;
  data_quality: string;
  freshness_label: string;
  state_of_charge_percent: number | null;
  target_soc_percent: number | null;
  electric_range_km: number | null;
  is_plugged_in: boolean | null;
  is_charging: boolean | null;
  charging_power_kw: number | null;
  last_vehicle_update: string | null;
  capabilities: VehicleCapabilities;
  halo_correlation: VehicleHaloCorrelation | null;
  state_of_charge?: VehicleValueEnvelope | null;
  charging_power?: VehicleValueEnvelope | null;
  electric_range?: VehicleValueEnvelope | null;
}

export interface VehicleListResponse {
  site_slug: string;
  vehicles: VehicleListItem[];
}

export interface VehicleSyncResponse extends VehicleListResponse {
  synced_at: string;
  vehicles_updated: number;
}

export interface VehicleIntegrationStatus {
  site_slug: string;
  provider: string;
  enabled: boolean;
  region: string;
  username: string;
  password_configured: boolean;
  connection_state: string;
  commands_enabled: boolean;
  token_expires_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
  backoff_until: string | null;
  blocked_since: string | null;
  reconnect_count: number;
  http_429_count: number;
  decode_failure_count: number;
  health: string;
}

export interface VehicleIntegrationConfig {
  site_slug: string;
  provider: string;
  enabled: boolean;
  region: string;
  username: string;
  password_configured: boolean;
  commands_enabled: boolean;
}

export interface VehicleIntegrationLoginResult {
  success: boolean;
  message: string;
}

export interface VehicleEnergySources {
  solar_direct_kwh: number;
  solar_battery_kwh: number;
  grid_battery_kwh: number;
  grid_direct_kwh: number;
}

export interface VehicleChargeSession {
  id: number;
  vehicle_id: number;
  charger_id: number | null;
  connected_at: string;
  disconnected_at: string | null;
  charging_started_at: string | null;
  charging_stopped_at: string | null;
  start_soc: number | null;
  end_soc: number | null;
  target_soc: number | null;
  status: string;
  halo_energy_kwh: number | null;
  estimated_battery_energy_delta_kwh: number | null;
  energy_sources: VehicleEnergySources;
  actual_cost_sek: number | null;
  reference_cost_sek: number | null;
  savings_sek: number | null;
  renewable_share_pct: number | null;
  grid_share_pct: number | null;
  identification_confidence: number | null;
  energy_quality: string | null;
  cost_quality: string | null;
  attribution_quality: string | null;
  location_name?: string | null;
  charger_operator?: string | null;
  charging_type?: string | null;
  home_charging?: boolean | null;
  energy_source?: string | null;
  estimated_energy_kwh?: number | null;
  charging_cost_sek?: number | null;
  cost_source?: string | null;
  detection_confidence?: string | null;
  identification_method?: string | null;
  vehicle_data_quality?: string | null;
  charging_power_avg_kw?: number | null;
  charging_power_max_kw?: number | null;
}

export interface VehicleChargingStats {
  site_slug: string;
  vehicle_id: number | null;
  period: string;
  total_energy_kwh: number;
  home_energy_kwh: number;
  away_energy_kwh: number;
  ac_energy_kwh: number;
  dc_energy_kwh: number;
  free_energy_kwh: number;
  paid_energy_kwh: number;
  avg_price_sek_kwh: number | null;
  total_cost_sek: number;
  savings_vs_public_sek: number | null;
  solar_share_pct: number | null;
  grid_share_pct: number | null;
  session_count: number;
}

export interface VehicleChargeSessionListResponse {
  site_slug: string;
  vehicle_id: number;
  sessions: VehicleChargeSession[];
}

export async function fetchVehicles(slug: string): Promise<VehicleListResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function syncVehicles(slug: string): Promise<VehicleSyncResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/sync`, {
    method: "POST",
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchVehicleIntegrationStatus(slug: string): Promise<VehicleIntegrationStatus> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/integration/status`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchVehicleIntegrationConfig(slug: string): Promise<VehicleIntegrationConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/integration/config`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateVehicleIntegrationConfig(
  slug: string,
  payload: Record<string, unknown>,
): Promise<VehicleIntegrationConfig> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/integration/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function loginVehicleIntegration(slug: string): Promise<VehicleIntegrationLoginResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/integration/login`, { method: "POST" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface VehicleAttributeObservation {
  attribute_name: string;
  source: string;
  value_type: string;
  masked_sample: string;
  first_seen_at: string;
  last_seen_at: string;
  sample_count: number;
}

export interface VehicleRawAttributesResponse {
  site_slug: string;
  vehicle_id?: number | null;
  observations: VehicleAttributeObservation[];
}

export interface VehicleIntegrationDiagnosticsResponse {
  site_slug: string;
  health_status: string;
  connection_state: string;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  last_vehicle_update?: string | null;
  last_token_refresh_at?: string | null;
  consecutive_failures: number;
  last_error_code?: string | null;
  last_latency_ms?: number | null;
  current_polling_interval_seconds?: number | null;
  vehicle_data_age_seconds?: number | null;
  api_data_age_seconds?: number | null;
  recent_events: Array<{
    endpoint: string;
    method: string;
    http_status?: number | null;
    duration_ms: number;
    error_code?: string | null;
    retry_count: number;
    recorded_at: string;
  }>;
}

export interface VehicleIntegrationActionResponse {
  success: boolean;
  message: string;
}

export async function fetchVehicleRawAttributes(
  slug: string,
  vehicleId?: number,
): Promise<VehicleRawAttributesResponse> {
  const query = vehicleId != null ? `?vehicle_id=${vehicleId}` : "";
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/integration/raw-attributes${query}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchVehicleIntegrationDiagnostics(
  slug: string,
): Promise<VehicleIntegrationDiagnosticsResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/integration/diagnostics`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function runVehicleIntegrationAction(
  slug: string,
  action: string,
): Promise<VehicleIntegrationActionResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/integration/actions/${action}`, {
    method: "POST",
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchVehicleChargeSessions(
  slug: string,
  vehicleId: number,
): Promise<VehicleChargeSessionListResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/${vehicleId}/charge-sessions`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchCurrentVehicleChargeSession(
  slug: string,
  vehicleId: number,
): Promise<VehicleChargeSession> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/vehicles/${vehicleId}/charge-sessions/current`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function patchVehicleChargeSession(
  slug: string,
  vehicleId: number,
  sessionId: number,
  payload: Partial<Pick<VehicleChargeSession, "location_name" | "charger_operator" | "charging_type" | "charging_cost_sek" | "home_charging">>,
): Promise<VehicleChargeSession> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/vehicles/${vehicleId}/charge-sessions/${sessionId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchVehicleChargingStats(
  slug: string,
  vehicleId: number,
  period: "day" | "week" | "month" | "year" = "month",
): Promise<VehicleChargingStats> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/vehicles/${vehicleId}/charging-stats?period=${period}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface VehicleCommandResult {
  success: boolean;
  message: string;
  vehicle_id: number;
  command: string;
}

export async function sendVehicleSetTargetSoc(
  slug: string,
  vehicleId: number,
  targetSocPercent: number,
): Promise<VehicleCommandResult> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/vehicles/${vehicleId}/commands/set-target-soc`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_soc_percent: targetSocPercent }),
    },
  );
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function startVehicleCharging(slug: string, vehicleId: number): Promise<VehicleCommandResult> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/vehicles/${vehicleId}/commands/start-charging`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function stopVehicleCharging(slug: string, vehicleId: number): Promise<VehicleCommandResult> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/vehicles/${vehicleId}/commands/stop-charging`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchSiteDashboard(slug: string): Promise<SiteDashboard> {
  const res = await apiFetch(`${getApiBaseUrl()}/api/sites/${slug}/dashboard`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface SiteSnapshot {
  site: { slug: string; name: string; timezone: string };
  generated_at: string;
  age_seconds: number | null;
  freshness: string;
  source_status: Record<string, string>;
  live: Record<string, number | null> | null;
  today: Record<string, number | null>;
  solar: Record<string, number | null>;
  economy: Record<string, number | null>;
  ev: Record<string, unknown>;
}

export async function fetchSiteSnapshot(slug: string): Promise<SiteSnapshot> {
  const res = await apiFetch(`${getApiBaseUrl()}/api/sites/${slug}/snapshot`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface PerformanceCenterMetrics {
  request_count: number;
  cache: { hits: number; misses: number; hit_rate_pct: number };
  slowest_routes: Array<{ route: string; count: number; p50_ms: number; p95_ms: number }>;
  slowest_requests: Array<Record<string, unknown>>;
  slow_queries: Array<{ sql: string; duration_ms: number; route: string }>;
  providers: Array<{ provider: string; calls: number; avg_ms: number; errors: number }>;
  site_snapshots: Array<{
    site_slug: string;
    site_name: string;
    age_seconds: number | null;
    freshness: string;
    generated_at?: string | null;
  }>;
}

export async function fetchPerformanceMetrics(): Promise<PerformanceCenterMetrics> {
  const res = await apiFetch(`${getApiBaseUrl()}/api/system/performance`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface HeartbeatDiscoveryRunResult {
  run_id: number;
  report_text: string;
  setup_classification: string;
  bridge_lifecycle: string;
  resolved_ev_id: string | null;
  confidence_pct: number;
  virtual_bridge_suitable: boolean;
  charging_modes: string[];
  emic_vehicle_lines: string[];
  warnings: string[];
}

export interface HeartbeatBridgeDecision {
  bridge_state: string;
  heartbeat_ev_id: string | null;
  heartbeat_mode: string | null;
  ai_decision: string | null;
  reason: string;
  recorded_at: string;
}

export interface HeartbeatDiscoveryRunDetail {
  id: number;
  status: string;
  system_id: string | null;
  conclusion_class: string | null;
  bridge_lifecycle: string | null;
  resolved_ev_id: string | null;
  confidence_pct: number | null;
  report_text: string;
  report: Record<string, unknown>;
  observations: Array<Record<string, unknown>>;
  started_at: string;
  completed_at: string | null;
}

export interface HeartbeatBridgeStatus {
  heartbeat_connection: string;
  ev_profile: string;
  ev_id: string | null;
  confidence_pct: number | null;
  physical_hb_wallbox: string;
  charge_amps_halo: string;
  halo_online: boolean;
  virtual_bridge: string;
  setup_classification: string | null;
  bridge_lifecycle: string;
  simulation_mode: boolean;
  physical_control: string;
  write_enabled: boolean;
  settings: Record<string, unknown>;
  mappings: Array<Record<string, unknown>>;
}

export interface HeartbeatBridgeSettings {
  site_id: number;
  discovery_enabled: boolean;
  write_enabled: boolean;
  virtual_bridge_enabled: boolean;
  physical_control_enabled: boolean;
  soc_sync_enabled: boolean;
  replay_enabled: boolean;
  simulation_mode: boolean;
  confidence_threshold_pct: number;
  battery_priority_mode: string;
}

export async function runHeartbeatDiscovery(slug: string): Promise<HeartbeatDiscoveryRunResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/heartbeat/discovery/run`, { method: "POST" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchHeartbeatDiscoveryRun(
  slug: string,
  runId: number,
): Promise<HeartbeatDiscoveryRunDetail> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/heartbeat/discovery/runs/${runId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchHeartbeatBridgeStatus(slug: string): Promise<HeartbeatBridgeStatus> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/heartbeat/bridge/status`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchHeartbeatBridgeSettings(slug: string): Promise<HeartbeatBridgeSettings> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/heartbeat/bridge/settings`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function updateHeartbeatBridgeSettings(
  slug: string,
  payload: Partial<HeartbeatBridgeSettings>,
): Promise<HeartbeatBridgeSettings> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/heartbeat/bridge/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function runHeartbeatWriteTest(
  slug: string,
  dryRun: boolean,
): Promise<{
  classification: string;
  http_status?: number | null;
  error?: string | null;
}> {
  const res = await fetch(
    `${getApiBaseUrl()}/api/sites/${slug}/heartbeat/write-test/run?dry_run=${dryRun ? "true" : "false"}`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function runHeartbeatReplay(slug: string): Promise<{ report_text: string }> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/heartbeat/replay/run`, { method: "POST" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function fetchHeartbeatBridgeDecisions(slug: string): Promise<HeartbeatBridgeDecision[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/heartbeat/bridge/decisions`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export interface AppleDevice {
  id: number;
  owner_label: string;
  device_name: string;
  device_type: string;
  token_prefix: string;
  scopes: string;
  default_site_slug: string | null;
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
  status: string;
}

export interface AppleDeviceCreateResult extends AppleDevice {
  token: string;
}

export async function fetchAppleDevices(): Promise<AppleDevice[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/apple-devices`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function createAppleDevice(payload: {
  owner_label: string;
  device_name: string;
  device_type?: string;
  default_site_slug?: string;
}): Promise<AppleDeviceCreateResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/apple-devices`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}

export async function revokeAppleDevice(deviceId: number): Promise<AppleDevice> {
  const res = await fetch(`${getApiBaseUrl()}/api/apple-devices/${deviceId}/revoke`, { method: "POST" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}
