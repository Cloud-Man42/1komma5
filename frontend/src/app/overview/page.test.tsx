import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MultiSiteOverviewPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/overview",
}));

vi.mock("@/lib/SiteSelectionProvider", () => ({
  useSiteSelection: () => ({
    loading: false,
    selectedSlugs: ["akarp", "summer-house-denmark"],
    accessibleSites: [
      { slug: "akarp", name: "Åkarp" },
      { slug: "summer-house-denmark", name: "Danmark" },
    ],
    draftSlugs: ["akarp", "summer-house-denmark"],
    toggleDraft: vi.fn(),
    selectAll: vi.fn(),
    clearAll: vi.fn(),
    applySelection: vi.fn(),
  }),
}));

vi.mock("@/components/multisite/OverviewPowerBalance24h", () => ({
  OverviewPowerBalance24h: () => (
    <section>
      <h2>Generation, grid and battery – 24 hours</h2>
    </section>
  ),
}));

vi.mock("@/lib/useMultiSiteHistory", () => ({
  useMultiSiteHistory: () => ({
    loading: false,
    error: null,
    points: [
      {
        label: "10:00",
        sortKey: 1,
        solarW: 5600,
        gridImportW: 500,
        gridExportW: 1000,
        batteryChargeW: 500,
        batteryDischargeW: 0,
      },
    ],
  }),
}));

vi.mock("@/lib/useMultiSiteOverview", () => ({
  useMultiSiteOverview: () => ({
    loading: false,
    error: null,
    data: {
      generatedAt: new Date().toISOString(),
      sites: [
        {
          slug: "akarp",
          name: "Åkarp",
          currency: "SEK",
          health: "healthy",
          healthDetail: null,
          available: true,
          live: { solarPowerKw: 4.8, consumptionPowerKw: 3.2, gridImportPowerKw: 0, gridExportPowerKw: 1.1, batterySocPercent: 82, batteryPowerKw: 0 },
          today: { solarKwh: 21.4, consumptionKwh: 17.2, gridImportKwh: 0, gridExportKwh: 2, costToday: 112, savingsToday: 20 },
          error: null,
        },
        {
          slug: "summer-house-denmark",
          name: "Danmark",
          currency: "DKK",
          health: "healthy",
          healthDetail: null,
          available: true,
          live: { solarPowerKw: 1.6, consumptionPowerKw: 2.1, gridImportPowerKw: 0.5, gridExportPowerKw: 0, batterySocPercent: 65, batteryPowerKw: 0 },
          today: { solarKwh: 8.7, consumptionKwh: 12.4, gridImportKwh: 1, gridExportKwh: 0, costToday: 74, savingsToday: 10 },
          error: null,
        },
      ],
      aggregate: {
        solarPowerKw: 6.4,
        consumptionPowerKw: 5.3,
        gridImportPowerKw: 0.5,
        gridExportPowerKw: 1.1,
        gridNetPowerKw: 0.6,
        batteryChargePowerKw: null,
        batteryDischargePowerKw: null,
        batteryCapacityKwh: 25,
        batteryStoredKwh: 17,
        batterySocPercent: 68,
        solarTodayKwh: 30.1,
        consumptionTodayKwh: 29.6,
        gridImportTodayKwh: 1,
        gridExportTodayKwh: 2,
        evPowerKw: null,
        bestSolarSiteSlug: "akarp",
        bestSolarSiteKwh: 21.4,
      },
      health: { healthy: 2, degraded: 0, offline: 0 },
      dataQuality: { partial: false, sitesRequested: 2, sitesAvailable: 2, sitesStale: 0, message: null },
      freshness: { freshestAt: new Date().toISOString(), oldestAt: new Date().toISOString(), maxDataAgeSeconds: 30 },
      currencies: [
        { currency: "SEK", costToday: 112, savingsToday: 20 },
        { currency: "DKK", costToday: 74, savingsToday: 10 },
      ],
    },
  }),
}));

describe("MultiSiteOverviewPage", () => {
  it("renders live flow and 24h balance panels", () => {
    render(<MultiSiteOverviewPage />);
    expect(screen.getByText("Multi-Site Overview")).toBeInTheDocument();
    expect(screen.getByText("Anläggningar i vyn")).toBeInTheDocument();
    expect(screen.getByText("Live power flow")).toBeInTheDocument();
    expect(screen.getByText("Generation, grid and battery – 24 hours")).toBeInTheDocument();
    expect(screen.getAllByText("Solar").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Grid").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Åkarp/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Åkarp" })).toBeInTheDocument();
  });
});
