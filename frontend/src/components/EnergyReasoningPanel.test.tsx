import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import EnergyReasoningPanel from "@/components/EnergyReasoningPanel";

const mockFetchEnergyReasoning = vi.fn();
const mockControlEvCharger = vi.fn();
const mockUpdateEvCharger = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchEnergyReasoning: (...args: unknown[]) => mockFetchEnergyReasoning(...args),
    controlEvCharger: (...args: unknown[]) => mockControlEvCharger(...args),
    updateEvCharger: (...args: unknown[]) => mockUpdateEvCharger(...args),
  };
});

const reasoning = {
  charger_id: 4,
  bridge_enabled: true,
  charging_active: true,
  charging_mode: "SMART_CHARGE",
  heartbeat_charging_mode: "SMART_CHARGE",
  ev_charge_from_grid_recommended: true,
  ev_target_power_w: 7200,
  pv_power_w: 5000,
  grid_import_w: 0,
  grid_export_w: 2500,
  home_consumption_w: 2100,
  battery_soc_pct: 65,
  ev_actual_power_w: 0,
  current_price_eur_kwh: 0.2,
  price_average_eur_kwh: 0.45,
  price_tier: "green",
  price_would_charge: true,
  price_reason: "cheap_now",
  smart_charging_state: "WAITING_TO_START",
  decision_reason: "cheap_now",
  decision_reason_sv: "Laddar smart",
  display_status_sv: "Laddar smart",
  requested_current_a: 16,
  applied_current_a: 0,
  vehicle_connected: true,
  halo_connected: true,
  solar_plan_available: false,
  solar_plan_reason: null,
  solar_first: false,
  active_optimizations: ["EV_CHARGE_FROM_GRID"],
  energy_flow_line: "PV 5.0kW → Load 2.1kW | EV 0.0kW",
  energy_balance_status: "OK",
  reasoning_steps: [
    "Elprisnivå: grönt (billigt).",
    "Prisregel säger ladda (cheap_now).",
  ],
  vehicle_linked: false,
  vehicle_display_name: null,
  vehicle_soc_pct: null,
  vehicle_target_soc_pct: null,
  vehicle_required_energy_kwh: null,
  vehicle_departure_time: null,
  vehicle_energy_quality: null,
};

describe("EnergyReasoningPanel", () => {
  beforeEach(() => {
    mockFetchEnergyReasoning.mockReset();
    mockControlEvCharger.mockReset();
    mockUpdateEvCharger.mockReset();
    mockFetchEnergyReasoning.mockResolvedValue(reasoning);
    mockControlEvCharger.mockResolvedValue({});
    mockUpdateEvCharger.mockResolvedValue({});
  });

  it("renders heartbeat and EMIC reasoning sections", async () => {
    render(<EnergyReasoningPanel siteSlug="akarp" chargerId={4} refreshSeconds={30} />);

    await waitFor(() => {
      expect(screen.getByTestId("energy-reasoning-panel")).toBeInTheDocument();
    });

    expect(screen.getByText(/Heartbeat \(indata\)/)).toBeInTheDocument();
    expect(screen.getByText(/EMIC \(beslut\)/)).toBeInTheDocument();
    expect(screen.getByText(/Resonemang steg för steg/)).toBeInTheDocument();
    expect(screen.getByText(/EV_CHARGE_FROM_GRID/)).toBeInTheDocument();
  });

  it("renders vehicle smart charging block when linked", async () => {
    mockFetchEnergyReasoning.mockResolvedValue({
      ...reasoning,
      vehicle_linked: true,
      vehicle_display_name: "Mercedes EQE",
      vehicle_soc_pct: 47,
      vehicle_target_soc_pct: 80,
      vehicle_required_energy_kwh: 29.7,
      vehicle_departure_time: "07:30",
      vehicle_energy_quality: "ESTIMATED",
    });
    render(<EnergyReasoningPanel siteSlug="akarp" chargerId={4} refreshSeconds={30} />);
    await waitFor(() => {
      expect(screen.getByTestId("energy-reasoning-vehicle")).toBeInTheDocument();
    });
    expect(screen.getByText(/Mercedes EQE/)).toBeInTheDocument();
    expect(screen.getByText(/29\.7 kWh/)).toBeInTheDocument();
  });

  it("pauses charging when toggled off", async () => {
    const user = userEvent.setup();
    render(<EnergyReasoningPanel siteSlug="akarp" chargerId={4} refreshSeconds={30} />);

    await waitFor(() => {
      expect(screen.getByTestId("energy-reasoning-settings")).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Laddning aktiv"), "false");
    await user.click(screen.getByRole("button", { name: "Spara laddningsläge" }));

    await waitFor(() => {
      expect(mockControlEvCharger).toHaveBeenCalledWith("akarp", 4, { charging_mode: "PAUSED" });
    });
  });
});
