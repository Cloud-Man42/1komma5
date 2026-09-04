import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EconomyOverview } from "./EconomyOverview";

const mockFetchFinancialStats = vi.fn();
const mockFetchYearForecast = vi.fn();
const mockFetchMarketPrices = vi.fn();
const mockFetchSiteDashboard = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchFinancialStats: (...args: unknown[]) => mockFetchFinancialStats(...args),
    fetchYearForecast: (...args: unknown[]) => mockFetchYearForecast(...args),
    fetchMarketPrices: (...args: unknown[]) => mockFetchMarketPrices(...args),
    fetchSiteDashboard: (...args: unknown[]) => mockFetchSiteDashboard(...args),
  };
});

const financialStats = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  period: "day" as const,
  fallback_purchase_price_sek_kwh: 0.58,
  export_compensation_sek_kwh: 0.29,
  stats: [
    {
      period_start: "2026-09-01",
      solar_self_consumed_kwh: 12,
      battery_self_consumed_kwh: 4,
      exported_kwh: 2,
      imported_kwh: 6,
      solar_savings_sek: 400,
      battery_savings_sek: 120,
      export_revenue_sek: 80,
      grid_import_cost_sek: 500,
      market_priced_fraction: 0.9,
    },
    {
      period_start: "2026-08-14",
      solar_self_consumed_kwh: 8,
      battery_self_consumed_kwh: 2,
      exported_kwh: 1,
      imported_kwh: 4,
      solar_savings_sek: 200,
      battery_savings_sek: 60,
      export_revenue_sek: 40,
      grid_import_cost_sek: 250,
      market_priced_fraction: 0.9,
    },
  ],
};

beforeEach(() => {
  mockFetchFinancialStats.mockResolvedValue(financialStats);
  mockFetchYearForecast.mockResolvedValue({
    slug: "akarp",
    timezone: "Europe/Stockholm",
    year: 2026,
    observed_days: 200,
    confidence: "medium",
    uncertainty_pct: 12,
    import_baseline_year: null,
    import_baseline_source: null,
    import_baseline_estimated: false,
    import_baseline_kwh: null,
    fallback_purchase_price_sek_kwh: 0.58,
    export_compensation_sek_kwh: 0.29,
    actual: {
      solar_self_consumed_kwh: 0,
      battery_self_consumed_kwh: 0,
      exported_kwh: 0,
      imported_kwh: 0,
      solar_savings_sek: 0,
      battery_savings_sek: 0,
      export_revenue_sek: 0,
      grid_import_cost_sek: 0,
      net_sek: 0,
    },
    forecast: {
      solar_self_consumed_kwh: 0,
      battery_self_consumed_kwh: 0,
      exported_kwh: 0,
      imported_kwh: 0,
      solar_savings_sek: 0,
      battery_savings_sek: 0,
      export_revenue_sek: 0,
      grid_import_cost_sek: 0,
      net_sek: 0,
    },
    total: {
      solar_self_consumed_kwh: 1000,
      battery_self_consumed_kwh: 200,
      exported_kwh: 100,
      imported_kwh: 500,
      solar_savings_sek: 12000,
      battery_savings_sek: 4000,
      export_revenue_sek: 2000,
      grid_import_cost_sek: 8000,
      net_sek: 2000,
    },
    months: [],
  });
  mockFetchMarketPrices.mockResolvedValue({
    slug: "akarp",
    timezone: "Europe/Stockholm",
    resolution: "1h",
    current_price_eur_kwh: 0.05,
    average_all_in_eur_kwh: 0.05,
    highest_all_in_eur_kwh: 0.12,
    lowest_all_in_eur_kwh: 0.02,
    points: [
      { timestamp: "2026-08-14T03:00:00Z", spot_eur_kwh: 0.02, all_in_eur_kwh: 0.02 },
      { timestamp: "2026-08-16T18:00:00Z", spot_eur_kwh: 0.12, all_in_eur_kwh: 0.12 },
    ],
  });
  mockFetchSiteDashboard.mockResolvedValue({
    site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
    freshness: { updated_at: "2026-08-27T17:00:00Z", data_age_seconds: 27, stale: false },
    live: null,
    today: null,
    ev: null,
    solar: null,
    price: { current_eur_kwh: 0.05, lowest_eur_kwh: 0.02, highest_eur_kwh: 0.12, tier: null },
    optimization: null,
    alerts: [],
  });
});

describe("EconomyOverview", () => {
  it("renders live ekonomi dashboard with metric cards", async () => {
    render(<EconomyOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("economy-overview")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByLabelText("Period")).toBeInTheDocument();
    });

    expect(screen.getByText("EKONOMI")).toBeInTheDocument();
    expect(screen.getByTestId("economy-metric-strip")).toBeInTheDocument();
    expect(screen.getByTestId("economy-cost-chart")).toBeInTheDocument();
    expect(screen.getByTestId("economy-donut")).toBeInTheDocument();
    expect(screen.getByText("TOTAL BESPARING")).toBeInTheDocument();
    expect(screen.getByLabelText("Förklaring av färger")).toBeInTheDocument();
    expect(screen.getAllByText(/Egenanvänd solel/i).length).toBeGreaterThan(0);
  });

  it("shows error when financial stats fail", async () => {
    mockFetchFinancialStats.mockRejectedValueOnce(new Error("API fel"));
    render(<EconomyOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByText("API fel")).toBeInTheDocument();
    });
  });

  it("switches to reports section via hash", async () => {
    window.history.replaceState(null, "", "/sites/akarp/costs#rapporter");
    render(<EconomyOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByTestId("economy-reports-section")).toBeInTheDocument();
    });
  });

  it("navigates to cashflow report from panel link", async () => {
    const user = userEvent.setup();
    window.history.replaceState(null, "", "/sites/akarp/costs");
    render(<EconomyOverview siteSlug="akarp" />);

    await waitFor(
      () => {
        expect(screen.getByRole("button", { name: /visa kassaflödesrapport/i })).toBeInTheDocument();
      },
      { timeout: 10_000 },
    );

    await user.click(screen.getByRole("button", { name: /visa kassaflödesrapport/i }));

    await waitFor(
      () => {
        expect(screen.getByTestId("economy-cashflow-section")).toBeInTheDocument();
      },
      { timeout: 10_000 },
    );
  }, 20_000);

  it("navigates to price details from panel link", async () => {
    window.history.replaceState(null, "", "/sites/akarp/costs");
    render(<EconomyOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /visa prisdetaljer/i })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /visa prisdetaljer/i }));

    await waitFor(() => {
      expect(screen.getByTestId("economy-price-details-section")).toBeInTheDocument();
    });
  });

  it("navigates to extended insights from panel link", async () => {
    window.history.replaceState(null, "", "/sites/akarp/costs");
    render(<EconomyOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /fler insikter/i })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /fler insikter/i }));

    await waitFor(() => {
      expect(screen.getByTestId("economy-insights-section")).toBeInTheDocument();
    });
  });

  it("exports csv from header button", async () => {
    const createObjectURL = vi.fn(() => "blob:test");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<EconomyOverview siteSlug="akarp" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /exportera rapport/i })).toBeEnabled();
    });

    await userEvent.click(screen.getByRole("button", { name: /exportera rapport/i }));
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    click.mockRestore();
    vi.unstubAllGlobals();
  });
});
