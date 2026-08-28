import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useParams: () => ({ slug: "akarp" }),
}));

vi.mock("@/lib/useSiteDashboard", () => ({
  useSiteDashboard: () => ({
    dashboard: {
      site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
      freshness: { updated_at: "2026-08-22T10:00:00Z", data_age_seconds: 12, stale: false },
      live: { solar_production_w: 540, consumption_w: 5370, grid_import_w: 0, grid_export_w: 2300, battery_soc_pct: 58, battery_power_w: -7130, battery_direction: "discharging", ev_power_w: 0 },
      today: { produced_kwh: 21.7, consumed_kwh: 32.4, imported_kwh: 12.4, exported_kwh: 2.3, energy_cost_sek: 24.54, savings_sek: 4.02 },
      ev: null,
      solar: { expected_today_kwh: 38.4, remaining_kwh: 16.7, confidence_pct: 89 },
      price: null,
      optimization: null,
      alerts: [],
      spa_integration_enabled: false,
      vehicle_integration_enabled: false,
    },
    error: null,
    loading: false,
    reload: vi.fn(),
  }),
}));

vi.mock("@/components/intelligence-dashboard/IntelligenceOverview", () => ({
  IntelligenceOverviewLoader: () => (
    <div>
      <h1>Åkarp</h1>
      <span>PRODUKTION</span>
      <span>ENERGIFLÖDE</span>
      <span>IDAG</span>
      <span>PRESTANDA</span>
      <span>VÄDER & SOLPROGNOS</span>
      <span>CONFIDENCE</span>
    </div>
  ),
}));

describe("SiteDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders intelligence overview dashboard sections", async () => {
    const SitePage = (await import("@/app/sites/[slug]/page")).default;
    render(<SitePage />);
    await waitFor(() => {
      expect(screen.getByText("Åkarp")).toBeTruthy();
    });
    expect(screen.getByText("PRODUKTION")).toBeTruthy();
    expect(screen.getByText("ENERGIFLÖDE")).toBeTruthy();
    expect(screen.getByText("IDAG")).toBeTruthy();
    expect(screen.getByText("PRESTANDA")).toBeTruthy();
    expect(screen.getByText("VÄDER & SOLPROGNOS")).toBeTruthy();
    expect(screen.getByText("CONFIDENCE")).toBeTruthy();
  });
});
