import { describe, expect, it } from "vitest";
import type { Reading, SolarForecast } from "@/lib/api";
import {
  buildProductionChartData,
  chartYMax,
  hasForecastSeries,
} from "./productionChartData";

const TZ = "Europe/Stockholm";
const NOW = "2026-08-27T08:00:00Z";

function reading(iso: string, solarW: number): Reading {
  return {
    bucket_start: iso,
    bucket_end: iso,
    solar_production_w: solarW,
    consumption_w: 0,
    grid_import_w: 0,
    grid_export_w: 0,
    battery_soc_pct: 0,
    battery_power_w: 0,
    sample_count: 1,
  };
}

function forecastPoint(iso: string, correctedW: number): SolarForecast["points"][number] {
  return {
    timestamp: iso,
    baseline_power_w: correctedW,
    corrected_power_w: correctedW,
    expected_energy_kwh: correctedW / 4000,
    lower_bound_power_w: 0,
    upper_bound_power_w: correctedW * 1.2,
    confidence: 0.6,
    correction_factor: 1,
  };
}

describe("buildProductionChartData", () => {
  it("aligns today's forecast with readings in 15-min buckets", () => {
    const forecast: SolarForecast = {
      site_id: 1,
      generated_at: NOW,
      model_version: "v2",
      quality: "MEDIUM",
      weather_source: "live",
      expected_today_kwh: 20,
      remaining_today_kwh: 10,
      expected_tomorrow_kwh: 20,
      peak_power_w: 3000,
      peak_time: null,
      confidence: 0.6,
      lower_today_kwh: 10,
      upper_today_kwh: 30,
      weather_summary: "Klart",
      actual_today_kwh: 5,
      forecast_so_far_kwh: 4,
      remaining_vs_expected_kwh: 15,
      points: [
        forecastPoint("2026-08-27T06:30:00Z", 2000),
        forecastPoint("2026-08-27T06:45:00Z", 2500),
      ],
    };

    const rows = buildProductionChartData({
      readings: [
        reading("2026-08-26T06:30:00Z", 9999),
        reading("2026-08-27T06:32:00Z", 1800),
        reading("2026-08-27T06:46:00Z", 2200),
      ],
      forecast,
      timezone: TZ,
      now: NOW,
    });

    expect(rows).toHaveLength(2);
    expect(rows[0]?.forecastKw).toBe(2);
    expect(rows[0]?.actualKw).toBe(1.8);
    expect(rows[1]?.forecastKw).toBe(2.5);
    expect(rows[1]?.actualKw).toBe(2.2);
  });

  it("ignores yesterday readings that share the same clock label", () => {
    const forecast: SolarForecast = {
      site_id: 1,
      generated_at: NOW,
      model_version: "v2",
      quality: "MEDIUM",
      weather_source: "live",
      expected_today_kwh: 20,
      remaining_today_kwh: 10,
      expected_tomorrow_kwh: 20,
      peak_power_w: 3000,
      peak_time: null,
      confidence: 0.6,
      lower_today_kwh: 10,
      upper_today_kwh: 30,
      weather_summary: "Klart",
      actual_today_kwh: 5,
      forecast_so_far_kwh: 4,
      remaining_vs_expected_kwh: 15,
      points: [forecastPoint("2026-08-27T07:00:00Z", 3000)],
    };

    const rows = buildProductionChartData({
      readings: [reading("2026-08-26T07:00:00Z", 5000)],
      forecast,
      timezone: TZ,
      now: NOW,
    });

    expect(rows).toHaveLength(1);
    expect(rows[0]?.actualKw).toBeNull();
    expect(rows[0]?.forecastKw).toBe(3);
  });

  it("aligns hourly forecast with readings in 1h buckets", () => {
    const forecast: SolarForecast = {
      site_id: 1,
      generated_at: NOW,
      model_version: "v2",
      quality: "MEDIUM",
      weather_source: "live",
      expected_today_kwh: 20,
      remaining_today_kwh: 10,
      expected_tomorrow_kwh: 20,
      peak_power_w: 3000,
      peak_time: null,
      confidence: 0.6,
      lower_today_kwh: 10,
      upper_today_kwh: 30,
      weather_summary: "Klart",
      actual_today_kwh: 5,
      forecast_so_far_kwh: 4,
      remaining_vs_expected_kwh: 15,
      points: [
        forecastPoint("2026-08-27T05:00:00Z", 2000),
        forecastPoint("2026-08-27T06:00:00Z", 3000),
      ],
    };

    const rows = buildProductionChartData({
      readings: [
        reading("2026-08-27T05:20:00Z", 1800),
        reading("2026-08-27T05:40:00Z", 2200),
        reading("2026-08-27T06:10:00Z", 2800),
      ],
      forecast,
      timezone: TZ,
      now: NOW,
      bucketMinutes: 60,
    });

    expect(rows).toHaveLength(2);
    expect(rows[0]?.forecastKw).toBe(2);
    expect(rows[0]?.actualKw).toBe(2);
    expect(rows[1]?.forecastKw).toBe(3);
    expect(rows[1]?.actualKw).toBe(2.8);
  });

  it("includes actual readings before the first forecast point", () => {
    const forecast: SolarForecast = {
      site_id: 1,
      generated_at: "2026-08-29T08:00:00Z",
      model_version: "v2",
      quality: "MEDIUM",
      weather_source: "live",
      expected_today_kwh: 20,
      remaining_today_kwh: 10,
      expected_tomorrow_kwh: 20,
      peak_power_w: 3000,
      peak_time: null,
      confidence: 0.6,
      lower_today_kwh: 10,
      upper_today_kwh: 30,
      weather_summary: "Klart",
      actual_today_kwh: 2.3,
      forecast_so_far_kwh: 4,
      remaining_vs_expected_kwh: 15,
      points: [
        forecastPoint("2026-08-29T08:00:00Z", 1928),
        forecastPoint("2026-08-29T09:00:00Z", 1729),
      ],
    };

    const rows = buildProductionChartData({
      readings: [
        reading("2026-08-29T05:10:00Z", 272),
        reading("2026-08-29T05:20:00Z", 400),
        reading("2026-08-29T07:25:00Z", 1516),
        reading("2026-08-29T07:35:00Z", 2271),
      ],
      forecast,
      timezone: TZ,
      now: "2026-08-29T08:00:00Z",
    });

    expect(rows.some((row) => row.actualKw != null && row.actualKw > 0 && row.forecastKw == null)).toBe(true);
    const preForecast = rows.filter(
      (row) => row.sort < new Date("2026-08-29T08:00:00Z").getTime() && row.actualKw != null,
    );
    expect(preForecast.length).toBeGreaterThan(0);
    expect(preForecast.some((row) => (row.actualKw ?? 0) > 1)).toBe(true);
  });

  it("overlaps forecast and actual on the same buckets", () => {
    const forecast: SolarForecast = {
      site_id: 1,
      generated_at: "2026-08-29T08:45:00Z",
      model_version: "v2",
      quality: "MEDIUM",
      weather_source: "live",
      expected_today_kwh: 20,
      remaining_today_kwh: 10,
      expected_tomorrow_kwh: 20,
      peak_power_w: 3000,
      peak_time: null,
      confidence: 0.6,
      lower_today_kwh: 10,
      upper_today_kwh: 30,
      weather_summary: "Klart",
      actual_today_kwh: 2.3,
      forecast_so_far_kwh: 4,
      remaining_vs_expected_kwh: 15,
      points: [
        forecastPoint("2026-08-28T22:00:00Z", 0),
        forecastPoint("2026-08-29T05:00:00Z", 800),
        forecastPoint("2026-08-29T08:00:00Z", 2000),
        forecastPoint("2026-08-29T09:00:00Z", 3000),
      ],
    };

    const rows = buildProductionChartData({
      readings: [
        reading("2026-08-29T05:10:00Z", 720),
        reading("2026-08-29T08:05:00Z", 1800),
        reading("2026-08-29T08:40:00Z", 2600),
      ],
      forecast,
      timezone: TZ,
      now: "2026-08-29T08:45:00Z",
    });

    const overlap = rows.filter((row) => row.actualKw != null && row.forecastKw != null);
    expect(overlap.length).toBeGreaterThan(0);
    expect(overlap.some((row) => row.actualKw > 0 && row.forecastKw > 0)).toBe(true);
  });

  it("overlaps forecast and actual on the same 15-min grid for hourly forecast", () => {
    const forecast: SolarForecast = {
      site_id: 1,
      generated_at: "2026-08-29T08:00:00Z",
      model_version: "v2",
      quality: "MEDIUM",
      weather_source: "live",
      expected_today_kwh: 20,
      remaining_today_kwh: 10,
      expected_tomorrow_kwh: 20,
      peak_power_w: 3000,
      peak_time: null,
      confidence: 0.6,
      lower_today_kwh: 10,
      upper_today_kwh: 30,
      weather_summary: "Klart",
      actual_today_kwh: 2.3,
      forecast_so_far_kwh: 4,
      remaining_vs_expected_kwh: 15,
      points: [
        forecastPoint("2026-08-29T08:00:00Z", 2000),
        forecastPoint("2026-08-29T09:00:00Z", 3000),
      ],
    };

    const rows = buildProductionChartData({
      readings: [
        reading("2026-08-29T08:05:00Z", 1800),
        reading("2026-08-29T08:20:00Z", 2200),
        reading("2026-08-29T08:40:00Z", 2600),
      ],
      forecast,
      timezone: TZ,
      now: "2026-08-29T08:45:00Z",
    });

    const overlap = rows.filter((row) => row.actualKw != null && row.forecastKw != null);
    expect(overlap.length).toBeGreaterThan(0);
    expect(overlap.every((row) => row.forecastKw === 2)).toBe(true);
  });

  it("detects when forecast series has values", () => {
    const rows = [
      { timestamp: "t", time: "09:00", sort: 1, actualKw: 1, forecastKw: 2 },
      { timestamp: "t2", time: "09:15", sort: 2, actualKw: null, forecastKw: 0 },
    ];
    expect(hasForecastSeries(rows)).toBe(true);
    expect(chartYMax(rows)).toBeGreaterThan(2);
  });
});
