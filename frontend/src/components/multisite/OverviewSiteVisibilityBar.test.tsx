import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OverviewSiteVisibilityBar } from "./OverviewSiteVisibilityBar";

const sites = [
  {
    slug: "akarp",
    name: "Åkarp",
    health: "healthy",
    healthDetail: null,
    available: true,
    live: {
      solarPowerKw: 1,
      consumptionPowerKw: 2,
      gridImportPowerKw: 0,
      gridExportPowerKw: 0,
      batterySocPercent: 80,
      batteryPowerKw: 0,
    },
    today: {
      solarKwh: 1,
      consumptionKwh: 2,
      gridImportKwh: 0,
      gridExportKwh: 0,
      costToday: 1,
      savingsToday: 1,
    },
    error: null,
  },
  {
    slug: "summer-house-denmark",
    name: "Danmark",
    health: "healthy",
    healthDetail: null,
    available: true,
    live: {
      solarPowerKw: 1,
      consumptionPowerKw: 2,
      gridImportPowerKw: 0,
      gridExportPowerKw: 0,
      batterySocPercent: 65,
      batteryPowerKw: 0,
    },
    today: {
      solarKwh: 1,
      consumptionKwh: 2,
      gridImportKwh: 0,
      gridExportKwh: 0,
      costToday: 1,
      savingsToday: 1,
    },
    error: null,
  },
];

describe("OverviewSiteVisibilityBar", () => {
  it("renders site chips and toggles visibility", () => {
    const onToggle = vi.fn();
    render(
      <OverviewSiteVisibilityBar
        sites={sites}
        visibleSlugs={["akarp", "summer-house-denmark"]}
        onToggle={onToggle}
        onShowAll={vi.fn()}
        onIsolate={vi.fn()}
      />,
    );
    expect(screen.getByText("Anläggningar i vyn")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Åkarp/ }));
    expect(onToggle).toHaveBeenCalledWith("akarp");
  });
});
