import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { VehicleCommandsPanel } from "@/components/VehicleCommandsPanel";

const mockSendTarget = vi.fn();
const mockStart = vi.fn();
const mockStop = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    sendVehicleSetTargetSoc: (...args: unknown[]) => mockSendTarget(...args),
    startVehicleCharging: (...args: unknown[]) => mockStart(...args),
    stopVehicleCharging: (...args: unknown[]) => mockStop(...args),
  };
});

const vehicle = {
  id: 1,
  site_id: 1,
  provider: "mercedes",
  display_name: "Mercedes EQE",
  manufacturer: "Mercedes-Benz",
  model: "EQE 500",
  masked_vin: "W1K***0001",
  enabled: true,
  connection_state: "CONNECTED",
  data_quality: "MEASURED",
  freshness_label: "LIVE",
  state_of_charge_percent: 47,
  target_soc_percent: 80,
  electric_range_km: 300,
  is_plugged_in: true,
  is_charging: false,
  charging_power_kw: 0,
  last_vehicle_update: null,
  capabilities: {
    can_read_soc: true,
    can_read_range: true,
    can_read_charging_state: true,
    can_read_charging_power: true,
    can_read_target_soc: true,
    can_read_departure_time: true,
    can_set_target_soc: true,
    can_start_charging: true,
    can_stop_charging: true,
  },
  halo_correlation: null,
};

describe("VehicleCommandsPanel", () => {
  it("shows disabled message when commands flag is off", () => {
    render(<VehicleCommandsPanel siteSlug="akarp" vehicle={vehicle} commandsEnabled={false} />);
    expect(screen.getByTestId("vehicle-commands-panel")).toBeInTheDocument();
    expect(screen.getByText(/Kommandon är avstängda/)).toBeInTheDocument();
  });

  it("sends set-target-soc when enabled", async () => {
    mockSendTarget.mockResolvedValue({ success: true, message: "ok", vehicle_id: 1, command: "set_target_soc" });
    const user = userEvent.setup();
    render(<VehicleCommandsPanel siteSlug="akarp" vehicle={vehicle} commandsEnabled={true} />);
    await user.click(screen.getByRole("button", { name: "Sätt mål-SoC" }));
    expect(mockSendTarget).toHaveBeenCalledWith("akarp", 1, 80);
  });
});
