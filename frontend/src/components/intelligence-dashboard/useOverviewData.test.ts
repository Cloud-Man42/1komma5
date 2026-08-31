import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SolarLayoutProvider } from "@/lib/SolarLayoutContext";
import { createElement } from "react";

const mockFetchSolarConfig = vi.fn();
const mockFetchSolarWeather = vi.fn();
const mockFetchSiteHistory = vi.fn();
const mockFetchSolarForecast = vi.fn();
const mockFetchSolarPerformance = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchSolarConfig: (...args: unknown[]) => mockFetchSolarConfig(...args),
  fetchSolarWeather: (...args: unknown[]) => mockFetchSolarWeather(...args),
  fetchSiteHistory: (...args: unknown[]) => mockFetchSiteHistory(...args),
  fetchSolarForecast: (...args: unknown[]) => mockFetchSolarForecast(...args),
  fetchSolarPerformance: (...args: unknown[]) => mockFetchSolarPerformance(...args),
}));

describe("useOverviewExtraData", () => {
  beforeEach(() => {
    mockFetchSolarConfig.mockReset();
    mockFetchSolarWeather.mockReset();
    mockFetchSiteHistory.mockReset();
    mockFetchSolarForecast.mockReset();
    mockFetchSolarPerformance.mockReset();

    mockFetchSiteHistory.mockResolvedValue({ readings: [] });
    mockFetchSolarForecast.mockResolvedValue(null);
    mockFetchSolarPerformance.mockResolvedValue(null);
  });

  it("reuses solar config and weather from layout context", async () => {
    const { useOverviewExtraData } = await import("./useOverviewData");
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(
        SolarLayoutProvider,
        {
          config: { site_slug: "akarp", enabled: true, complete: true },
          weather: { site_slug: "akarp", provider: "open-meteo", source: "cache", hours: [] },
        },
        children,
      );

    const { result } = renderHook(() => useOverviewExtraData("akarp"), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(mockFetchSolarConfig).not.toHaveBeenCalled();
    expect(mockFetchSolarWeather).not.toHaveBeenCalled();
    expect(mockFetchSiteHistory).toHaveBeenCalledTimes(1);
    expect(result.current.config?.enabled).toBe(true);
    expect(result.current.weather?.provider).toBe("open-meteo");
  });

  it("fetches config and weather when layout context is absent", async () => {
    const { useOverviewExtraData } = await import("./useOverviewData");
    mockFetchSolarConfig.mockResolvedValue({ site_slug: "akarp", enabled: true, complete: false });
    mockFetchSolarWeather.mockResolvedValue({ site_slug: "akarp", provider: "open-meteo", source: "live", hours: [] });

    const { result } = renderHook(() => useOverviewExtraData("akarp"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(mockFetchSolarConfig).toHaveBeenCalledWith("akarp");
    expect(mockFetchSolarWeather).toHaveBeenCalledWith("akarp");
  });
});
