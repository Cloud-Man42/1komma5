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

export interface DashboardSolarSection extends DashboardSectionMeta {
  expected_today_kwh: number | null;
  remaining_kwh: number | null;
  peak_power_w: number | null;
  peak_at: string | null;
  confidence_pct: number | null;
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
  reserved_solar_kwh: number | null;
  planned_grid_kwh: number | null;
  ev_need_kwh: number | null;
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
  solar: DashboardSolarSection | null;
  price: DashboardPriceSection | null;
  optimization: DashboardOptimizationSection | null;
  alerts: DashboardAlert[];
  spa_integration_enabled: boolean;
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
  required_energy_kwh?: number | null;
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
  solar_planned_grid_kwh: number | null;
  active_optimizations: string[];
  energy_flow_line: string | null;
  energy_balance_status: string | null;
  reasoning_steps: string[];
}

export interface EvSolarChargingPlan {
  available: boolean;
  expected_usable_solar_kwh: number | null;
  planning_solar_kwh: number | null;
  reserved_solar_kwh: number | null;
  planned_grid_kwh: number | null;
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
}

export interface FinancialStatsResponse {
  slug: string;
  timezone: string;
  period: PeakPeriod;
  fallback_purchase_price_sek_kwh: number;
  export_compensation_sek_kwh: number;
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
): Promise<MarketPricesResponse> {
  const to = new Date();
  const from = new Date(to.getTime() - 60 * 60 * 1000);
  to.setTime(to.getTime() + (hours - 1) * 60 * 60 * 1000);
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
    required_energy_kwh?: number | null;
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
    required_energy_kwh?: number | null;
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

export async function fetchEnergyBalanceHistory(
  slug: string,
  chargerId: number,
  limit = 50,
  offset = 0,
): Promise<EnergyBalanceHistory> {
  const params = new URLSearchParams({
    limit: String(limit),
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
  raw_forecast_tomorrow_kwh?: number | null;
  corrected_forecast_today_kwh?: number;
  corrected_forecast_tomorrow_kwh?: number | null;
  correction_factor?: number;
  model_state?: string;
  confidence_score?: number | null;
  confidence_label?: string | null;
  historical_samples?: number;
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
  correction_factor: number;
  confidence_score: number | null;
  confidence_label: string | null;
  metrics_insufficient: boolean;
  raw_mae_30d: number | null;
  corrected_mae_30d: number | null;
  improvement_pct_30d: number | null;
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
  errors: string[];
  current_power_w: number | null;
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
  max_power_w: number | null;
  avg_power_w: number | null;
  heater_runtime_hours: number;
  pump_runtime_hours: number;
  avg_cost_sek_kwh: number | null;
  has_data: boolean;
}

export interface SpaHistoryPoint {
  timestamp: string;
  power_w: number | null;
  energy_kwh: number | null;
  cost_sek: number | null;
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
  data_quality: string;
  measured_pct: number | null;
  calculated_pct: number | null;
  estimated_pct: number | null;
  missing_pct: number | null;
  last_error: string | null;
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

export async function fetchSiteDashboard(slug: string): Promise<SiteDashboard> {
  const res = await fetch(`${getApiBaseUrl()}/api/sites/${slug}/dashboard`, { cache: "no-store" });
  if (!res.ok) throw new Error(await readApiError(res));
  return res.json();
}
