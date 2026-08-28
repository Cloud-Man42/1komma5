import { describe, expect, it } from "vitest";
import { buildPerformanceMetrics } from "./PerformancePanel";
import { isNavActive } from "./navItems";

describe("navItems", () => {
  it("marks overview as active only on exact path", () => {
    expect(
      isNavActive("/sites/akarp", "akarp", {
        id: "overview",
        label: "Översikt",
        href: (slug) => `/sites/${slug}`,
        exact: true,
      }),
    ).toBe(true);
    expect(
      isNavActive("/sites/akarp/energy", "akarp", {
        id: "overview",
        label: "Översikt",
        href: (slug) => `/sites/${slug}`,
        exact: true,
      }),
    ).toBe(false);
  });
});

describe("computePerformanceFromSummary", () => {
  it("uses backend summary when available", async () => {
    const { computePerformanceFromSummary } = await import("./useOverviewData");
    const metrics = computePerformanceFromSummary(
      {
        site_slug: "akarp",
        days: [],
        headline_ratio: 0.944,
        today_deviation_pct: -5.6,
        week_avg: 0.931,
        month_avg: 0.952,
        quarter_avg: 0.948,
        ytd_avg: 0.951,
        raw_forecast_so_far_kwh: 8,
        actual_today_kwh: 4,
      },
      null,
    );
    expect(metrics.headlineRatio).toBe(0.944);
    expect(metrics.todayDeviation).toBe(-5.6);
    expect(metrics.weekAvg).toBe(0.931);
  });

  it("falls back to raw forecast deviation when summary is missing", async () => {
    const { computePerformanceFromSummary } = await import("./useOverviewData");
    const metrics = computePerformanceFromSummary(null, {
      site_id: 1,
      generated_at: "2026-08-27T08:00:00Z",
      model_version: "solar-forecast-v2",
      quality: "good",
      weather_source: "live",
      expected_today_kwh: 20,
      remaining_today_kwh: 10,
      peak_power_w: 3000,
      confidence: 0.8,
      lower_today_kwh: 15,
      upper_today_kwh: 25,
      weather_summary: "Klart",
      actual_today_kwh: 4,
      forecast_so_far_kwh: 5,
      remaining_vs_expected_kwh: 1,
      raw_forecast_so_far_kwh: 8,
    });
    expect(metrics.todayDeviation).toBe(-50);
    expect(metrics.headlineRatio).toBeNull();
  });
});

describe("buildPerformanceMetrics", () => {
  it("formats headline and signed today deviation", () => {
    const metrics = buildPerformanceMetrics({
      headlineRatio: 0.944,
      todayDeviation: -5.6,
      weekAvg: 0.931,
      monthAvg: 0.952,
      quarterAvg: 0.948,
      ytdAvg: 0.951,
    });
    expect(metrics.headlineLabel).toBe("Utmärkt");
    expect(metrics.rows[0].value).toBe("-5,6 %");
    expect(metrics.rows[1].value).toBe("93,1 %");
  });
});
