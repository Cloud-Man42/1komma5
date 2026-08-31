import { describe, expect, it, vi } from "vitest";

import type { Reading, SolarForecast, SolarPerformance, SolarWeather } from "@/lib/api";

import {

  buildComparisonBars,

  buildDayStats,

  buildKpiMetrics,

  buildMultiDayOverview,

  buildPeriodDistribution,

  buildProductionChartSeries,

  buildTomorrowForecast,

  buildWeatherFactors,

  exportSolarCsv,

  tomorrowDateKey,

  weatherAttribution,

} from "./solarDashboardHelpers";

import { parseSolarSection, readSolarSectionFromLocation, solarSectionHref } from "./solarSection";



const TZ = "Europe/Stockholm";

const NOW = "2026-08-27T10:00:00Z";



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



function reading(iso: string, solarW: number, soc?: number): Reading {

  return {

    recorded_at: iso,

    solar_production_w: solarW,

    consumption_w: 0,

    grid_import_w: 0,

    grid_export_w: 0,

    battery_soc_pct: soc ?? null,

    battery_power_w: 0,

  };

}



const baseForecast: SolarForecast = {

  site_id: 1,

  generated_at: NOW,

  model_version: "v2",

  quality: "MEDIUM",

  weather_source: "smhi",

  expected_today_kwh: 20,

  remaining_today_kwh: 10,

  expected_tomorrow_kwh: 18,

  peak_power_w: 4000,

  peak_time: null,

  confidence: 0.72,

  lower_today_kwh: 14,

  upper_today_kwh: 24,

  weather_summary: "Klart",

  actual_today_kwh: 8.5,

  forecast_so_far_kwh: 7.2,

  remaining_vs_expected_kwh: 12.8,

  points: [

    forecastPoint("2026-08-27T06:30:00Z", 2000),

    forecastPoint("2026-08-27T07:00:00Z", 3000),

    forecastPoint("2026-08-27T11:00:00Z", 2500),

    forecastPoint("2026-08-28T07:00:00Z", 2800),

  ],

};



describe("solarSection", () => {

  it("parses hash sections", () => {

    expect(parseSolarSection("#prognos")).toBe("forecast");

    expect(parseSolarSection("")).toBe("overview");

  });



  it("builds hrefs", () => {
    expect(solarSectionHref("akarp", "overview")).toBe("/sites/akarp/solar");
    expect(solarSectionHref("akarp", "forecast")).toBe("/sites/akarp/solar#prognos");
  });

  it("reads section from window location", () => {
    vi.stubGlobal("window", {
      location: { href: "http://localhost/sites/akarp/solar#vader" },
    });
    expect(readSolarSectionFromLocation()).toBe("weather");
    vi.unstubAllGlobals();
  });
});



