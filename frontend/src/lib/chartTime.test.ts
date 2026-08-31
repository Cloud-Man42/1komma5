import { describe, expect, it } from "vitest";
import type { Reading } from "@/lib/api";
import {
  formatChartClock,
  inferForecastIntervalMs,
  localDateKey,
  localDayBoundsMs,
  readingTimestamp,
  roundKwh,
  roundKw,
  sumEnergyKwh,
} from "./chartTime";

describe("chartTime", () => {
  const TZ = "Europe/Stockholm";

  it("localDateKey returns calendar date in timezone", () => {
    expect(localDateKey("2026-08-27T22:00:00Z", TZ)).toBe("2026-08-28");
  });

  it("formatChartClock returns hour:minute in timezone", () => {
    expect(formatChartClock("2026-08-27T06:30:00Z", TZ)).toMatch(/^\d{2}:\d{2}$/);
  });

  it("localDayBoundsMs returns midnight in site timezone", () => {
    const { startMs, endMs } = localDayBoundsMs("2026-08-29T08:00:00Z", TZ);
    expect(formatChartClock(new Date(startMs).toISOString(), TZ)).toBe("00:00");
    expect(endMs - startMs).toBe(24 * 60 * 60 * 1000);
  });

  it("readingTimestamp prefers bucket_start for aggregated readings", () => {
    const reading: Reading = {
      bucket_start: "2026-08-27T06:00:00Z",
      bucket_end: "2026-08-27T06:15:00Z",
      solar_production_w: 1000,
      consumption_w: 0,
      grid_import_w: 0,
      grid_export_w: 0,
      battery_soc_pct: 0,
      battery_power_w: 0,
      sample_count: 1,
    };
    expect(readingTimestamp(reading)).toBe("2026-08-27T06:00:00Z");
  });

  it("readingTimestamp uses recorded_at for raw readings", () => {
    expect(
      readingTimestamp({
        recorded_at: "2026-08-27T07:00:00Z",
        solar_production_w: 0,
        consumption_w: 0,
        grid_import_w: 0,
        grid_export_w: 0,
        battery_soc_pct: 0,
        battery_power_w: 0,
      }),
    ).toBe("2026-08-27T07:00:00Z");
  });

  it("roundKw converts watts to kW with two decimals", () => {
    expect(roundKw(1234)).toBe(1.23);
  });

  it("roundKwh rounds to one decimal", () => {
    expect(roundKwh(12.34)).toBe(12.3);
  });

  it("inferForecastIntervalMs detects 15-min steps", () => {
    const points = [
      { timestamp: "2026-08-27T06:00:00Z" },
      { timestamp: "2026-08-27T06:15:00Z" },
      { timestamp: "2026-08-27T06:30:00Z" },
    ];
    expect(inferForecastIntervalMs(points)).toBe(15 * 60 * 1000);
  });

  it("inferForecastIntervalMs defaults for single point", () => {
    expect(inferForecastIntervalMs([{ timestamp: "2026-08-27T06:00:00Z" }])).toBe(15 * 60 * 1000);
  });

  it("sumEnergyKwh uses expected_energy_kwh when all points have it", () => {
    const points = [
      { corrected_power_w: 2000, expected_energy_kwh: 0.5 },
      { corrected_power_w: 3000, expected_energy_kwh: 0.75 },
    ];
    expect(sumEnergyKwh(points, 0.25)).toBe(1.25);
  });

  it("sumEnergyKwh derives from power when energy missing", () => {
    const points = [{ corrected_power_w: 2000 }, { corrected_power_w: 4000 }];
    expect(sumEnergyKwh(points, 0.25)).toBe(1.5);
  });
});
