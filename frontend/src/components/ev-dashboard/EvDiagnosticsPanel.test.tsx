import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EvDiagnosticsPanel } from "./EvDiagnosticsPanel";
import type { EnergyReasoning, EvBridgeStatus } from "@/lib/api";

const mockFetchEnergyBalance = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchEnergyBalance: (...args: unknown[]) => mockFetchEnergyBalance(...args),
  };
});

const bridge: EvBridgeStatus = {
  charger_id: 1,
  bridge_enabled: true,
  charging_mode: "SMART_CHARGE",
  active_policy: "SMART",
  ev_target_power_w: null,
  requested_current_a: 16,
  applied_current_a: 16,
  previous_current_a: null,
  last_heartbeat_data_at: "2026-09-06T10:00:00Z",
  last_bridge_run_at: "2026-09-06T10:01:00Z",
  halo_connected: true,
  vehicle_connected: false,
  decision_reason: "Väntar på bättre pris",
  discovery_hints: [],
  stale: false,
  override_active: false,
  override_until: null,
  display_status_sv: "Väntar på bil",
};

const reasoning: EnergyReasoning = {
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
  decision_reason: "expensive",
  decision_reason_sv: "Dyrt just nu",
  display_status_sv: "Väntar på bil",
  requested_current_a: 16,
  applied_current_a: 16,
  vehicle_connected: false,
  halo_connected: true,
  solar_plan_available: true,
  solar_plan_reason: null,
  solar_first: false,
  active_optimizations: [],
  energy_flow_line: "Sol → batteri → hus",
  energy_balance_status: "ok",
  reasoning_steps: ["Prisnivå röd", "Väntar på solfönster"],
  vehicle_linked: true,
  vehicle_display_name: "Mercedes EQE 500",
  vehicle_soc_pct: 55,
  vehicle_target_soc_pct: 80,
  vehicle_required_energy_kwh: 20,
  vehicle_departure_time: "07:00",
  vehicle_energy_quality: "good",
};

beforeEach(() => {
  mockFetchEnergyBalance.mockResolvedValue({
    charger_id: 1,
    recorded_at: "2026-09-06T10:01:00Z",
    status: "OK",
    flags: [],
    inverter_display_name: "Sungrow",
    sungrow_pv_power_w: 4200,
    sungrow_load_power_w: 1800,
    sungrow_grid_import_w: 0,
    sungrow_grid_export_w: 2400,
    sungrow_battery_charge_w: null,
    sungrow_battery_discharge_w: null,
    sungrow_battery_soc_pct: 62,
    sungrow_fresh: true,
    sungrow_telemetry_age_seconds: 12,
    halo_power_w: 0,
    virtual_evse_reported_power_w: 0,
    heartbeat_observed_ev_power_w: 0,
    heartbeat_home_consumption_w: 1500,
    non_ev_house_load_w: 1500,
    non_ev_house_load_reason: null,
    residual_w: 50,
    alignment_delta_seconds: 2,
    energy_flow_line: "Sol → export",
  });
});

describe("EvDiagnosticsPanel", () => {
  it("renders bridge and energy balance diagnostics", async () => {
    render(
      <EvDiagnosticsPanel
        siteSlug="akarp"
        chargerId={1}
        bridge={bridge}
        reasoning={reasoning}
        refreshSeconds={30}
      />,
    );

    const panel = await screen.findByTestId("ev-diagnostics-panel");
    expect(within(panel).getByText(/Virtual EV bridge/i)).toBeTruthy();
    expect(within(panel).getByText(/Halo: Online/i)).toBeTruthy();
    expect(within(panel).getByText(/PV:/)).toBeTruthy();
    expect(within(panel).getByText(/Prisnivå röd/)).toBeTruthy();
    expect(mockFetchEnergyBalance).toHaveBeenCalledWith("akarp", 1);
  });

  it("shows error when energy balance fetch fails", async () => {
    mockFetchEnergyBalance.mockRejectedValueOnce(new Error("503"));
    render(
      <EvDiagnosticsPanel
        siteSlug="akarp"
        chargerId={1}
        bridge={bridge}
        reasoning={reasoning}
        refreshSeconds={30}
      />,
    );
    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("503");
    });
  });

  it("shows balance status badge for non-OK states", async () => {
    mockFetchEnergyBalance.mockResolvedValueOnce({
      charger_id: 1,
      recorded_at: "2026-09-06T10:01:00Z",
      status: "MISALIGNED",
      flags: ["stale_halo"],
      inverter_display_name: "Sungrow",
      sungrow_pv_power_w: null,
      sungrow_load_power_w: null,
      sungrow_grid_import_w: null,
      sungrow_grid_export_w: null,
      sungrow_battery_charge_w: null,
      sungrow_battery_discharge_w: null,
      sungrow_battery_soc_pct: null,
      sungrow_fresh: false,
      sungrow_telemetry_age_seconds: null,
      halo_power_w: null,
      virtual_evse_reported_power_w: null,
      heartbeat_observed_ev_power_w: null,
      heartbeat_home_consumption_w: null,
      non_ev_house_load_w: null,
      non_ev_house_load_reason: "Saknar Halo-data",
      residual_w: null,
      alignment_delta_seconds: null,
      energy_flow_line: null,
    });

    render(
      <EvDiagnosticsPanel
        siteSlug="akarp"
        chargerId={1}
        bridge={bridge}
        reasoning={null}
        refreshSeconds={30}
      />,
    );

    expect((await screen.findByTestId("ev-balance-status-badge")).textContent).toContain("MISALIGNED");
    expect(screen.getByText(/Saknar Halo-data/)).toBeTruthy();
  });
});
