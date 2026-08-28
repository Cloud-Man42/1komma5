import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SolarWeather } from "@/lib/api";
import { WeatherSolarPanel } from "./WeatherSolarPanel";
import { normalizeIconKey } from "./weatherIcons";

const weather: SolarWeather = {
  site_slug: "akarp",
  provider: "open-meteo",
  source: "live",
  fetched_at: "2026-08-27T08:00:00Z",
  cache_age_minutes: 0,
  sunrise: "2026-08-27T03:37:00Z",
  sunset: "2026-08-27T18:32:00Z",
  solar_impact_sv: "Goda solförhållanden — nära full produktion",
  current: {
    timestamp: "2026-08-27T08:00:00Z",
    temperature_c: 18.4,
    cloud_cover_pct: 5,
    wind_speed_ms: 3.1,
    relative_humidity_pct: 52,
    precipitation_mm: 0,
    ghi_wm2: 540,
    weather_code: 0,
    condition_sv: "Klart",
    condition_icon: "clear",
  },
  hours: [
    {
      timestamp: "2026-08-27T08:00:00Z",
      temperature_c: 18.4,
      cloud_cover_pct: 5,
      wind_speed_ms: 3.1,
      relative_humidity_pct: 52,
      precipitation_mm: 0,
      ghi_wm2: 540,
      weather_code: 0,
      condition_sv: "Klart",
      condition_icon: "clear",
      forecast_power_w: 2400,
    },
    {
      timestamp: "2026-08-27T09:00:00Z",
      temperature_c: 19.2,
      cloud_cover_pct: 20,
      wind_speed_ms: 2.8,
      relative_humidity_pct: 49,
      precipitation_mm: 0,
      ghi_wm2: 640,
      weather_code: 1,
      condition_sv: "Mestadels klart",
      condition_icon: "mostly-clear",
      forecast_power_w: 3100,
    },
  ],
};

describe("WeatherSolarPanel", () => {
  it("renders live temperature, condition and metrics", () => {
    render(<WeatherSolarPanel weather={weather} timezone="UTC" />);
    expect(screen.getByText("18,4 °C")).toBeTruthy();
    expect(screen.getByText("Klart")).toBeTruthy();
    expect(screen.getByText("3,1 m/s")).toBeTruthy();
    expect(screen.getByText("52 %")).toBeTruthy();
    expect(screen.getByText("5 %")).toBeTruthy();
    expect(screen.getByText("540 W/m²")).toBeTruthy();
  });

  it("shows solar impact text and sun times", () => {
    render(<WeatherSolarPanel weather={weather} timezone="UTC" />);
    expect(screen.getByText(/Goda solförhållanden/)).toBeTruthy();
    expect(screen.getByText("Soluppgång 03:37")).toBeTruthy();
    expect(screen.getByText("Solnedgång 18:32")).toBeTruthy();
  });

  it("renders the hourly strip", () => {
    render(<WeatherSolarPanel weather={weather} timezone="UTC" />);
    expect(screen.getByLabelText("Timprognos")).toBeTruthy();
    expect(screen.getByText("09:00")).toBeTruthy();
  });

  it("shows an error message instead of data when the request failed", () => {
    render(<WeatherSolarPanel weather={null} error="Väderdata otillgänglig" />);
    expect(screen.getByText("Väderdata otillgänglig")).toBeTruthy();
    expect(screen.queryByLabelText("Timprognos")).toBeNull();
  });

  it("shows a loading hint while weather is missing", () => {
    render(<WeatherSolarPanel weather={null} />);
    expect(screen.getByText("Hämtar väderdata…")).toBeTruthy();
  });

  it("renders dashes when measurements are missing", () => {
    const sparse: SolarWeather = {
      ...weather,
      solar_impact_sv: "",
      sunrise: null,
      sunset: null,
      current: {
        ...weather.current!,
        temperature_c: null,
        wind_speed_ms: null,
        relative_humidity_pct: null,
        cloud_cover_pct: null,
        ghi_wm2: null,
        condition_sv: "Okänt",
        condition_icon: "unknown",
      },
      hours: [],
    };
    render(<WeatherSolarPanel weather={sparse} timezone="UTC" />);
    expect(screen.getByText("Okänt")).toBeTruthy();
    expect(screen.getByText("Ingen timprognos tillgänglig")).toBeTruthy();
    expect(screen.getByText("Soluppgång —")).toBeTruthy();
  });

  it("notes cached and fallback sources", () => {
    const { rerender } = render(
      <WeatherSolarPanel weather={{ ...weather, source: "cache", cache_age_minutes: 12.4 }} timezone="UTC" />,
    );
    expect(screen.getByText(/cache 12 min/)).toBeTruthy();

    rerender(<WeatherSolarPanel weather={{ ...weather, source: "fallback" }} timezone="UTC" />);
    expect(screen.getByText(/reservdata/)).toBeTruthy();
  });
});

describe("normalizeIconKey", () => {
  it("passes through known icon keys", () => {
    expect(normalizeIconKey("clear")).toBe("clear");
    expect(normalizeIconKey("thunder")).toBe("thunder");
  });

  it("falls back to unknown for unrecognised or missing keys", () => {
    expect(normalizeIconKey("meteor-shower")).toBe("unknown");
    expect(normalizeIconKey(null)).toBe("unknown");
    expect(normalizeIconKey(undefined)).toBe("unknown");
  });
});
