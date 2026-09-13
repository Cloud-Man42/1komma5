import { describe, expect, it } from "vitest";
import type { MultiSiteSiteEntry } from "@/lib/multiSiteApi";
import {
  aggregateSiteCurrencies,
  aggregateSiteEntries,
  aggregateSiteHealth,
} from "@/lib/multiSiteClientAggregate";

const baseSite = (
  slug: string,
  name: string,
  consumptionKw: number,
  currency = "SEK",
): MultiSiteSiteEntry => ({
  slug,
  name,
  currency,
  health: "healthy",
  healthDetail: null,
  available: true,
  live: {
    solarPowerKw: consumptionKw * 0.5,
    consumptionPowerKw: consumptionKw,
    gridImportPowerKw: 0,
    gridExportPowerKw: 0.5,
    batterySocPercent: 80,
    batteryPowerKw: 0,
  },
  today: {
    solarKwh: 10,
    consumptionKwh: 20,
    gridImportKwh: 0,
    gridExportKwh: 1,
    costToday: 100,
    savingsToday: 10,
  },
  error: null,
});

describe("aggregateSiteEntries", () => {
  it("sums consumption across visible sites", () => {
    const agg = aggregateSiteEntries([
      baseSite("akarp", "Åkarp", 3.2),
      baseSite("denmark", "Danmark", 2.1),
    ]);
    expect(agg.consumptionPowerKw).toBe(5.3);
    expect(agg.solarPowerKw).toBeCloseTo(2.65, 2);
  });

  it("ignores unavailable sites", () => {
    const offline = { ...baseSite("x", "X", 9), available: false };
    const agg = aggregateSiteEntries([baseSite("akarp", "Åkarp", 1), offline]);
    expect(agg.consumptionPowerKw).toBe(1);
  });
});

describe("aggregateSiteCurrencies", () => {
  it("groups cost and savings by currency for visible sites", () => {
    const rows = aggregateSiteCurrencies([
      baseSite("akarp", "Åkarp", 3, "SEK"),
      baseSite("denmark", "Danmark", 2, "DKK"),
    ]);
    expect(rows).toEqual([
      { currency: "DKK", costToday: 100, savingsToday: 10 },
      { currency: "SEK", costToday: 100, savingsToday: 10 },
    ]);
  });

  it("returns empty list when no sites have currency", () => {
    const site = { ...baseSite("akarp", "Åkarp", 1), currency: undefined };
    expect(aggregateSiteCurrencies([site])).toEqual([]);
  });
});

describe("aggregateSiteHealth", () => {
  it("counts health labels for visible sites", () => {
    const degraded = { ...baseSite("x", "X", 1), health: "degraded" };
    const offline = { ...baseSite("y", "Y", 1), health: "offline" };
    expect(aggregateSiteHealth([baseSite("akarp", "Åkarp", 1), degraded, offline])).toEqual({
      healthy: 1,
      degraded: 1,
      offline: 1,
    });
  });
});
