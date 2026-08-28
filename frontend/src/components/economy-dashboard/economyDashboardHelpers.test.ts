import { describe, expect, it } from "vitest";
import {
  aggregateFinancialStats,
  buildCostBreakdown,
  buildEconomyInsights,
  buildEconomyMetrics,
  buildSavingsBreakdown,
  computeDailyEconomicResult,
  computeMetricChange,
  computeNetCost,
  computeTotalSavings,
  filterRepresentativeDailyStats,
  filterStatsForMonth,
  findBestEconomyDay,
  formatEconomyKr,
  formatEconomyPct,
  resolveSiteInvestmentSek,
} from "./economyDashboardHelpers";
import type { FinancialStat } from "@/lib/api";

const stat = (overrides: Partial<FinancialStat> = {}): FinancialStat => ({
  period_start: "2026-08-14",
  solar_self_consumed_kwh: 10,
  battery_self_consumed_kwh: 2,
  exported_kwh: 3,
  imported_kwh: 8,
  solar_savings_sek: 100,
  battery_savings_sek: 50,
  export_revenue_sek: 30,
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
  });

  it("computes total savings without export revenue", () => {
    const totals = aggregateFinancialStats([stat()]);
    expect(computeTotalSavings(totals, 20)).toBe(170);
  });

  it("builds metric changes with direction", () => {
    expect(computeMetricChange(120, 100).direction).toBe("up");
    expect(computeMetricChange(80, 100).direction).toBe("down");
  });

  it("builds economy metrics from current and previous totals", () => {
    const current = aggregateFinancialStats([stat()]);
    const previous = aggregateFinancialStats([stat({ grid_import_cost_sek: 100, solar_savings_sek: 50 })]);
    const metrics = buildEconomyMetrics(current, previous, 150);
    expect(metrics.gridImportCostSek).toBe(200);
    expect(metrics.netCostSek).toBe(170);
    expect(metrics.totalSavingsSek).toBe(150);
  });

  it("splits import cost into breakdown slices", () => {
    const slices = buildCostBreakdown(1000);
    expect(slices).toHaveLength(4);
    expect(slices.reduce((sum, s) => sum + s.amountSek, 0)).toBeCloseTo(1000, 5);
  });

  it("builds savings breakdown with colors and descriptions", () => {
    const totals = aggregateFinancialStats([stat()]);
    const breakdown = buildSavingsBreakdown(totals, 20);
    expect(breakdown).toHaveLength(3);
    expect(breakdown[0].color).toBe("#4ade80");
    expect(breakdown[0].description).toContain("Solenergi");
    expect(breakdown[2].label).toBe("Laddsmart optimering");
  });

  it("resolves site-specific investment amounts", () => {
    expect(resolveSiteInvestmentSek("akarp")).toBe(148_000);
    expect(resolveSiteInvestmentSek("summer-house-denmark")).toBe(90_000);
    expect(resolveSiteInvestmentSek("unknown-site")).toBe(152_000);
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
});
