import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VehicleChargingWidget } from "./VehicleChargingWidget";

describe("VehicleChargingWidget", () => {
  it("shows parked mode with soc and range", () => {
    render(
      <VehicleChargingWidget
        vehicle={{
          available: true,
          display_name: "EQE 350+",
          mode: "parked",
          state_of_charge_percent: 72,
          electric_range_km: 380,
          is_plugged_in: false,
          is_charging: false,
          charging_power_kw: null,
          location_name: "Home Åkarp",
          charging_type: "AC",
          session_energy_kwh: null,
          data_quality: "LIVE",
          freshness_label: "LIVE",
        }}
      />,
    );
    expect(screen.getByText("EQE 350+")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
    expect(screen.getByText(/Home Åkarp/)).toBeInTheDocument();
  });

  it("shows unavailable state", () => {
    render(<VehicleChargingWidget vehicle={{ available: false, unavailable_reason: "Avstängd" }} />);
    expect(screen.getByText(/Avstängd/)).toBeInTheDocument();
  });
});