describe("solarDashboardHelpers", () => {

  it("builds KPI metrics from forecast", () => {

    const kpi = buildKpiMetrics(baseForecast, new Date(NOW));

    expect(kpi.forecastTodayKwh).toBe(20);

    expect(kpi.producedSoFarKwh).toBe(8.5);

    expect(kpi.confidencePct).toBe(72);

    expect(kpi.intervalLabel).toContain("14");

  });



  it("builds production chart with actual and forecast", () => {

    const series = buildProductionChartSeries({

      readings: [reading("2026-08-27T06:32:00Z", 1800, 55)],

      forecast: baseForecast,

      performance: null,

      timezone: TZ,

      now: NOW,

    });

    expect(series.length).toBeGreaterThan(0);

    expect(series.some((p) => p.forecastKw != null)).toBe(true);

    expect(series.some((p) => p.batterySocPct != null)).toBe(true);

  });



  it("builds production chart with hourly forecast and actual readings", () => {

    const hourlyForecast: SolarForecast = {

      ...baseForecast,

      points: [

        {

          ...forecastPoint("2026-08-27T05:00:00Z", 2000),

          expected_energy_kwh: 2,

        },

        {

          ...forecastPoint("2026-08-27T06:00:00Z", 3000),

          expected_energy_kwh: 3,

        },

      ],

    };

    const series = buildProductionChartSeries({

      readings: [

        reading("2026-08-27T05:20:00Z", 1600, 55),

        reading("2026-08-27T05:50:00Z", 2400, 56),

      ],

      forecast: hourlyForecast,

      performance: null,

      timezone: TZ,

      now: NOW,

    });

    expect(series.some((p) => p.actualKw != null && p.actualKw > 0)).toBe(true);

    expect(series.some((p) => p.forecastKw != null)).toBe(true);

  });



  it("builds period distribution for today", () => {

    const slices = buildPeriodDistribution(baseForecast, TZ, NOW);

    expect(slices).toHaveLength(4);

    expect(slices.reduce((sum, s) => sum + s.kwh, 0)).toBeGreaterThan(0);

  });



  it("builds multi-day overview with honest partial labels", () => {

    const rows = buildMultiDayOverview(baseForecast, TZ, NOW);

    expect(rows.length).toBeGreaterThan(0);

    expect(rows.length).toBeLessThanOrEqual(7);

    const today = rows.find((r) => r.label === "Idag");

    expect(today?.expectedKwh).toBe(20);

  });



  it("sums hourly points via expected_energy_kwh", () => {

    const hourlyForecast: SolarForecast = {

      ...baseForecast,

      points: [

        { ...forecastPoint("2026-08-27T08:00:00Z", 4000), expected_energy_kwh: 2.5 },

        { ...forecastPoint("2026-08-27T09:00:00Z", 5000), expected_energy_kwh: 3.0 },

      ],

    };

    const rows = buildMultiDayOverview(hourlyForecast, TZ, NOW);

    const today = rows.find((r) => r.label === "Idag");

    expect(today?.expectedKwh).toBe(20);

  });



  it("builds comparison bars from performance days", () => {

    const performance: SolarPerformance = {

      site_slug: "akarp",

      days: [

        { date: "2026-08-20", actual_kwh: 15, expected_kwh: 16, performance_ratio: 0.94, anomaly_flag: false },

        { date: "2026-08-21", actual_kwh: 17, expected_kwh: 16, performance_ratio: 1.06, anomaly_flag: false },

      ],

      headline_ratio: 1,

      today_deviation_pct: 0,

      week_avg: 1,

      month_avg: 1,

      quarter_avg: null,

      ytd_avg: null,

      raw_forecast_so_far_kwh: null,

      actual_today_kwh: null,

    };

    const bars = buildComparisonBars(performance);

    expect(bars).toHaveLength(2);

    expect(bars[1]?.ratioPct).toBeCloseTo(106.25, 0);

  });



  it("builds weather factors from hours", () => {

    const weather: SolarWeather = {

      site_slug: "akarp",

      provider: "SMHI",

      source: "forecast",

      fetched_at: NOW,

      cache_age_minutes: 0,

      sunrise: null,

      sunset: null,

      current: null,

      solar_impact_sv: "",

      hours: [

        {

          timestamp: "2026-08-27T08:00:00Z",

          temperature_c: 20,

          cloud_cover_pct: 30,

          wind_speed_ms: 3,

          relative_humidity_pct: 60,

          precipitation_mm: 0.5,

          ghi_wm2: 500,

          weather_code: 1,

          condition_sv: "Klart",

          condition_icon: "clear",

        },

      ],

    };

    const factors = buildWeatherFactors(weather, TZ, NOW);

    expect(factors.maxGhi).toBe(500);

    expect(factors.avgTempC).toBe(20);

  });



  it("builds day stats with specific yield", () => {

    const stats = buildDayStats({

      forecast: baseForecast,

      readings: [reading("2026-08-27T07:00:00Z", 3000)],

      weather: {

        site_slug: "akarp",

        provider: "SMHI",

        source: "forecast",

        fetched_at: NOW,

        cache_age_minutes: 0,

        sunrise: "2026-08-27T04:00:00Z",

        sunset: "2026-08-27T19:00:00Z",

        current: null,

        solar_impact_sv: "",

        hours: [],

      },

      config: {

        site_slug: "akarp",

        latitude: 55,

        longitude: 13,

        installed_peak_power_kw: 8.5,

        azimuth_deg: 180,

        tilt_deg: 30,

        inverter_max_power_kw: 8,

        system_loss_percent: 14,

        enabled: true,

        tilt_estimated: false,

        azimuth_estimated: false,

        complete: true,

      },

      timezone: TZ,

      now: NOW,

    });

    expect(stats.maxForecastKw).toBe(3);

    expect(stats.specificYieldWhPerWp).toBeGreaterThan(0);

  });



  it("attributes weather provider", () => {

    expect(weatherAttribution("SMHI")).toContain("SMHI");

    expect(weatherAttribution("dmi")).toContain("DMI");

  });



  it("exports csv without throwing", () => {

    const anchor = { click: vi.fn() } as unknown as HTMLAnchorElement;

    const createElement = vi.spyOn(document, "createElement").mockReturnValue(anchor);

    const createObjectURL = vi.fn(() => "blob:test");

    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL: vi.fn() });



    exportSolarCsv([

      {

        label: "08:00",

        sortKey: 1,

        forecastKw: 2,

        actualKw: 1.8,

        yesterdayKw: null,

        batterySocPct: 55,

      },

    ]);



    expect(createObjectURL).toHaveBeenCalled();

    expect(anchor.click).toHaveBeenCalled();

    createElement.mockRestore();

    vi.unstubAllGlobals();

  });

});



describe("tomorrow forecast helpers", () => {

  it("resolves tomorrow date key in site timezone", () => {

    expect(tomorrowDateKey("2026-08-28T10:00:00Z", "Europe/Stockholm")).toBe("2026-08-29");

  });



  it("does not show stale total without tomorrow points", () => {

    const result = buildTomorrowForecast(

      {

        ...baseForecast,

        generated_at: "2026-08-26T22:00:00Z",

        expected_tomorrow_kwh: 26.9,

        points: [

          forecastPoint("2026-08-28T07:00:00Z", 2800),

        ],

      },

      TZ,

      "2026-08-28T10:00:00Z",

    );



    expect(result.expectedKwh).toBeNull();

    expect(result.points).toHaveLength(0);

    expect(result.message).toContain("inaktuell");

  });



  it("shows chart and total when tomorrow points exist", () => {

    const result = buildTomorrowForecast(

      {

        ...baseForecast,

        generated_at: "2026-08-28T08:00:00Z",

        expected_tomorrow_kwh: 5.5,

        points: [

          forecastPoint("2026-08-29T07:00:00Z", 2800),

          forecastPoint("2026-08-29T08:00:00Z", 3200),

        ],

      },

      TZ,

      "2026-08-28T10:00:00Z",

    );



    expect(result.expectedKwh).toBe(1.5);

    expect(result.points.length).toBeGreaterThan(0);

    expect(result.message).toBeNull();

  });

});


