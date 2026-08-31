import type { DisplayOverview } from "@/lib/displayOverview";

/**
 * The exact readings shown in the design reference ("Smart Home Energy
 * Dashboard.png"). Used by the visual-comparison preview route and by unit
 * tests so both exercise the same shape the backend returns.
 */

/** Deterministic 0..1 noise so chart shapes are stable across renders. */
function noise(seed: number): number {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

function series(count: number, shape: (t: number, n: number) => number) {
  const points = [];
  const start = Date.UTC(2026, 7, 23, 22, 0, 0);
  for (let i = 0; i < count; i += 1) {
    points.push({
      timestamp: new Date(start + i * 15 * 60 * 1000).toISOString(),
      value: shape(i / (count - 1), noise(i + 1)),
    });
  }
  return { points };
}

/** Solar: overnight zero, then a noisy bell peaking mid-afternoon. */
const solarSeries = series(64, (t, n) => {
  if (t < 0.28) return 0;
  const day = Math.sin(((t - 0.28) / 0.68) * Math.PI);
  return Math.max(0, day * 7600 * (0.72 + n * 0.42));
});

/** House: jagged baseline with morning and evening peaks. */
const houseSeries = series(64, (t, n) => {
  const base = 780 + n * 900;
  const morning = Math.exp(-(((t - 0.32) / 0.05) ** 2)) * 2400;
  const evening = Math.exp(-(((t - 0.86) / 0.07) ** 2)) * 2100;
  return base + morning + evening;
});

/** Battery state of charge: drains overnight, charges through the solar day. */
const batterySeries = series(64, (t, n) => {
  if (t < 0.3) return 22 - t * 18 + n * 2;
  const charge = Math.min(100, 17 + (t - 0.3) * 150);
  return t > 0.82 ? Math.max(40, charge - (t - 0.82) * 220) + n * 2 : charge + n * 2;
});

/** Grid: import overnight (negative), export at solar peak (positive). */
const gridSeries = series(64, (t, n) => {
  if (t < 0.3) return -(900 + n * 700);
  const exportPower = Math.sin(((t - 0.3) / 0.66) * Math.PI) * 5200;
  return exportPower - 700 * n;
});

const economyDaily = Array.from({ length: 28 }, (_, index) => {
  const day = index + 1;
  const n1 = noise(day * 3.1);
  const n2 = noise(day * 7.7);
  const savings = Math.round(40 + n1 * 240);
  const cost = Math.round(30 + n2 * 210);
  return { day, savings_sek: savings, cost_sek: cost, net_sek: savings - cost };
});

export const MOCKUP_OVERVIEW: DisplayOverview = {
  generated_at: "2026-08-24T06:08:07Z",
  site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
  freshness: {
    updated_at: "2026-08-24T06:08:07Z",
    data_age_seconds: 3,
    stale: false,
    connection_state: "CONNECTED",
  },
  live: {
    solar_power_kw: 3.25,
    house_power_kw: 1.78,
    grid_net_power_kw: 1.24,
    grid_direction: "export",
    grid_direction_sv: "Exporterar",
    battery_soc_pct: 58,
    battery_power_kw: 0.46,
    battery_state_sv: "Laddar",
    battery_stored_kwh: 7.8,
    battery_capacity_kwh: 13.5,
    solar_surplus_kw: 1.47,
    produced_today_kwh: 24.7,
    consumed_today_kwh: 16.3,
    imported_today_kwh: 3.1,
    exported_today_kwh: 8.1,
    self_consumption_pct: 87,
    self_sufficiency_pct: 81,
    battery_soh_pct: 100,
  },
  sparklines: {
    solar: solarSeries,
    house: houseSeries,
    battery: batterySeries,
    grid: gridSeries,
  },
  weather: { available: true, temperature_c: 18, label_sv: "Klart", icon: "clear" },
  price: { available: true, tier: "red", tier_label_sv: "Rött (dyrt)", current_ore_kwh: 200.6 },
  flow: {
    available: true,
    nodes: [
      { key: "solar", label_sv: "SOL", power_kw: 3.25, status_sv: null },
      { key: "battery", label_sv: "BATTERI", power_kw: 0.46, status_sv: "Laddar" },
      { key: "grid", label_sv: "NÄT", power_kw: 1.24, status_sv: "Exporterar" },
      { key: "house", label_sv: "HUS", power_kw: 1.78, status_sv: null },
      { key: "charger", label_sv: "LADDBOX", power_kw: 0, status_sv: "Väntar" },
      { key: "spa", label_sv: "SPA", power_kw: 0.6, status_sv: "Standby" },
    ],
  },
  vehicle: {
    available: true,
    display_name: "Mercedes EQE 500",
    model: "Mercedes EQE 500",
    status_sv: "Väntar på bil",
    soc_pct: 78,
    range_km: 412,
    charging_mode_sv: "Smart laddning",
    ready_by: "2026-08-24T06:00:00Z",
    cost_today_sek: 0,
  },
  charger: {
    available: true,
    name: "ChargeAmps Halo",
    status_sv: "Väntar på bil",
    power_w: 0,
    available_current_a: 16,
    smart_charging_active: true,
    ready_by: "2026-08-24T06:00:00Z",
    price_tier_label_sv: "Rött (dyrt)",
  },
  spa: {
    available: true,
    water_temperature_c: 37.4,
    filter_status_sv: "Pågår",
    next_cleaning_at: "2026-08-24T20:00:00Z",
    consumption_today_kwh: 3.2,
    cost_today_sek: 1.28,
    power_w: 600,
  },
  economy: {
    available: true,
    total_savings_sek: 2846,
    total_savings_change_pct: 38,
    total_cost_sek: 1924,
    total_cost_change_pct: -21,
    net_sek: 912,
    net_change_pct: 62,
    daily: economyDaily,
  },
  highlights: {
    available: true,
    items: [
      { label_sv: "Högsta soleffekt", value: "8.8 kW", detail_sv: "12:31" },
      { label_sv: "Batteri laddat från sol", value: "7.2 kWh", detail_sv: null },
      { label_sv: "Export till nätet", value: "8.1 kWh", detail_sv: null },
      { label_sv: "Smart laddning aktiv", value: "0 ses.", detail_sv: null },
      { label_sv: "CO₂ besparing", value: "21.4 kg", detail_sv: null },
    ],
  },
  system_status: {
    status_sv: "Allt normalt",
    detail_sv: "Alla system fungerar som de ska.",
    healthy: true,
  },
};

/** Fixed clock so preview screenshots are byte-stable. */
export const MOCKUP_NOW = new Date("2026-08-24T06:08:07Z");
