import { describe, expect, it } from "vitest";
import {
  filterStatsForPeriod,
  resolveComparisonRange,
  resolvePeriodRange,
} from "./economyPeriods";
import type { FinancialStat } from "@/lib/api";

const stat = (day: string): FinancialStat => ({
  period_start: day,
  solar_self_consumed_kwh: 1,
  battery_self_consumed_kwh: 0,
  exported_kwh: 0,
  imported_kwh: 1,
  solar_savings_sek: 1,
  battery_savings_sek: 0,
  export_revenue_sek: 0,
  grid_import_cost_sek: 2,
  market_priced_fraction: 1,
});

describe("economyPeriods", () => {
  const now = new Date("2026-08-31T12:00:00+02:00");

  it("resolves this-month range", () => {
    expect(resolvePeriodRange("this-month", now).from).toBe("2026-08-01");
    expect(resolvePeriodRange("this-month", now).to).toBe("2026-08-31");
  });

  it("filters stats for 7-day window", () => {
    const stats = [
      stat("2026-08-24"),
      stat("2026-08-25"),
      stat("2026-08-31"),
      stat("2026-08-20"),
    ];
    const filtered = filterStatsForPeriod(stats, "7d", now);
    expect(filtered.map((row) => row.period_start)).toEqual([
      "2026-08-25",
      "2026-08-31",
    ]);
  });

  it("resolves previous-period comparison for this-month", () => {
    const range = resolveComparisonRange("this-month", "previous-period", now);
    expect(range?.from).toBe("2026-07-01");
    expect(range?.to).toBe("2026-07-31");
  });

  it("returns null comparison for since-installation", () => {
    expect(resolveComparisonRange("since-installation", "previous-period", now)).toBeNull();
  });
});
