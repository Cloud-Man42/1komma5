import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VehicleHistorySection } from "./VehicleHistorySection";

describe("VehicleHistorySection", () => {
  it("renders readable session cards with primary fields", () => {
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
            station_name: "Home Åkarp",
            charger_operator: "Charge Amps Halo",
            charging_type: "AC",
            home_charging: true,
            energy_source: "CHARGER_METER",
            detection_confidence: "VERY_HIGH",
            charging_power_avg_kw: 7.4,
            identification_method: "GEOFENCE",
            station_provider: "LOCAL",
          },
        ]}
      />,
    );

    expect(screen.getAllByText("Hemma")).toHaveLength(2);
    expect(screen.getByText("18.5 kWh")).toBeInTheDocument();
    expect(screen.getByText("42.00 kr")).toBeInTheDocument();
    expect(screen.getByText(/Charge Amps Halo · AC/)).toBeInTheDocument();
    expect(screen.queryByRole("columnheader")).not.toBeInTheDocument();
  });

  it("shows unknown away location label instead of Unknown", () => {
    render(
      <VehicleHistorySection
        sessions={[
          {
            id: 2,
            vehicle_id: 1,
            charger_id: null,
            connected_at: "2026-08-31T18:13:00Z",
            disconnected_at: "2026-09-01T06:46:00Z",
            charging_started_at: "2026-08-31T18:27:00Z",
            charging_stopped_at: "2026-09-01T06:46:00Z",
            start_soc: 16,
            end_soc: 31,
            target_soc: null,
            status: "COMPLETED",
            halo_energy_kwh: 0,
            estimated_battery_energy_delta_kwh: 13.5,
            energy_sources: { solar_direct_kwh: 0, solar_battery_kwh: 0, grid_battery_kwh: 0, grid_direct_kwh: 0 },
            actual_cost_sek: 0,
            reference_cost_sek: null,
            savings_sek: null,
            renewable_share_pct: null,
            grid_share_pct: null,
            identification_confidence: null,
            energy_quality: "ESTIMATED",
            cost_quality: "INCOMPLETE",
            attribution_quality: "UNAVAILABLE",
            location_name: "Unknown",
            station_name: null,
            charger_operator: null,
            charging_type: "AC",
            home_charging: false,
            energy_source: "SOC_ESTIMATE",
            detection_confidence: "LOW",
            identification_method: "UNKNOWN",
          },
        ]}
      />,
    );

    expect(screen.getByText("Okänd plats")).toBeInTheDocument();
    expect(screen.getByText("Borta")).toBeInTheDocument();
    expect(screen.getByText(/13\.5 kWh/)).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<VehicleHistorySection sessions={[]} />);
    expect(screen.getByText(/Ingen laddhistorik/)).toBeInTheDocument();
  });
});
