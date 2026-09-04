import { describe, expect, it } from "vitest";
import type { MarketPricesResponse } from "@/lib/api";
import {
  buildPriceTrend,
  buildSidebarElectricityPriceModel,
  buildSidebarElectricityPriceModelFromImportPeriods,
  lineColorForOre,
  pointOre,
} from "@/lib/sidebarElectricityPrice";

const TIMEZONE = "Europe/Stockholm";

function samplePrices(): MarketPricesResponse {
  return {
    slug: "akarp",
    timezone: TIMEZONE,
    resolution: "1h",
    current_price_eur_kwh: 0.84,
    average_all_in_eur_kwh: 0.95,
    highest_all_in_eur_kwh: 1.87,
    lowest_all_in_eur_kwh: 0.26,
    current_import_sek_kwh: 0.84,
    points: [
      { timestamp: "2026-08-28T00:00:00+02:00", spot_eur_kwh: 0.26, all_in_eur_kwh: 0.26, spot_sek_kwh: 0.26, import_sek_kwh: 0.26 },
      { timestamp: "2026-08-28T06:00:00+02:00", spot_eur_kwh: 0.35, all_in_eur_kwh: 0.35, spot_sek_kwh: 0.35, import_sek_kwh: 0.35 },
      { timestamp: "2026-08-28T09:00:00+02:00", spot_eur_kwh: 0.84, all_in_eur_kwh: 0.84, spot_sek_kwh: 0.84, import_sek_kwh: 0.84 },
      { timestamp: "2026-08-28T14:00:00+02:00", spot_eur_kwh: 0.43, all_in_eur_kwh: 0.43, spot_sek_kwh: 0.43, import_sek_kwh: 0.43 },
      { timestamp: "2026-08-28T18:00:00+02:00", spot_eur_kwh: 1.87, all_in_eur_kwh: 1.87, spot_sek_kwh: 1.87, import_sek_kwh: 1.87 },
    ],
  };
}

describe("sidebarElectricityPrice", () => {
  it("converts kr/kWh to whole öre", () => {
    expect(pointOre({ timestamp: "", spot_eur_kwh: 0.84, all_in_eur_kwh: 0.84 })).toBe(84);
  });

  it("builds today model from import periods in SEK", () => {
    const periods = samplePrices().points.map((point) => ({
      period_start: point.timestamp,
      period_end: point.timestamp,
      price_area: "SE4",
      currency: "SEK",
      market_price_sek_kwh: point.all_in_eur_kwh,
      import_price_sek_kwh: point.all_in_eur_kwh,
      export_price_sek_kwh: 0.39,
      source: "heartbeat",
      quality: "REAL",
      is_estimated: false,
      components: {},
    }));
    const model = buildSidebarElectricityPriceModelFromImportPeriods(
      periods,
      TIMEZONE,
      new Date("2026-08-28T09:15:00+02:00"),
    );
    expect(model).not.toBeNull();
    expect(model?.lowestOre).toBe(26);
    expect(model?.highestOre).toBe(187);
    expect(model?.currentOre).toBe(84);
  });

  it("builds today model with min, max and current", () => {
    const model = buildSidebarElectricityPriceModel(
      samplePrices(),
      new Date("2026-08-28T09:15:00+02:00"),
    );
    expect(model).not.toBeNull();
    expect(model?.lowestOre).toBe(26);
    expect(model?.highestOre).toBe(187);
    expect(model?.currentOre).toBe(84);
    expect(model?.yMax).toBeGreaterThan(model!.highestOre);
    expect(model?.yMin).toBeLessThanOrEqual(model!.lowestOre);
  });

  it("builds falling trend toward cheaper hour", () => {
    const model = buildSidebarElectricityPriceModel(
      samplePrices(),
      new Date("2026-08-28T09:15:00+02:00"),
    );
    expect(model?.trend?.direction).toBe("falling");
    expect(model?.trend?.deltaOre).toBe(41);
    expect(model?.trend?.atHourLabel).toBe("14:00");
  });

  it("returns null when fewer than two points today", () => {
    const model = buildSidebarElectricityPriceModel({
      ...samplePrices(),
      points: [{ timestamp: "2026-08-28T09:00:00+02:00", spot_eur_kwh: 0.84, all_in_eur_kwh: 0.84 }],
    });
    expect(model).toBeNull();
  });

  it("maps line colors from low to high", () => {
    expect(lineColorForOre(22, 22, 187)).toBe("#4ade80");
    expect(lineColorForOre(180, 22, 187)).toBe("#f87171");
  });

  it("fills missing hours to span 00–23", () => {
    const model = buildSidebarElectricityPriceModel(
      {
        ...samplePrices(),
        points: [
          { timestamp: "2026-08-28T14:00:00+02:00", spot_eur_kwh: 0.99, all_in_eur_kwh: 0.99 },
          { timestamp: "2026-08-28T18:00:00+02:00", spot_eur_kwh: 1.14, all_in_eur_kwh: 1.14 },
          { timestamp: "2026-08-28T23:00:00+02:00", spot_eur_kwh: 0.65, all_in_eur_kwh: 0.65 },
        ],
      },
      new Date("2026-08-28T15:00:00+02:00"),
    );
    expect(model?.points).toHaveLength(24);
    expect(model?.points[0]?.hour).toBe(0);
    expect(model?.points[23]?.hour).toBe(23);
  });

  it("buildPriceTrend handles stable day", () => {
    const points = [
      { timestamp: "2026-08-28T09:00:00+02:00", hour: 9, ore: 84, isCurrent: true },
      { timestamp: "2026-08-28T10:00:00+02:00", hour: 10, ore: 84, isCurrent: false },
    ];
    const trend = buildPriceTrend(points, 0, TIMEZONE);
    expect(trend?.direction).toBe("stable");
  });
});
