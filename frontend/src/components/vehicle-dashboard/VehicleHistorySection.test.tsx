import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VehicleHistorySection } from "./VehicleHistorySection";

describe("VehicleHistorySection", () => {
  it("renders CSI table columns", () => {
    render(
      <VehicleHistorySection
        sessions={[
          {
            id: 1,
            vehicle_id: 1,
            charger_id: 2,
            connected_at: "2026-08-31T10:00:00Z",
            disconnected_at: "2026-08-31T12:00:00Z",
            charging_started_at: "2026-08-31T10:05:00Z",
            charging_stopped_at: "2026-08-31T11:55:00Z",
            start_soc: 40,
            end_soc: 70,
            target_soc: 80,
            status: "COMPLETED",
            halo_energy_kwh: 18.5,
            estimated_battery_energy_delta_kwh: null,
            energy_sources: { solar_direct_kwh: 5, solar_battery_kwh: 0, grid_battery_kwh: 0, grid_direct_kwh: 13.5 },
            actual_cost_sek: 42,
            reference_cost_sek: 55,
            savings_sek: 13,
            renewable_share_pct: 27,
            grid_share_pct: 73,
            identification_confidence: 0.9,
            energy_quality: "MEASURED",
            cost_quality: "CALCULATED",
            attribution_quality: "CALCULATED",
            location_name: "Home Åkarp",
            charger_operator: "Charge Amps Halo",
            charging_type: "AC",
            home_charging: true,
            energy_source: "CHARGER_METER",
            detection_confidence: "VERY_HIGH",
            charging_power_avg_kw: 7.4,
          },
        ]}
      />,
    );
    expect(screen.getByText("Home Åkarp")).toBeInTheDocument();
    expect(screen.getByText("Charge Amps Halo")).toBeInTheDocument();
    expect(screen.getByText(/VERY HIGH/)).toBeInTheDocument();
    expect(screen.getByText(/CHARGER_METER/)).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<VehicleHistorySection sessions={[]} />);
    expect(screen.getByText(/Ingen laddhistorik/)).toBeInTheDocument();
  });
});
