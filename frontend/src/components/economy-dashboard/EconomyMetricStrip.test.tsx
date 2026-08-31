import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EconomyMetricStrip } from "./EconomyMetricStrip";
import type { EconomyDisplayMetrics, ExportRevenueBreakdown, PaybackMetrics } from "./economyDashboardHelpers";

const metrics: EconomyDisplayMetrics = {
  totalSavingsSek: 6076,
  avoidedCostSavingsSek: 5660,
  economicBenefitSek: 6076,
  gridImportCostSek: 4534,
  exportRevenueSek: 83,
  netCostSek: 4451,
  ytdReturnPct: 4,
  ytdEconomicBenefitSek: 5920,
  lifetimeEconomicBenefitSek: 18742,
  changes: {
    totalSavings: { value: 6076, previous: 5081, deltaSek: 995, pct: 19.6, direction: "up" },
    gridImportCost: { value: 4534, previous: 5529, deltaSek: -995, pct: -18, direction: "down" },
    exportRevenue: { value: 83, previous: 67, deltaSek: 16, pct: 23.9, direction: "up" },
    netCost: { value: 4451, previous: 5462, deltaSek: -1011, pct: -18.5, direction: "down" },
  },
};

const payback: PaybackMetrics = {
  investmentSek: 148_000,
  repaidSek: 18_742,
  remainingSek: 129_258,
  repaidPct: 12.7,
  paybackYears: 8.7,
  annualizedBenefitSek: 14_850,
  isForecast: false,
};

const exportBreakdown: ExportRevenueBreakdown = {
  exportedKwh: 124.8,
  weightedSpotPriceKrKwh: 0.61,
  energySaleRevenueSek: 76.13,
  supplierAdjustmentSek: 0,
  gridBenefitRevenueSek: 7.24,
  taxCreditSek: 0,
  totalExportRevenueSek: 83.37,
  totalEconomicValueSek: 83.37,
  spotPricedFraction: 1,
  showTaxCreditNotice: true,
  lines: [
    { id: "spot", label: "Spotersättning", valueSek: 76.13, quality: "ACTUAL" },
    { id: "grid-benefit", label: "Nätnytta", valueSek: 7.24, quality: "CALCULATED" },
  ],
};

describe("EconomyMetricStrip", () => {
  it("renders primary KPI cards with comparison subtext", () => {
    render(
      <EconomyMetricStrip
        metrics={metrics}
        payback={payback}
        savingsBreakdown={[
          {
            id: "solar",
            label: "Egenanvänd solel",
            amountSek: 3120,
            pct: 51,
            color: "#4ade80",
            description: "test",
            quality: "CALCULATED",
          },
        ]}
        exportBreakdown={exportBreakdown}
        comparisonLabel="Föregående månad"
        sparkSeries={[[1, 2, 3], [3, 2, 1], [1, 2, 3], [2, 3, 2], [2, 3, 4, 5]]}
      />,
    );

    expect(screen.getByText("NETTOKOSTNAD")).toBeInTheDocument();
    expect(screen.getByText("4 451 kr")).toBeInTheDocument();
    expect(screen.getByText(/995 kr lägre föregående månad/i)).toBeInTheDocument();
    expect(screen.getByText("SEDAN INSTALLATION")).toBeInTheDocument();
    expect(screen.getByText("18 742 kr")).toBeInTheDocument();
  });

  it("expands total savings breakdown", async () => {
    render(
      <EconomyMetricStrip
        metrics={metrics}
        payback={payback}
        savingsBreakdown={[
          {
            id: "solar",
            label: "Egenanvänd solel",
            amountSek: 3120,
            pct: 100,
            color: "#4ade80",
            description: "test",
            quality: "CALCULATED",
          },
        ]}
        exportBreakdown={exportBreakdown}
        comparisonLabel="Föregående månad"
        sparkSeries={[[1], [1], [1], [1], [1]]}
      />,
    );

    await userEvent.click(screen.getAllByRole("button", { name: /visa fördelning/i })[0]);
    expect(screen.getByText("Egenanvänd solel")).toBeInTheDocument();
    expect(screen.getByText("3 120 kr")).toBeInTheDocument();
  });

  it("expands export revenue breakdown", async () => {
    render(
      <EconomyMetricStrip
        metrics={metrics}
        payback={payback}
        savingsBreakdown={[]}
        exportBreakdown={exportBreakdown}
        comparisonLabel="Föregående månad"
        sparkSeries={[[1], [1], [1], [1], [1]]}
      />,
    );

    const expandButtons = screen.getAllByRole("button", { name: /visa fördelning/i });
    await userEvent.click(expandButtons[expandButtons.length - 1]);
    expect(screen.getByTestId("export-revenue-breakdown")).toBeInTheDocument();
    expect(screen.getByText("Spotersättning")).toBeInTheDocument();
    expect(screen.getByText("Nätnytta")).toBeInTheDocument();
    expect(screen.getByText(/Skattereduktion för mikroproduktion upphörde 2026-01-01/i)).toBeInTheDocument();
  });
});
