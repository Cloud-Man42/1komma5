import { describe, expect, it } from "vitest";
import {
  aggregateFinancialStats,
  buildCostBreakdown,
  buildCostReductionGoal,
  buildEconomyGoals,
  buildEconomyInsights,
  buildEconomyMetrics,
  buildExportRevenueBreakdown,
  buildPriceAnalysis,
  buildSavingsBreakdown,
  computeDailyEconomicResult,
  computeEconomicBenefit,
  computeTotalEconomicValue,
  computeMetricChange,
  computeNetCost,
  computePaybackMetrics,
  computeTotalSavings,
  computeYtdReturnPct,
  filterRepresentativeDailyStats,
  filterStatsForMonth,
  findBestEconomyDay,
  formatComparisonSubtext,
  formatEconomyKr,
  formatEconomyPct,
  formatMetricValue,
  resolveSiteInvestmentSek,
} from "./economyDashboardHelpers";
import type { FinancialStat, MarketPricesResponse } from "@/lib/api";

const stat = (overrides: Partial<FinancialStat> = {}): FinancialStat => ({
  period_start: "2026-08-14",
  solar_self_consumed_kwh: 10,
  battery_self_consumed_kwh: 2,
  exported_kwh: 3,
  imported_kwh: 8,
  solar_savings_sek: 100,
  battery_savings_sek: 50,
  export_revenue_sek: 30,
  energy_sale_revenue_sek: 25,
  grid_benefit_revenue_sek: 5,
  tax_credit_sek: 0,
  grid_import_cost_sek: 200,
  market_priced_fraction: 0.8,
  ...overrides,
});

