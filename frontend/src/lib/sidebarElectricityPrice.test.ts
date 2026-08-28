import { describe, expect, it } from "vitest";
import type { MarketPricesResponse } from "@/lib/api";
import {
  buildPriceTrend,
  buildSidebarElectricityPriceModel,
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
    lowest_all_in_eur_kwh: 0.22,
    points: [
      { timestamp: "2026-08-28T00:00:00+02:00", spot_eur_kwh: 0.22, all_in_eur_kwh: 0.22 },
      { timestamp: "2026-08-28T06:00:00+02:00", spot_eur_kwh: 0.35, all_in_eur_kwh: 0.35 },
      { timestamp: "2026-08-28T09:00:00+02:00", spot_eur_kwh: 0.84, all_in_eur_kwh: 0.84 },
      { timestamp: "2026-08-28T14:00:00+02:00", spot_eur_kwh: 0.43, all_in_eur_kwh: 0.43 },
      { timestamp: "2026-08-28T18:00:00+02:00", spot_eur_kwh: 1.87, all_in_eur_kwh: 1.87 },
    ],
  };
}

describe("sidebarElectricityPrice", () => {
  it("converts kr/kWh to whole öre", () => {
    expect(pointOre({ timestamp: "", spot_eur_kwh: 0.84, all_in_eur_kwh: 0.84 })).toBe(84);
  });

  it("builds today model with min, max and current", () => {
    const model = buildSidebarElectricityPriceModel(
      samplePrices(),
      new Date("2026-08-28T09:15:00+02:00"),
    );
    expect(model).not.toBeNull();
    expect(model?.lowestOre).toBe(22);
    expect(model?.highestOre).toBe(187);
    expect(model?.currentOre).toBe(84);
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
