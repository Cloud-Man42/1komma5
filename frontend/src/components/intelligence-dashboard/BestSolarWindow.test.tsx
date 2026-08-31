import { describe, expect, it } from "vitest";
import { computeBestSolarWindow } from "./BestSolarWindow";

const TZ = "Europe/Stockholm";
const REF_NOW = "2026-08-27T12:00:00Z";

function point(
  hourUtc: number,
  minute: number,
  powerW: number,
  energyKwh: number,
  day = "2026-08-27",
): Parameters<typeof computeBestSolarWindow>[0]["points"][number] {
  return {
    timestamp: `${day}T${String(hourUtc).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00Z`,
    baseline_power_w: powerW,
    corrected_power_w: powerW,
    expected_energy_kwh: energyKwh,
    lower_bound_power_w: powerW * 0.8,
    upper_bound_power_w: powerW * 1.1,
    confidence: 0.8,
    correction_factor: 1,
  };
}

describe("computeBestSolarWindow", () => {
  it("returns null when no daylight points exist", () => {
    expect(
      computeBestSolarWindow({
        points: [
          point(2, 0, 0, 0),
        ],
        timezone: TZ,
        now: REF_NOW,
      }),
    ).toBeNull();
  });

  it("ignores forecast points from other days", () => {
    const result = computeBestSolarWindow({
      points: [
        point(10, 0, 3000, 0.8, "2026-08-26"),
        point(11, 0, 3500, 0.9, "2026-08-27"),
        point(11, 15, 3600, 0.95, "2026-08-27"),
        point(11, 30, 3700, 1.0, "2026-08-27"),
        point(11, 45, 3600, 0.95, "2026-08-27"),
        point(12, 0, 3500, 0.9, "2026-08-27"),
      ],
      timezone: TZ,
      houseLoadW: 1000,
      windowPoints: 3,
      now: REF_NOW,
    });

    expect(result).not.toBeNull();
    expect(result?.start).toMatch(/^\d{2}:\d{2}$/);
    expect(result?.expectedProductionKwh).toBeGreaterThan(0);
  });

  it("picks the window with highest surplus, not just first daylight", () => {
    const lowMorning = Array.from({ length: 5 }, (_, i) =>
      point(6, i * 15, 500, 0.2),
    );
    const peak = Array.from({ length: 5 }, (_, i) =>
      point(11, i * 15, 3000 + i * 100, 0.9),
    );

    const result = computeBestSolarWindow({
      points: [...lowMorning, ...peak],
      timezone: TZ,
      houseLoadW: 1000,
      windowPoints: 5,
      now: REF_NOW,
    });

    expect(result).not.toBeNull();
    expect(result?.expectedSurplusKwh).toBeGreaterThan(2);
    expect(result?.bars.length).toBe(5);
    expect(Math.max(...(result?.bars ?? []))).toBeGreaterThan(3000);
  });

  it("computes surplus after subtracting estimated house load", () => {
    const result = computeBestSolarWindow({
      points: [point(12, 0, 4000, 1.0)],
      timezone: TZ,
      houseLoadW: 2000,
      windowPoints: 1,
      now: REF_NOW,
    });

    expect(result?.expectedProductionKwh).toBe(1);
    expect(result?.expectedSurplusKwh).toBeCloseTo(0.5, 3);
  });
});