describe("economyDashboardHelpers", () => {
  it("aggregates financial stats", () => {
    const totals = aggregateFinancialStats([stat(), stat({ period_start: "2026-08-15", grid_import_cost_sek: 100 })]);
    expect(totals.gridImportCostSek).toBe(300);
    expect(totals.solarSavingsSek).toBe(200);
  });

  it("filters stats for month", () => {
    const stats = [stat(), stat({ period_start: "2026-07-31" })];
    expect(filterStatsForMonth(stats, 2026, 8)).toHaveLength(1);
  });

  it("computes net cost as import minus export revenue", () => {
    const totals = aggregateFinancialStats([stat()]);
    expect(computeNetCost(totals)).toBe(170);
    expect(computeNetCost(aggregateFinancialStats([stat({ grid_import_cost_sek: 50, export_revenue_sek: 80 })]))).toBe(-30);
  });

  it("computes economic benefit including export revenue", () => {
    const totals = aggregateFinancialStats([stat()]);
    expect(computeEconomicBenefit(totals)).toBe(180);
    expect(computeTotalSavings(totals, 20)).toBe(200);
  });

  it("builds metric changes with direction", () => {
    expect(computeMetricChange(120, 100).direction).toBe("up");
    expect(computeMetricChange(80, 100).direction).toBe("down");
  });

  it("builds economy metrics from current and previous totals", () => {
    const current = aggregateFinancialStats([stat()]);
    const previous = aggregateFinancialStats([stat({ grid_import_cost_sek: 100, solar_savings_sek: 50 })]);
    const ytd = aggregateFinancialStats([stat(), stat({ period_start: "2026-08-01" })]);
    const lifetime = ytd;
    const metrics = buildEconomyMetrics(current, previous, ytd, lifetime, 148_000);
    expect(metrics.gridImportCostSek).toBe(200);
    expect(metrics.netCostSek).toBe(170);
    expect(metrics.totalSavingsSek).toBe(180);
    expect(metrics.ytdReturnPct).not.toBeNull();
  });

  it("splits import cost into breakdown slices", () => {
    const slices = buildCostBreakdown(1000);
    expect(slices).toHaveLength(4);
    expect(slices.reduce((sum, s) => sum + s.amountSek, 0)).toBeCloseTo(1000, 5);
  });

  it("builds savings breakdown only for categories with data", () => {
    const totals = aggregateFinancialStats([stat()]);
    const breakdown = buildSavingsBreakdown(totals, 0);
    expect(breakdown.map((row) => row.id)).toEqual(["solar", "battery", "export"]);
    expect(breakdown.find((row) => row.id === "ev")).toBeUndefined();
  });

  it("resolves site-specific investment amounts", () => {
    expect(resolveSiteInvestmentSek("akarp")).toBe(148_000);
    expect(resolveSiteInvestmentSek("summer-house-denmark")).toBe(90_000);
    expect(resolveSiteInvestmentSek("unknown-site")).toBeNull();
  });

  it("returns null ytd return when investment missing", () => {
    expect(computeYtdReturnPct(10_000, null)).toBeNull();
    expect(computeYtdReturnPct(10_000, 250_000)).toBeCloseTo(4);
  });

  it("computes payback metrics from lifetime and trailing benefits", () => {
    const payback = computePaybackMetrics(18_742, 21_500, 250_000);
    expect(payback.repaidPct).toBeCloseTo(7.5, 1);
    expect(payback.remainingSek).toBeCloseTo(231_258, 0);
    expect(payback.paybackYears).toBeCloseTo(10.8, 1);
  });

  it("formats comparison subtext with kr delta", () => {
    const change = computeMetricChange(4451, 5462);
    expect(formatComparisonSubtext(change, "Föregående månad", { higherIsGood: false, invertGood: true })).toMatch(
      /1[\s\u00a0]?011 kr lägre/i,
    );
  });

  it("shows missing label instead of zero kr", () => {
    expect(formatMetricValue(0)).toBe("Data saknas");
    expect(formatMetricValue(0, { allowZero: true })).toBe("0 kr");
  });

  it("formats kr and percent labels", () => {
    expect(formatEconomyKr(2846)).toBe("2\u00a0846 kr");
    expect(formatEconomyPct(38)).toBe("↑ 38%");
    expect(formatEconomyPct(-21, true)).toBe("↓ 21%");
  });

  it("computes daily economic result including savings", () => {
    expect(computeDailyEconomicResult(stat())).toBe(-20);
    expect(
      computeDailyEconomicResult(
        stat({
          solar_savings_sek: 120,
          battery_savings_sek: 45,
          export_revenue_sek: 25,
          grid_import_cost_sek: 60,
        }),
      ),
    ).toBe(130);
  });

  it("ignores partial connection day when finding best day", () => {
    const connectionDay = stat({
      period_start: "2026-08-13",
      solar_self_consumed_kwh: 1,
      battery_self_consumed_kwh: 0.5,
      imported_kwh: 2,
      exported_kwh: 0,
      solar_savings_sek: 15,
      battery_savings_sek: 3,
      export_revenue_sek: 0,
      grid_import_cost_sek: 5,
    });
    const strongDay = stat({
      period_start: "2026-08-20",
      solar_self_consumed_kwh: 25,
      battery_self_consumed_kwh: 8,
      imported_kwh: 12,
      exported_kwh: 5,
      solar_savings_sek: 120,
      battery_savings_sek: 45,
      export_revenue_sek: 25,
      grid_import_cost_sek: 60,
    });
    const fillerDays = Array.from({ length: 4 }, (_, index) =>
      stat({
        period_start: `2026-08-${10 + index}`,
        solar_self_consumed_kwh: 18,
        battery_self_consumed_kwh: 6,
        imported_kwh: 10,
        exported_kwh: 4,
      }),
    );

    const best = findBestEconomyDay([connectionDay, ...fillerDays, strongDay]);
    expect(best?.period_start).toBe("2026-08-20");
    expect(filterRepresentativeDailyStats([connectionDay, ...fillerDays])).not.toContainEqual(connectionDay);
  });

  it("builds economy goals from measured self-use instead of hardcoded cost target", () => {
    const totals = aggregateFinancialStats([stat()]);
    const previous = aggregateFinancialStats([stat({ grid_import_cost_sek: 400 })]);
    const goals = buildEconomyGoals(totals, previous, "Föregående månad");
    const costGoal = goals.find((goal) => goal.id === "cost");
    expect(costGoal?.displayValue).not.toBe("—");
    expect(costGoal?.valuePct).toBeGreaterThan(0);
    expect(costGoal?.displayValue).toMatch(/lägre|högre|Oförändrat/i);
  });

  it("shows signed cost change with visible bar when costs increased", () => {
    const current = aggregateFinancialStats([stat({ grid_import_cost_sek: 500 })]);
    const previous = aggregateFinancialStats([stat({ grid_import_cost_sek: 400 })]);
    const goal = buildCostReductionGoal(current, previous, "Föregående månad");
    expect(goal.displayValue).toContain("↑");
    expect(goal.valuePct).toBeGreaterThan(0);
    expect(goal.tone).toBe("warn");
  });

  it("shows cost reduction in green when costs decreased", () => {
    const current = aggregateFinancialStats([stat({ grid_import_cost_sek: 300 })]);
    const previous = aggregateFinancialStats([stat({ grid_import_cost_sek: 500 })]);
    const goal = buildCostReductionGoal(current, previous, "Föregående månad");
    expect(goal.displayValue).toContain("↓");
    expect(goal.valuePct).toBeGreaterThan(0);
    expect(goal.tone).toBe("green");
  });

  it("falls back to period cost when comparison history is missing", () => {
    const current = aggregateFinancialStats([stat({ grid_import_cost_sek: 500 })]);
    const goal = buildCostReductionGoal(current, null, "");
    expect(goal.displayValue).toContain("500");
    expect(goal.valuePct).toBeGreaterThan(0);
  });

  it("builds best-day insight from full economic result", () => {
    const insights = buildEconomyInsights(
      aggregateFinancialStats([
        stat({
          period_start: "2026-08-13",
          solar_self_consumed_kwh: 1,
          imported_kwh: 1,
          solar_savings_sek: 10,
          grid_import_cost_sek: 2,
        }),
        stat({
          period_start: "2026-08-22",
          solar_self_consumed_kwh: 20,
          battery_self_consumed_kwh: 6,
          imported_kwh: 8,
          exported_kwh: 3,
          solar_savings_sek: 90,
          battery_savings_sek: 30,
          export_revenue_sek: 12,
          grid_import_cost_sek: 40,
        }),
      ]),
      [
        stat({
          period_start: "2026-08-13",
          solar_self_consumed_kwh: 1,
          imported_kwh: 1,
          solar_savings_sek: 10,
          grid_import_cost_sek: 2,
        }),
        stat({
          period_start: "2026-08-22",
          solar_self_consumed_kwh: 20,
          battery_self_consumed_kwh: 6,
          imported_kwh: 8,
          exported_kwh: 3,
          solar_savings_sek: 90,
          battery_savings_sek: 30,
          export_revenue_sek: 12,
          grid_import_cost_sek: 40,
        }),
      ],
      0,
    );

    const bestDay = insights.find((item) => item.id === "bestday");
    expect(bestDay?.text).toContain("22 aug");
    expect(bestDay?.text).not.toContain("13 aug");
  });

  it("builds price analysis from live market data instead of fallback tariffs", () => {
    const marketPrices: MarketPricesResponse = {
      slug: "akarp",
      timezone: "Europe/Stockholm",
      resolution: "1h",
      current_price_eur_kwh: 1.36,
      average_all_in_eur_kwh: 1.05,
      highest_all_in_eur_kwh: 2.44,
      lowest_all_in_eur_kwh: 0.77,
      current_spot_sek_kwh: 1.21,
      current_import_sek_kwh: 1.61,
      average_import_sek_kwh: 1.605,
      highest_import_sek_kwh: 2.44,
      lowest_import_sek_kwh: 0.77,
      points: [
        {
          timestamp: "2026-08-31T02:00:00+02:00",
          spot_eur_kwh: 0.55,
          all_in_eur_kwh: 0.77,
          spot_sek_kwh: 0.55,
          import_sek_kwh: 0.77,
        },
        {
          timestamp: "2026-08-31T14:00:00+02:00",
          spot_eur_kwh: 1.87,
          all_in_eur_kwh: 2.44,
          spot_sek_kwh: 1.87,
          import_sek_kwh: 2.44,
        },
      ],
    };

    const analysis = buildPriceAnalysis(
      marketPrices,
      0.8,
      "Europe/Stockholm",
      new Date("2026-08-31T12:00:00+02:00"),
    );

    expect(analysis.spotOre).toBe(121);
    expect(analysis.purchaseOre).toBe(161);
    expect(analysis.exportOre).toBe(80);
    expect(analysis.cheapestOre).toBe(77);
    expect(analysis.expensiveOre).toBe(244);
    expect(analysis.cheapestAt).toContain("02:00");
    expect(analysis.expensiveAt).toContain("14:00");
  });

  it("returns null prices when market data is missing", () => {
    const analysis = buildPriceAnalysis(null, 0.8, "Europe/Stockholm");
    expect(analysis.spotOre).toBeNull();
    expect(analysis.purchaseOre).toBeNull();
    expect(analysis.cheapestOre).toBeNull();
    expect(analysis.expensiveOre).toBeNull();
    expect(analysis.exportOre).toBe(80);
  });

  it("builds export revenue breakdown with weighted sell price", () => {
    const stats = [
      stat({
        exported_kwh: 2.4,
        export_revenue_sek: 1.728,
        energy_sale_revenue_sek: 1.728,
        export_spot_priced_fraction: 1,
      }),
      stat({
        period_start: "2026-08-15",
        exported_kwh: 1.8,
        export_revenue_sek: 0.558,
        energy_sale_revenue_sek: 0.558,
        export_spot_priced_fraction: 1,
      }),
    ];
    const totals = aggregateFinancialStats(stats);
    const breakdown = buildExportRevenueBreakdown(totals, stats, new Date("2026-08-31T12:00:00+02:00"));
    expect(breakdown.exportedKwh).toBeCloseTo(4.2, 1);
    expect(breakdown.energySaleRevenueSek).toBeCloseTo(2.286, 2);
    expect(breakdown.weightedSpotPriceKrKwh).toBeCloseTo(2.286 / 4.2, 3);
    expect(breakdown.showTaxCreditNotice).toBe(true);
    expect(breakdown.lines[0]?.label).toBe("Spotersättning");
  });

  it("uses feed-in label when pricing mode is feed_in", () => {
    const totals = aggregateFinancialStats([stat()]);
    const breakdown = buildExportRevenueBreakdown(totals, [stat()], new Date("2026-08-31T12:00:00+02:00"), "feed_in");
    expect(breakdown.lines[0]?.label).toBe("Inmatningstariff");
  });

  it("flags export before contract start without counting it as revenue", () => {
    const totals = aggregateFinancialStats([
      stat({ exported_kwh: 10, export_revenue_sek: 2, uncontracted_exported_kwh: 6 }),
      stat({ period_start: "2026-08-25", exported_kwh: 4, export_revenue_sek: 3, uncontracted_exported_kwh: 0 }),
    ]);
    const breakdown = buildExportRevenueBreakdown(
      totals,
      [
        stat({ exported_kwh: 10, export_revenue_sek: 2, uncontracted_exported_kwh: 6 }),
        stat({ period_start: "2026-08-25", exported_kwh: 4, export_revenue_sek: 3, uncontracted_exported_kwh: 0 }),
      ],
      new Date("2026-08-31T12:00:00+02:00"),
      "feed_in",
      "2026-08-25",
    );
    expect(breakdown.showPreContractExportNotice).toBe(true);
    expect(breakdown.preContractExportedKwh).toBeCloseTo(6, 1);
    expect(breakdown.totalExportRevenueSek).toBeCloseTo(5, 2);
  });

  it("includes tax credit in total economic value but not export revenue", () => {
    const totals = aggregateFinancialStats([
      stat({ export_revenue_sek: 100, energy_sale_revenue_sek: 90, grid_benefit_revenue_sek: 10, tax_credit_sek: 60 }),
    ]);
    expect(computeEconomicBenefit(totals)).toBe(250);
    expect(computeTotalEconomicValue(totals)).toBe(310);
    expect(computeNetCost(totals)).toBe(100);
  });

  it("does not double count export in savings breakdown vs net cost", () => {
    const totals = aggregateFinancialStats([stat()]);
    const savings = buildSavingsBreakdown(totals);
    const exportLine = savings.find((row) => row.id === "export");
    expect(exportLine?.amountSek).toBe(30);
    expect(computeNetCost(totals)).toBe(totals.gridImportCostSek - totals.exportRevenueSek);
    expect(computeEconomicBenefit(totals)).toBe(totals.solarSavingsSek + totals.batterySavingsSek + totals.exportRevenueSek);
  });
});
