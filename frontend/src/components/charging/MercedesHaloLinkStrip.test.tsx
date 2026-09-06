import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MercedesHaloLinkStrip } from "./MercedesHaloLinkStrip";

describe("MercedesHaloLinkStrip", () => {
  it("renders Mercedes and Halo cards when linked", () => {
    render(
      <MercedesHaloLinkStrip
        reasoning={{
          charger_id: 1,
          bridge_enabled: true,
          charging_active: true,
          charging_mode: "SMART_CHARGE",
          heartbeat_charging_mode: null,
          ev_charge_from_grid_recommended: false,
          ev_target_power_w: 7000,
          pv_power_w: 4000,
          grid_import_w: 0,
          grid_export_w: 0,
          home_consumption_w: 2000,
          battery_soc_pct: 50,
          ev_actual_power_w: 7000,
          current_price_eur_kwh: 0.1,
          price_average_eur_kwh: 0.1,
          price_tier: "green",
          price_would_charge: true,
          price_reason: "",
          smart_charging_state: "charging",
          decision_reason_sv: "Laddar med sol",
          display_status_sv: "Laddar",
          requested_current_a: 16,
          applied_current_a: 16,
          vehicle_connected: true,
          halo_connected: true,
          solar_plan_available: true,
          solar_plan_reason: null,
          solar_first: true,
          active_optimizations: [],
          energy_flow_line: null,
          energy_balance_status: "ok",
          reasoning_steps: [],
          vehicle_linked: true,
          vehicle_display_name: "Mercedes EQE 500",
          vehicle_soc_pct: 55,
          vehicle_target_soc_pct: 80,
          vehicle_required_energy_kwh: 10,
          vehicle_departure_time: "07:00",
          vehicle_energy_quality: "good",
        }}
      />,
    );

    expect(screen.getByText("Mercedes EQE 500")).toBeTruthy();
    expect(screen.getByText(/SOC 55%/)).toBeTruthy();
    expect(screen.getByText(/Laddar med sol/)).toBeTruthy();
  });

  it("returns null when nothing is linked", () => {
    const { container } = render(
      <MercedesHaloLinkStrip
        reasoning={{
          charger_id: 1,
          bridge_enabled: false,
          charging_active: false,
          charging_mode: "PAUSED",
          heartbeat_charging_mode: null,
          ev_charge_from_grid_recommended: false,
          ev_target_power_w: null,
          pv_power_w: null,
          grid_import_w: null,
          grid_export_w: null,
          home_consumption_w: null,
          battery_soc_pct: null,
          ev_actual_power_w: null,
          current_price_eur_kwh: null,
          price_average_eur_kwh: null,
          price_tier: "unknown",
          price_would_charge: false,
          price_reason: "",
          smart_charging_state: null,
          decision_reason_sv: null,
          display_status_sv: null,
          requested_current_a: null,
          applied_current_a: null,
          vehicle_connected: false,
          halo_connected: false,
          solar_plan_available: false,
          solar_plan_reason: null,
          solar_first: false,
          active_optimizations: [],
          energy_flow_line: null,
          energy_balance_status: null,
          reasoning_steps: [],
          vehicle_linked: false,
          vehicle_display_name: null,
          vehicle_soc_pct: null,
          vehicle_target_soc_pct: null,
          vehicle_required_energy_kwh: null,
          vehicle_departure_time: null,
          vehicle_energy_quality: null,
        }}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
