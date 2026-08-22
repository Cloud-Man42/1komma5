import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useSiteDashboard } from "@/lib/useSiteDashboard";

const mockFetchSiteDashboard = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchSiteDashboard: (...args: unknown[]) => mockFetchSiteDashboard(...args),
}));

describe("useSiteDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchSiteDashboard.mockResolvedValue({
      site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
      freshness: { updated_at: "2026-08-22T10:00:00Z", data_age_seconds: 12, stale: false },
      live: null,
      today: null,
      ev: null,
      solar: null,
      price: null,
      optimization: null,
      alerts: [],
      spa_integration_enabled: false,
    });
  });

  it("loads dashboard data for slug", async () => {
    const { result } = renderHook(() => useSiteDashboard("akarp"));
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.dashboard?.site.slug).toBe("akarp");
    expect(mockFetchSiteDashboard).toHaveBeenCalledWith("akarp");
  });
});
