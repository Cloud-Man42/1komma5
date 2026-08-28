import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EvOverview } from "./EvOverview";
import { makeEvCharger } from "@/test/fixtures";

vi.mock("next/image", () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img alt="" {...props} />,
}));

const mockFetchEvChargers = vi.fn();
const mockFetchEvBridgeStatus = vi.fn();
const mockFetchEvSolarChargingPlan = vi.fn();
const mockFetchEvChargerSavings = vi.fn();
const mockFetchEvChargingStats = vi.fn();
const mockFetchEvChargingSessions = vi.fn();
const mockFetchEnergyBalanceHistory = vi.fn();
const mockFetchEnergyReasoning = vi.fn();
const mockFetchSiteDashboard = vi.fn();
const mockFetchSiteEnergyConfig = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchEvChargers: (...args: unknown[]) => mockFetchEvChargers(...args),
    fetchEvBridgeStatus: (...args: unknown[]) => mockFetchEvBridgeStatus(...args),
    fetchEvSolarChargingPlan: (...args: unknown[]) => mockFetchEvSolarChargingPlan(...args),
    fetchEvChargerSavings: (...args: unknown[]) => mockFetchEvChargerSavings(...args),
    fetchEvChargingStats: (...args: unknown[]) => mockFetchEvChargingStats(...args),
    fetchEvChargingSessions: (...args: unknown[]) => mockFetchEvChargingSessions(...args),
    fetchEnergyBalanceHistory: (...args: unknown[]) => mockFetchEnergyBalanceHistory(...args),
    fetchEnergyReasoning: (...args: unknown[]) => mockFetchEnergyReasoning(...args),
    fetchSiteDashboard: (...args: unknown[]) => mockFetchSiteDashboard(...args),
    fetchSiteEnergyConfig: (...args: unknown[]) => mockFetchSiteEnergyConfig(...args),
  };
});

vi.mock("@/lib/useDashboardRefresh", () => ({
  useDashboardRefreshSeconds: () => 30,
}));

const charger = makeEvCharger({ power_w: 0, deadline_at: "2026-08-24T08:00:00Z" });

