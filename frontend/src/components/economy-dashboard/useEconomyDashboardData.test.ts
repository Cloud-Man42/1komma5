import { renderHook } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

const mockFetchFinancialStats = vi.fn();
const mockFetchYearForecast = vi.fn();
const mockFetchMarketPrices = vi.fn();
const mockFetchSiteDashboard = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchFinancialStats: (...args: unknown[]) => mockFetchFinancialStats(...args),
  fetchYearForecast: (...args: unknown[]) => mockFetchYearForecast(...args),
  fetchMarketPrices: (...args: unknown[]) => mockFetchMarketPrices(...args),
  fetchSiteDashboard: (...args: unknown[]) => mockFetchSiteDashboard(...args),
}));

vi.mock("@/lib/SiteDataProvider", () => ({
  useOptionalSiteData: () => ({ dashboard: null }),
}));

import { useEconomyDashboardData } from "./useEconomyDashboardData";

describe("useEconomyDashboardData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockFetchFinancialStats.mockResolvedValue({ stats: [], timezone: "Europe/Stockholm" });
    mockFetchYearForecast.mockResolvedValue(null);
    mockFetchMarketPrices.mockResolvedValue(null);
    mockFetchSiteDashboard.mockResolvedValue(null);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("polls financial stats on interval", async () => {
    renderHook(() => useEconomyDashboardData("akarp"));
    await vi.advanceTimersByTimeAsync(0);
    const afterMount = mockFetchFinancialStats.mock.calls.length;
    expect(afterMount).toBeGreaterThanOrEqual(1);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(mockFetchFinancialStats.mock.calls.length).toBeGreaterThan(afterMount);
  });
});
