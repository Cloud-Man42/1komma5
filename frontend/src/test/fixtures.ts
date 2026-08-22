import type {
  EvCharger,
  Reading,
  Site,
  SolarSiteConfig,
} from "@/lib/api";

export function makeSite(overrides: Partial<Site> = {}): Site {
  return {
    slug: "akarp",
    name: "Åkarp",
    timezone: "Europe/Stockholm",
    main_fuse_a: 20,
    fallback_purchase_price_sek_kwh: 2,
    export_compensation_sek_kwh: 0.8,
    external_system_id: null,
    latest_reading: null,
    ...overrides,
  };
}

export function makeEvCharger(overrides: Partial<EvCharger> = {}): EvCharger {
  return {
    id: 1,
    site_slug: "akarp",
    name: "Halo",
    manufacturer: "ChargeAmps",
    model: "Halo",
    control_source: "chargeamp",
    bridge_enabled: true,
    chargeamp_charger_id: "mock-halo",
    heartbeat_ev_id: null,
    heartbeat_charger_id: null,
    max_current_a: 16,
    min_current_a: 6,
    phases: 3,
    nominal_voltage_v: 230,
    max_power_w: null,
    max_grid_import_w: null,
    update_interval_seconds: 30,
    min_change_interval_seconds: 60,
    current_hysteresis_a: 1,
    stale_timeout_seconds: 300,
    chargeamps_api_key_configured: true,
    last_applied_current_a: null,
    last_bridge_run_at: null,
    last_heartbeat_data_at: null,
    charging_mode: "SMART_CHARGE",
    departure_time: null,
    target_soc_pct: null,
    manual_soc_pct: null,
    override_active: false,
    override_until: null,
    power_w: null,
    available_modes: ["SMART_CHARGE", "PRICE_CHARGE", "QUICK_CHARGE", "SOLAR_CHARGE", "PAUSED"],
    ...overrides,
  };
}

export function makeSolarConfig(overrides: Partial<SolarSiteConfig> = {}): SolarSiteConfig {
  return {
    site_slug: "akarp",
    enabled: false,
    complete: false,
    latitude: null,
    longitude: null,
    installed_peak_power_kw: null,
    azimuth_deg: null,
    tilt_deg: null,
    inverter_max_power_kw: null,
    system_loss_percent: 14,
    tilt_estimated: false,
    azimuth_estimated: false,
    ...overrides,
  };
}

export function makeReading(overrides: Partial<Reading> = {}): Reading {
  return {
    recorded_at: "2026-08-18T10:00:00Z",
    solar_production_w: 5000,
    consumption_w: 1200,
    grid_import_w: 0,
    grid_export_w: 3800,
    battery_soc_pct: 55,
    battery_power_w: 0,
    ...overrides,
  };
}
