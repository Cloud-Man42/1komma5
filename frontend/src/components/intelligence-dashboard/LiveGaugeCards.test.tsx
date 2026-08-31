import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LiveGaugeCards } from "./LiveGaugeCards";

const baseReading = {
  recorded_at: "2026-08-28T13:00:00Z",
  solar_production_w: 540,
  consumption_w: 5370,
  battery_soc_pct: 58,
  battery_power_w: -7130,
};

describe("LiveGaugeCards", () => {
  it("shows NÄT IMPORT when buying from the grid", () => {
    render(
      <LiveGaugeCards
        reading={{ ...baseReading, grid_import_w: 857, grid_export_w: 0 }}
        live={{
          consumption_w: 5370,
          grid_import_w: 857,
          grid_export_w: 0,
          solar_production_w: 540,
          battery_power_w: -7130,
          battery_soc_pct: 58,
          battery_direction: "discharging",
          ev_power_w: 0,
          status: "ok",
          stale: false,
        }}
        sparkSolar={[0, 540]}
        sparkHouse={[5000, 5370]}
        sparkGrid={[800, 857]}
      />,
    );

    expect(screen.getByText("NÄT IMPORT")).toBeTruthy();
    expect(screen.queryByText("EXPORT TILL NÄT")).toBeNull();
  });

  it("shows EXPORT TILL NÄT when selling to the grid", () => {
    render(
      <LiveGaugeCards
        reading={{ ...baseReading, grid_import_w: 0, grid_export_w: 2300 }}
        live={{
          consumption_w: 5370,
          grid_import_w: 0,
          grid_export_w: 2300,
          solar_production_w: 540,
          battery_power_w: -7130,
          battery_soc_pct: 58,
          battery_direction: "discharging",
          ev_power_w: 0,
          status: "ok",
          stale: false,
        }}
        sparkSolar={[0, 540]}
        sparkHouse={[5000, 5370]}
        sparkGrid={[2000, 2300]}
      />,
    );

    expect(screen.getByText("EXPORT TILL NÄT")).toBeTruthy();
    expect(screen.queryByText("NÄT IMPORT")).toBeNull();
  });
});
