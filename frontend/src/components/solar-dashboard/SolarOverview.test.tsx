import { render, screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { SolarOverview } from "./SolarOverview";



const mockFetchSiteDashboard = vi.fn();

const mockFetchSolarConfig = vi.fn();

const mockFetchSolarForecast = vi.fn();

const mockFetchSolarPerformance = vi.fn();

const mockFetchSolarWeather = vi.fn();

const mockFetchSolarAccuracy = vi.fn();

const mockFetchSiteHistory = vi.fn();



vi.mock("@/lib/api", async () => {

  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");

  return {

    ...actual,

    fetchSiteDashboard: (...args: unknown[]) => mockFetchSiteDashboard(...args),

    fetchSolarConfig: (...args: unknown[]) => mockFetchSolarConfig(...args),

    fetchSolarForecast: (...args: unknown[]) => mockFetchSolarForecast(...args),

    fetchSolarPerformance: (...args: unknown[]) => mockFetchSolarPerformance(...args),

    fetchSolarWeather: (...args: unknown[]) => mockFetchSolarWeather(...args),

    fetchSolarAccuracy: (...args: unknown[]) => mockFetchSolarAccuracy(...args),

    fetchSiteHistory: (...args: unknown[]) => mockFetchSiteHistory(...args),

  };

});



vi.mock("@/lib/useDashboardRefresh", () => ({

  useDashboardRefreshSeconds: () => 30,

}));



const forecast = {

  site_id: 1,

  generated_at: new Date().toISOString(),

  model_version: "v2",

  quality: "MEDIUM" as const,

  weather_source: "smhi",

  expected_today_kwh: 18.5,

  remaining_today_kwh: 10,

  expected_tomorrow_kwh: 20,

  peak_power_w: 4200,

  peak_time: null,

  confidence: 0.72,

  lower_today_kwh: 14,

  upper_today_kwh: 22,

  weather_summary: "Delvis molnigt",

  actual_today_kwh: 8.2,

  forecast_so_far_kwh: 7.5,

  remaining_vs_expected_kwh: 10.3,

  points: [

    {

      timestamp: new Date().toISOString(),

      baseline_power_w: 2000,

      corrected_power_w: 2100,

      expected_energy_kwh: 0.5,

      lower_bound_power_w: 1500,

      upper_bound_power_w: 2600,

      confidence: 0.7,

      correction_factor: 1.05,

    },

  ],

};



beforeEach(() => {

  mockFetchSiteDashboard.mockResolvedValue({

    site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },

    freshness: { updated_at: new Date().toISOString(), data_age_seconds: 10, stale: false },

    live: null,

    today: null,

    ev: null,

    solar: null,

    price: null,

    optimization: null,

    alerts: [],

    spa_integration_enabled: false,

    vehicle_integration_enabled: false,

  });

  mockFetchSolarConfig.mockResolvedValue({

    site_slug: "akarp",

    latitude: 55.6,

    longitude: 13.0,

    installed_peak_power_kw: 8.5,

    azimuth_deg: 180,

    tilt_deg: 30,

    inverter_max_power_kw: 8,

    system_loss_percent: 14,

    enabled: true,

    tilt_estimated: false,

    azimuth_estimated: false,

    complete: true,

  });

  mockFetchSolarForecast.mockResolvedValue(forecast);

  mockFetchSolarPerformance.mockResolvedValue({

    site_slug: "akarp",

    days: [

      { date: "2026-08-21", actual_kwh: 16, expected_kwh: 18, performance_ratio: 0.89, anomaly_flag: false },

      { date: "2026-08-22", actual_kwh: 19, expected_kwh: 17, performance_ratio: 1.12, anomaly_flag: false },

    ],

    headline_ratio: 0.95,

    today_deviation_pct: -5,

    week_avg: 0.95,

    month_avg: 0.92,

    quarter_avg: null,

    ytd_avg: null,

    raw_forecast_so_far_kwh: 7.5,

    actual_today_kwh: 8.2,

  });

  mockFetchSolarWeather.mockResolvedValue({

    site_slug: "akarp",

    provider: "SMHI",

    source: "forecast",

    fetched_at: new Date().toISOString(),

    cache_age_minutes: 5,

    sunrise: "2026-08-28T04:30:00Z",

    sunset: "2026-08-28T19:45:00Z",

    current: {

      timestamp: new Date().toISOString(),

      temperature_c: 18,

      cloud_cover_pct: 40,

      wind_speed_ms: 2.5,

      relative_humidity_pct: 65,

      precipitation_mm: 0,

      ghi_wm2: 450,

      weather_code: 2,

      condition_sv: "Delvis molnigt",

      condition_icon: "partly-cloudy",

    },

    solar_impact_sv: "Moln kan dämpa produktionen något.",

    hours: [],

  });

  mockFetchSolarAccuracy.mockResolvedValue({

    site_slug: "akarp",

    model_version: "v2",

    model_state: "CALIBRATED",

    mape_7d_pct: 12,

    mape_30d_pct: 15,

    mape_7d_valid_days: 7,

    mape_30d_valid_days: 28,

    mae_kwh_30d: 1.2,

    mae_kwh_7d: 1.0,

    bias_pct_30d: -3,

    sample_count_30d: 28,

    historical_samples: 45,

    production_days_observed: 50,

    correction_factor: 1.05,

    confidence_score: 72,

    confidence_label: "Hög tilltro",

    metrics_insufficient: false,

    raw_mae_30d: 1.8,

    corrected_mae_30d: 1.2,

    improvement_pct_30d: 33,

    wape_7d_pct: 11,

    wape_30d_pct: 14,

    rmse_kwh_7d: 1.5,

    rmse_kwh_30d: 1.8,

    r2_30d: 0.85,

    insufficient_reason: null,

    min_samples_for_calibrated: 30,

  });

  mockFetchSiteHistory.mockResolvedValue({

    slug: "akarp",

    bucket_minutes: 5,

    readings: [

      {

        recorded_at: new Date().toISOString(),

        solar_production_w: 1800,

        consumption_w: 1200,

        grid_import_w: 0,

        grid_export_w: 600,

        battery_soc_pct: 62,

        battery_power_w: -200,

      },

    ],

  });

});



