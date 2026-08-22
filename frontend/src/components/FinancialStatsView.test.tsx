import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FinancialStatsView } from "./FinancialStatsView";

const { fetchFinancialStatsMock } = vi.hoisted(() => ({
  fetchFinancialStatsMock: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, fetchFinancialStats: fetchFinancialStatsMock };
});

describe("FinancialStatsView", () => {
  beforeEach(() => {
    fetchFinancialStatsMock.mockReset();
    fetchFinancialStatsMock.mockImplementation(
      async (_slug: string, period: "day" | "month" | "year") => ({
        slug: "akarp",
        timezone: "Europe/Stockholm",
        period,
        fallback_purchase_price_sek_kwh: 2,
        export_compensation_sek_kwh: 0.8,
        stats: [
          {
            period_start:
              period === "day" ? "2026-08-18" : period === "month" ? "2026-08" : "2026",
            solar_self_consumed_kwh: 10,
            battery_self_consumed_kwh: 3,
            exported_kwh: 4,
            imported_kwh: 5,
            solar_savings_sek: 20,
            battery_savings_sek: 6,
            export_revenue_sek: 3.2,
            grid_import_cost_sek: 10,
            market_priced_fraction: 0.75,
          },
        ],
      }),
    );
  });

  it("shows savings, revenue and calculation basis", async () => {
    render(<FinancialStatsView siteSlug="akarp" />);

    expect((await screen.findAllByText("20 kr")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("6 kr").length).toBeGreaterThan(0);
    expect(screen.getAllByText("3 kr 20 öre").length).toBeGreaterThan(0);
    expect(screen.getAllByText("−10 kr").length).toBeGreaterThan(0);
    expect(screen.getByText(/19,20/)).toBeTruthy();
    expect(screen.getByText(/Heartbeat-timpris används för 75%/)).toBeTruthy();
    expect(screen.getByText(/2.00 kr\/kWh/)).toBeTruthy();
  });

  it("switches between daily, monthly and yearly statistics", async () => {
    render(<FinancialStatsView siteSlug="akarp" />);
    await screen.findAllByText("20 kr");

    fireEvent.click(screen.getByRole("tab", { name: "Månader" }));
    expect(await screen.findByRole("columnheader", { name: "Månad" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "År" }));
    expect(await screen.findByRole("columnheader", { name: "År" })).toBeTruthy();
    expect(screen.queryByLabelText("Välj statistikår")).toBeNull();
  });

  it("shows API failures", async () => {
    fetchFinancialStatsMock.mockRejectedValue(new Error("Price stats unavailable"));

    render(<FinancialStatsView siteSlug="akarp" />);

    expect((await screen.findByRole("alert")).textContent).toContain("Price stats unavailable");
  });
});
