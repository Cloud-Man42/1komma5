import React from "react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { SiteCard } from "./SiteCard";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("SiteCard", () => {
  it("renders site name and metrics", () => {
    render(
      <SiteCard
        site={{
          slug: "akarp",
          name: "Åkarp",
          timezone: "Europe/Stockholm",
          latest_reading: {
            recorded_at: "2026-01-01T12:00:00Z",
            solar_production_w: 1500,
            consumption_w: 800,
            grid_import_w: 0,
            grid_export_w: 700,
            battery_soc_pct: 75,
            battery_power_w: 200,
          },
        }}
      />,
    );

    expect(screen.getByRole("link").getAttribute("href")).toBe("/sites/akarp");
    expect(screen.getByText("Åkarp")).toBeTruthy();
    expect(screen.getByLabelText("Energiflöde visualisering")).toBeTruthy();
    expect(screen.getAllByText("1.5 kW").length).toBeGreaterThan(0);
  });
});

describe("EnergyChart mobile layout", () => {
  beforeEach(() => {
    // Must be a constructible value, not an arrow function: recharts'
    // ResponsiveContainer calls `new ResizeObserver(...)`, and an arrow
    // function has no [[Construct]] slot, so `new` on it throws
    // "is not a constructor". A class literal is used rather than
    // `vi.fn(function () { ... })` because nothing in this file asserts
    // against the observer's calls, so no spy capability is needed.
    vi.stubGlobal(
      "ResizeObserver",
      class ResizeObserverStub {
        observe(): void {}
        unobserve(): void {}
        disconnect(): void {}
      },
    );
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("640px"),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders chart container on narrow viewports", async () => {
    const { EnergyChart } = await import("./EnergyChart");
    const { container } = render(
      <EnergyChart
        readings={[
          {
            bucket_start: "2026-01-01T12:00:00Z",
            recorded_at: "2026-01-01T12:00:00Z",
            solar_production_w: 1000,
            consumption_w: 500,
            grid_import_w: 0,
            grid_export_w: 500,
            battery_soc_pct: 60,
            battery_power_w: 100,
          },
        ]}
      />,
    );
    expect(container.querySelector(".chart-inner")).toBeTruthy();
  });

  it("merges forecast bounds into chart rows", async () => {
    const { mergeChartData } = await import("./EnergyChart");
    const rows = mergeChartData(
      [
        {
          bucket_start: "2026-01-01T12:00:00Z",
          recorded_at: "2026-01-01T12:00:00Z",
          solar_production_w: 1000,
          consumption_w: 500,
          grid_import_w: 0,
          grid_export_w: 500,
          battery_soc_pct: 60,
          battery_power_w: 100,
        },
      ],
      [
        {
          timestamp: "2026-01-01T12:00:00Z",
          baseline_power_w: 900,
          corrected_power_w: 950,
          expected_energy_kwh: 0.25,
          lower_bound_power_w: 700,
          upper_bound_power_w: 1200,
          confidence: 0.8,
          correction_factor: 1.05,
        },
      ],
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].forecastSolar).toBe(950);
    expect(rows[0].forecastLower).toBe(700);
    expect(rows[0].forecastUpper).toBe(1200);
  });
});