describe("SolarOverview", () => {

  it("renders solprognos dashboard with key panels", async () => {

    render(<SolarOverview siteSlug="akarp" />);

    expect(await screen.findByTestId("solar-overview")).toBeTruthy();

    expect(screen.getByText(/SOLPROGNOS/i)).toBeTruthy();

    expect(await screen.findByTestId("solar-kpi-strip")).toBeTruthy();

    expect(await screen.findByTestId("solar-production-chart")).toBeTruthy();

    expect(screen.getByTestId("solar-day-stats")).toBeTruthy();

    expect(screen.getByTestId("solar-multiday")).toBeTruthy();

    expect(screen.getByTestId("solar-distribution")).toBeTruthy();

    expect(screen.getByTestId("solar-comparison")).toBeTruthy();

    expect(screen.getByTestId("solar-weather-factors")).toBeTruthy();

    expect(screen.getByTestId("solar-attribution")).toBeTruthy();

  });



  it("exports csv when export button is clicked", async () => {

    const user = userEvent.setup();

    const createObjectURL = vi.fn(() => "blob:test");

    const revokeObjectURL = vi.fn();

    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});



    render(<SolarOverview siteSlug="akarp" />);

    await screen.findByTestId("solar-overview");



    await user.click(screen.getByRole("button", { name: /Exportera data/i }));



    expect(createObjectURL).toHaveBeenCalled();

    expect(clickSpy).toHaveBeenCalled();



    clickSpy.mockRestore();

    vi.unstubAllGlobals();

  });



  it("shows empty state when solar is disabled", async () => {

    mockFetchSolarConfig.mockResolvedValueOnce({

      site_slug: "akarp",

      latitude: null,

      longitude: null,

      installed_peak_power_kw: null,

      azimuth_deg: null,

      tilt_deg: null,

      inverter_max_power_kw: null,

      system_loss_percent: 14,

      enabled: false,

      tilt_estimated: false,

      azimuth_estimated: false,

      complete: false,

    });



    render(<SolarOverview siteSlug="akarp" />);

    expect(await screen.findByText(/Solprognos är inte aktiverad/i)).toBeTruthy();

  });



  it("renders when history is empty and forecast is missing", async () => {
    mockFetchSiteHistory.mockResolvedValueOnce({ slug: "akarp", bucket_minutes: 5, readings: [] });
    mockFetchSolarForecast.mockResolvedValueOnce(null);

    render(<SolarOverview siteSlug="akarp" />);

    expect(await screen.findByTestId("solar-overview")).toBeTruthy();
    expect(screen.getByTestId("solar-kpi-strip")).toBeTruthy();
  });

  it("renders forecast section when hash is prognos", async () => {
    vi.stubGlobal("window", {
      ...window,
      location: { ...window.location, href: "http://localhost/sites/akarp/solar#prognos" },
      addEventListener: window.addEventListener.bind(window),
      removeEventListener: window.removeEventListener.bind(window),
      history: window.history,
      dispatchEvent: window.dispatchEvent.bind(window),
    });

    render(<SolarOverview siteSlug="akarp" />);
    await screen.findByTestId("solar-overview");

    expect(screen.getByText("Prognos")).toBeTruthy();
    expect(screen.queryByTestId("solar-kpi-strip")).toBeNull();

    vi.unstubAllGlobals();
  });

  it("shows dashboard before slow forecast finishes", async () => {
    let resolveForecast: (value: typeof forecast) => void = () => {};
    mockFetchSolarForecast.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveForecast = resolve;
        }),
    );

    render(<SolarOverview siteSlug="akarp" />);
    expect(await screen.findByTestId("solar-overview")).toBeTruthy();
    expect(screen.getByTestId("solar-kpi-strip")).toBeTruthy();

    resolveForecast(forecast);
    await waitFor(() => {
      expect(screen.getByTestId("solar-production-chart")).toBeTruthy();
    });
  });

  it("shows model confidence on 0-100 scale in accuracy section", async () => {
    mockFetchSolarAccuracy.mockResolvedValueOnce({
      site_slug: "akarp",
      model_version: "solar-forecast-v2",
      model_state: "PRELIMINARY",
      mape_7d_pct: 49.9,
      mape_30d_pct: 57.1,
      mape_7d_valid_days: 7,
      mape_30d_valid_days: 13,
      mae_kwh_30d: 18.2,
      mae_kwh_7d: 16,
      bias_pct_30d: -51.6,
      sample_count_30d: 13,
      historical_samples: 13,
      production_days_observed: 13,
      correction_factor: 1.05,
      confidence_score: 14.9,
      confidence_label: "Low",
      metrics_insufficient: false,
      raw_mae_30d: 20,
      corrected_mae_30d: 18.2,
      improvement_pct_30d: 9,
      wape_7d_pct: 48,
      wape_30d_pct: 55,
      rmse_kwh_7d: 16,
      rmse_kwh_30d: 18,
      r2_30d: 0.4,
      insufficient_reason: null,
      min_samples_for_calibrated: 30,
    });

    vi.stubGlobal("window", {
      ...window,
      location: { ...window.location, href: "http://localhost/sites/akarp/solar#modellkvalitet" },
      addEventListener: window.addEventListener.bind(window),
      removeEventListener: window.removeEventListener.bind(window),
      history: window.history,
      dispatchEvent: window.dispatchEvent.bind(window),
    });

    render(<SolarOverview siteSlug="akarp" />);
    await screen.findByTestId("solar-accuracy");

    expect(screen.getByText("15%")).toBeTruthy();
    expect(screen.queryByText("1490%")).toBeNull();

    vi.unstubAllGlobals();
  });
});


