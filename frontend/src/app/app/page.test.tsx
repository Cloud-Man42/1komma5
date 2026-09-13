import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MobileHomePage from "./page";

vi.mock("@/lib/SiteSelectionProvider", () => ({
  useSiteSelection: () => ({
    loading: false,
    selectedSlugs: ["akarp", "summer-house-denmark"],
    accessibleSites: [
      { slug: "akarp", name: "Åkarp" },
      { slug: "summer-house-denmark", name: "Danmark" },
    ],
  }),
}));

vi.mock("@/lib/useMobileSummary", () => ({
  useMobileSummary: () => ({
    loading: false,
    error: null,
    online: true,
    data: {
      sites: [
        {
          slug: "akarp",
          name: "Åkarp",
          health: "healthy",
          live: { solarPowerKw: 4.8, consumptionPowerKw: 3.2, gridImportPowerKw: 0, gridExportPowerKw: 1.1, batterySocPercent: 82, batteryPowerKw: 0 },
          today: { solarKwh: 21.4, consumptionKwh: 17.2, gridImportKwh: 0, gridExportKwh: 2, costToday: 112, savingsToday: 20 },
        },
      ],
      aggregate: {
        solarPowerKw: 6.2,
        consumptionPowerKw: 8.4,
        gridImportPowerKw: 1.1,
        gridExportPowerKw: 0,
        batteryChargePowerKw: null,
        batteryDischargePowerKw: 1.1,
        batteryCapacityKwh: 25,
        batteryStoredKwh: 17,
        batterySocPercent: 68,
        solarTodayKwh: 28.4,
        consumptionTodayKwh: 36.8,
        gridImportTodayKwh: 11.2,
        gridExportTodayKwh: 2.8,
      },
      health: { healthy: 2, degraded: 0, offline: 0 },
      dataQuality: { partial: false, message: null },
      currencies: [{ currency: "SEK", costToday: 123, savingsToday: 45 }],
      freshnessLabel: "Live",
      warnings: [],
      quickActions: [{ id: "sites", label: "Sites", route: "/app/sites" }],
    },
  }),
}));

describe("MobileHomePage", () => {
  it("renders hero summary and today section", () => {
    render(<MobileHomePage />);
    expect(screen.getByText("Total power now")).toBeInTheDocument();
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Energy flow")).toBeInTheDocument();
    expect(screen.getByText("Quick actions")).toBeInTheDocument();
  });
});