beforeEach(() => {
  mockFetchEvChargers.mockResolvedValue([charger]);
  mockFetchEvBridgeStatus.mockResolvedValue({
    charger_id: 1,
    bridge_enabled: true,
    charging_mode: "SMART_CHARGE",
    active_policy: "SMART",
    ev_target_power_w: null,
    requested_current_a: 16,
    applied_current_a: 16,
    previous_current_a: null,
    last_heartbeat_data_at: new Date().toISOString(),
    last_bridge_run_at: new Date().toISOString(),
    halo_connected: true,
    vehicle_connected: false,
    decision_reason: null,
    discovery_hints: [],
    stale: false,
    override_active: false,
    override_until: null,
    display_status_sv: "Väntar på bil",
  });
  mockFetchEvSolarChargingPlan.mockResolvedValue({
    available: true,
    expected_usable_solar_kwh: 5,
    planning_solar_kwh: 5,
    solar_first: true,
    quality: "MEDIUM",
    confidence: 61,
    expected_solar_window_start: "2026-08-28T07:00:00Z",
    expected_solar_window_end: "2026-08-28T16:00:00Z",
    cheapest_grid_window: "12:00–16:00",
    explanation_sv: "För lite solöverskott väntas innan deadline.",
    reason_code: null,
  });
  mockFetchEvChargerSavings.mockResolvedValue({
    charger_id: 1,
    period_from: "2026-08-01",
    period_to: "2026-08-31",
    energy_kwh: 20.9,
    actual_cost_sek: 8,
    baseline_cost_sek: 40,
    savings_sek: 32.82,
    savings_ore: 3282,
    savings_pct: 73,
    charging_intervals: 10,
    period_avg_price_kwh: 0.19,
    has_data: true,
  });
  mockFetchEvChargingStats.mockResolvedValue({
    period: "day",
    period_from: "2026-08-28",
    period_to: "2026-08-28",
    total_energy_kwh: 0,
    actual_cost_sek: 0,
    reference_cost_sek: 0,
    savings_sek: 0,
    average_cost_sek_per_kwh: 0.19,
    energy_sources: {
      solar_direct_kwh: 0,
      solar_battery_kwh: 0,
      grid_battery_kwh: 0,
      grid_direct_kwh: 0,
    },
    renewable_share_percent: 0,
    grid_share_percent: 0,
    smart_charging_savings_sek: 0,
    solar_contribution_sek: 0,
    session_count: 0,
    savings_baseline: "immediate",
  });
  mockFetchEvChargingSessions.mockResolvedValue([]);
  mockFetchEnergyBalanceHistory.mockResolvedValue({ items: [], total: 0 });
  mockFetchEnergyReasoning.mockResolvedValue({
    charger_id: 1,
    bridge_enabled: true,
    charging_active: false,
    charging_mode: "SMART_CHARGE",
    heartbeat_charging_mode: null,
    ev_charge_from_grid_recommended: true,
    ev_target_power_w: null,
    pv_power_w: 500,
    grid_import_w: 0,
    grid_export_w: 1000,
    home_consumption_w: 1500,
    battery_soc_pct: 58,
    ev_actual_power_w: 0,
    current_price_eur_kwh: 0.18,
    price_average_eur_kwh: 0.1,
    price_tier: "red",
    price_would_charge: false,
    price_reason: "dyrt",
    smart_charging_state: "waiting",
    decision_reason_sv: "För lite solöverskott väntas innan deadline.",
    display_status_sv: "Väntar på bil",
    requested_current_a: 16,
    applied_current_a: 16,
    vehicle_connected: false,
    halo_connected: true,
    solar_plan_available: true,
    solar_plan_reason: null,
    solar_first: false,
    active_optimizations: [],
    energy_flow_line: null,
    energy_balance_status: "ok",
    reasoning_steps: [],
    vehicle_linked: true,
    vehicle_display_name: "Mercedes EQE 500",
    vehicle_soc_pct: 55,
    vehicle_target_soc_pct: 80,
    vehicle_required_energy_kwh: 20,
    vehicle_departure_time: "07:00",
    vehicle_energy_quality: "good",
  });
  mockFetchSiteDashboard.mockResolvedValue({
    site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
    freshness: { updated_at: new Date().toISOString(), data_age_seconds: 10, stale: false },
    live: null,
    today: null,
    ev: { available: true, charging: false, charging_mode: null, display_status_sv: null, power_w: 0, session_energy_kwh: null, solar_share_pct: null, estimated_cost_sek: null, next_planned_charge_at: null, status: "ok", stale: false },
    solar: null,
    price: null,
    optimization: null,
    alerts: [],
    spa_integration_enabled: false,
    vehicle_integration_enabled: true,
  });
  mockFetchSiteEnergyConfig.mockResolvedValue({
    site_slug: "akarp",
    load_includes_ev_charger: false,
    inverter_display_name: "Sungrow",
    physical_ev_charger_label: "ChargeAmps Halo",
    ev_vehicle_label: "Mercedes EQE 500",
  });
});

describe("EvOverview", () => {
  it("renders laddbox dashboard with key panels", async () => {
    render(<EvOverview siteSlug="akarp" />);
    expect(await screen.findByTestId("ev-overview")).toBeTruthy();
    expect(screen.getByText(/LADDBOX – CHARGEAMPS HALO/i)).toBeTruthy();
    expect(screen.getByTestId("ev-power-panel")).toBeTruthy();
    expect(screen.getByTestId("ev-waiting-panel")).toBeTruthy();
    expect(screen.getByTestId("ev-mini-stats")).toBeTruthy();
    expect(screen.getByTestId("ev-sessions-table")).toBeTruthy();
    expect(screen.getByTestId("ev-manual-control")).toBeTruthy();
  });

  it("shows empty state without chargers", async () => {
    mockFetchEvChargers.mockResolvedValueOnce([]);
    render(<EvOverview siteSlug="akarp" />);
    expect(await screen.findByText(/Inga laddboxar konfigurerade/i)).toBeTruthy();
  });

  it("shows error when charger load fails", async () => {
    mockFetchEvChargers.mockRejectedValueOnce(new Error("offline"));
    render(<EvOverview siteSlug="akarp" />);
    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("offline");
    });
  });
});
