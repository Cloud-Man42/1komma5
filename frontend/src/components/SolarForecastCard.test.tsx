"use client";

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SolarForecastCard } from "@/components/SolarForecastCard";

vi.mock("@/lib/api", () => ({
  fetchSolarConfig: vi.fn().mockResolvedValue({
    site_slug: "akarp",
    latitude: 55.6,
    longitude: 13.0,
    installed_peak_power_kw: 8,
    azimuth_deg: 180,
    tilt_deg: 30,
    inverter_max_power_kw: null,
    system_loss_percent: 14,
    enabled: true,
    tilt_estimated: false,
    azimuth_estimated: false,
    complete: true,
  }),
  fetchSolarForecast: vi.fn().mockResolvedValue({
    site_id: 1,
    generated_at: "2026-06-15T08:00:00Z",
    model_version: "solar-forecast-v2",
    quality: "HIGH",
    weather_source: "live",
    expected_today_kwh: 31.8,
    remaining_today_kwh: 18.4,
    actual_today_kwh: 12.5,
    forecast_so_far_kwh: 13.4,
    remaining_vs_expected_kwh: 19.3,
    expected_tomorrow_kwh: 28.0,
    raw_forecast_tomorrow_kwh: 30.0,
    corrected_forecast_tomorrow_kwh: 28.0,
    correction_factor: 0.93,
    model_state: "CALIBRATED",
    confidence_score: 81,
    confidence_label: "High",
    historical_samples: 38,
    peak_power_w: 5900,
    peak_time: "2026-06-15T11:45:00Z",
    confidence: 0.87,
    lower_today_kwh: 27.0,
    upper_today_kwh: 35.0,
    weather_summary: "Sol förhållanden: bra",
    points: [],
  }),
  formatWatts: (w: number) => `${(w / 1000).toFixed(1)} kW`,
}));

describe("SolarForecastCard", () => {
  it("renders forecast summary when config is complete", async () => {
    render(<SolarForecastCard siteSlug="akarp" />);
    expect(await screen.findByText("Solprognos")).toBeTruthy();
    expect(await screen.findByText(/28 kWh/)).toBeTruthy();
    expect(await screen.findByText(/12,5 kWh faktiskt · 13,4 kWh prognos/)).toBeTruthy();
    expect(await screen.findByText(/19,3 kWh/)).toBeTruthy();
    expect(await screen.findByText(/81 % High/)).toBeTruthy();
  });

  it("prompts for setup when config is incomplete", async () => {
    const api = await import("@/lib/api");
    vi.mocked(api.fetchSolarConfig).mockResolvedValueOnce({
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

    render(<SolarForecastCard siteSlug="akarp" />);
    expect(await screen.findByText(/inte konfigurerad/i)).toBeTruthy();
    expect(screen.getByText("Gå till solprofil →")).toBeTruthy();
  });
});
