import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EnergyFlowChartPanel } from "./EnergyPanels";
import { EnergyOverview } from "./EnergyOverview";

vi.mock("next/dynamic", () => ({
  default: () => EnergyFlowChartPanel,
}));

const mockFetchSiteDashboard = vi.fn();
const mockFetchSiteHistory = vi.fn();
const mockFetchSitePeaks = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchSiteDashboard: (...args: unknown[]) => mockFetchSiteDashboard(...args),
    fetchSiteHistory: (...args: unknown[]) => mockFetchSiteHistory(...args),
    fetchSitePeaks: (...args: unknown[]) => mockFetchSitePeaks(...args),
  };
});

const dashboard = {
  site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
  freshness: { updated_at: new Date().toISOString(), data_age_seconds: 10, stale: false },
  live: {
    solar_production_w: 540,
    consumption_w: 1780,
    grid_import_w: 0,
    grid_export_w: 1240,
    battery_soc_pct: 58,
    battery_power_w: -460,
    battery_direction: "charging" as const,
    ev_power_w: 0,
    status: "ok",
    stale: false,
  },
  today: {
    produced_kwh: 8.8,
    consumed_kwh: 9.7,
    imported_kwh: 0,
    exported_kwh: 8.1,
    energy_cost_sek: 0,
    savings_sek: 0,
    status: "ok",
    stale: false,
  },
  ev: null,
  solar: null,
  price: null,
  optimization: null,
  alerts: [],
  spa_integration_enabled: false,
  vehicle_integration_enabled: false,
};

const history = {
  slug: "akarp",
  bucket_minutes: 15,
  readings: [
    {
      recorded_at: "2026-08-27T08:00:00Z",
      solar_production_w: 500,
      consumption_w: 1200,
      grid_import_w: 700,
      grid_export_w: 0,
      battery_soc_pct: 55,
      battery_power_w: 200,
    },
    {
      recorded_at: "2026-08-27T08:15:00Z",
      solar_production_w: 800,
      consumption_w: 1500,
      grid_import_w: 0,
      grid_export_w: 100,
      battery_soc_pct: 58,
      battery_power_w: -300,
    },
  ],
};

beforeEach(() => {
  mockFetchSiteDashboard.mockResolvedValue(dashboard);
  mockFetchSiteHistory.mockResolvedValue(history);
  mockFetchSitePeaks.mockImplementation(async (_slug: string, period: string) => ({
    slug: "akarp",
    timezone: "Europe/Stockholm",
    period,
    peaks: [
      {
        period_start: period === "year" ? "2026" : "2026-08-27",
        solar_production_w: 8800,
        consumption_w: 9700,
        battery_charge_w: 9400,
        battery_discharge_w: 9700,
      },
    ],
  }));
});

describe("EnergyOverview", () => {
  it("renders energy dashboard with live metrics and peaks table", async () => {
    render(<EnergyOverview siteSlug="akarp" />);

    expect(await screen.findByTestId("energy-overview")).toBeTruthy();
    expect(screen.getByText(/ENERGI – FLÖDE & FÖRBRUKNING/i)).toBeTruthy();
    expect(screen.getByTestId("energy-metric-strip")).toBeTruthy();
    expect(screen.getByTestId("energy-flow-chart")).toBeTruthy();
    expect(screen.getByTestId("energy-flow-legend")).toBeTruthy();
    expect(screen.getByText("Solproduktion")).toBeTruthy();
    expect(screen.getByText("Husförbrukning")).toBeTruthy();
    expect(screen.getByTestId("energy-battery-panel")).toBeTruthy();
    expect(screen.getByTestId("energy-quick-overview")).toBeTruthy();
    expect(screen.getByTestId("energy-peaks-panel")).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /Husförbrukning \(peak\)/i })).toBeTruthy();
  });

  it("exports csv when export button is clicked", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn(() => "blob:test");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    render(<EnergyOverview siteSlug="akarp" />);
    await screen.findByTestId("energy-overview");

    await user.click(screen.getByRole("button", { name: /Exportera data/i }));

    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();

    clickSpy.mockRestore();
    vi.unstubAllGlobals();
  });

  it("shows error when dashboard load fails", async () => {
    mockFetchSiteDashboard.mockRejectedValueOnce(new Error("offline"));
    mockFetchSiteHistory.mockRejectedValueOnce(new Error("offline"));

    render(<EnergyOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("offline");
    });
  });
});
