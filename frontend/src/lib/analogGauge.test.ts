import { describe, expect, it } from "vitest";

import {
  GAUGE_MAX_ANGLE,
  GAUGE_MIN_ANGLE,
  gaugeFillRatio,
  needleAngleForWatts,
  niceGaugeMaxW,
  resolveGaugeScales,
} from "@/lib/analogGauge";

describe("analogGauge", () => {
  it("maps zero to minimum angle for positive gauges", () => {
    expect(needleAngleForWatts(0, 10_000, "positive")).toBe(GAUGE_MIN_ANGLE);
  });

  it("maps max watts to maximum angle", () => {
    expect(needleAngleForWatts(10_000, 10_000, "positive")).toBe(GAUGE_MAX_ANGLE);
  });

  it("centers bidirectional gauge at zero watts", () => {
    expect(needleAngleForWatts(0, 10_000, "bidirectional")).toBe(0);
  });

  it("sweeps bidirectional gauge left for negative watts", () => {
    expect(needleAngleForWatts(-5000, 10_000, "bidirectional")).toBeLessThan(0);
  });

  it("computes fill ratio capped at 1", () => {
    expect(gaugeFillRatio(12_000, 10_000)).toBe(1);
  });

  it("rounds gauge max to readable steps", () => {
    expect(niceGaugeMaxW(1800)).toBe(2000);
    expect(niceGaugeMaxW(4200, 3100)).toBe(5000);
  });

  it("uses separate scales per channel", () => {
    const scales = resolveGaugeScales({
      solarW: 4200,
      houseW: 1500,
      batteryW: 0,
      gridW: -2600,
      solarPeakW: 3100,
      inverterMaxKw: 10,
    });
    expect(scales.solarMaxW).toBe(10_000);
    expect(scales.houseMaxW).toBe(4000);
    expect(scales.gridMaxW).toBe(6000);
  });
});
