"use client";

import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VehiclePanel } from "@/components/VehiclePanel";

vi.mock("@/lib/useDashboardRefresh", () => ({
  useDashboardRefreshSeconds: () => 30,
}));

describe("VehiclePanel", () => {
  it("shows disabled message when integration is off", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/vehicles/integration/status")) {
          return new Response(JSON.stringify({ enabled: false }), { status: 200 });
        }
        return new Response(JSON.stringify({ vehicles: [] }), { status: 200 });
      }),
    );

    render(<VehiclePanel siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("vehicle-panel")).toBeInTheDocument();
    });
    expect(screen.getByText(/inte aktiverad/i)).toBeInTheDocument();
  });

  it("renders live vehicle metrics", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/vehicles/integration/status")) {
          return new Response(
            JSON.stringify({
              enabled: true,
              connection_state: "CONNECTED",
              health: "HEALTHY",
              region: "Europe",
              reconnect_count: 0,
              http_429_count: 0,
              decode_failure_count: 0,
              commands_enabled: false,
            }),
            { status: 200 },
          );
        }
        if (url.includes("/charge-sessions/current")) {
          return new Response(JSON.stringify({ id: 1, status: "ACTIVE" }), { status: 404 });
        }
        if (url.includes("/charge-sessions")) {
          return new Response(JSON.stringify({ site_slug: "akarp", vehicle_id: 1, sessions: [] }), {
            status: 200,
          });
        }
        return new Response(
          JSON.stringify({
            vehicles: [
              {
                id: 1,
                site_id: 1,
                provider: "mock",
                display_name: "EQE 500",
                manufacturer: "Mercedes-Benz",
                model: "EQE 500",
                masked_vin: "W1K***1234",
                enabled: true,
                connection_state: "CONNECTED",
                data_quality: "MEASURED",
                freshness_label: "LIVE",
                state_of_charge_percent: 34,
                target_soc_percent: 80,
                electric_range_km: 220,
                is_plugged_in: true,
                is_charging: true,
                charging_power_kw: 7.4,
                last_vehicle_update: new Date().toISOString(),
                capabilities: {
                  can_read_soc: true,
                  can_read_range: true,
                  can_read_charging_state: true,
                  can_read_charging_power: true,
                  can_read_target_soc: true,
                  can_read_departure_time: null,
                  can_set_target_soc: null,
                  can_start_charging: null,
                  can_stop_charging: null,
                },
                halo_correlation: {
                  charger_id: 3,
                  confidence: 0.92,
                  status: "ALIGNED",
                  plugged_agreement: true,
                  charging_agreement: true,
                  power_delta_kw: 0.3,
                  vehicle_power_kw: 7.4,
                  halo_power_kw: 7.1,
                  notes: "Mercedes och Halo rapporterar överensstämmande laddning",
                  updated_at: new Date().toISOString(),
                },
              },
            ],
          }),
          { status: 200 },
        );
      }),
    );

    render(<VehiclePanel siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("vehicle-card-1")).toBeInTheDocument();
    });
    expect(screen.getByText("LIVE")).toBeInTheDocument();
    expect(screen.getByText("34 %")).toBeInTheDocument();
    expect(screen.getByTestId("vehicle-halo-correlation")).toBeInTheDocument();
    expect(screen.getByText("92 %")).toBeInTheDocument();
    expect(screen.getByTestId("vehicle-charge-sessions")).toBeInTheDocument();
  });
});
