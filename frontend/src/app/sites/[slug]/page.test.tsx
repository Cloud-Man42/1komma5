import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ slug: "akarp" }),
}));

const mockDashboard = {
  site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
  freshness: { updated_at: "2026-08-22T10:00:00Z", data_age_seconds: 12, stale: false },
  live: {
    solar_production_w: 3000,
    consumption_w: 1700,
    grid_import_w: 0,
    grid_export_w: 900,
    battery_soc_pct: 82,
    battery_power_w: 500,
    battery_direction: "charging",
    ev_power_w: 0,
  },
  today: {
    produced_kwh: 31.8,
    consumed_kwh: 24.2,
    imported_kwh: 6.1,
    exported_kwh: 9.4,
    energy_cost_sek: 18,
    savings_sek: 42,
  },
  ev: { available: false, charging: false },
  solar: { expected_today_kwh: 31.8, remaining_kwh: 18.4, confidence_pct: 87 },
  price: null,
  optimization: { strategy_sv: "Väntar på sol", explanation_sv: "Tillräcklig solel förväntas." },
  alerts: [],
  spa_integration_enabled: false,
};

vi.mock("@/lib/useSiteDashboard", () => ({
  useSiteDashboard: () => ({
    dashboard: mockDashboard,
    error: null,
    loading: false,
    reload: vi.fn(),
  }),
}));

vi.mock("@/components/dashboard/EnergyTodayChart", () => ({
  EnergyTodayChart: () => <div>Energi idag</div>,
}));
vi.mock("@/components/dashboard/LiveEnergyFlow", () => ({
  LiveEnergyFlow: () => <div>Live flow</div>,
}));

describe("SiteDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders site overview dashboard", async () => {
    const SitePage = (await import("@/app/sites/[slug]/page")).default;
    render(<SitePage />);
    await waitFor(() => {
      expect(screen.getByText("Åkarp")).toBeTruthy();
    });
    expect(screen.getByText("Idag")).toBeTruthy();
    expect(screen.getByText("EMIC-optimering")).toBeTruthy();
    expect(screen.getByText("Live flow")).toBeTruthy();
  });
});
