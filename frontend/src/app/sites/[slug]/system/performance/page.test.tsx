import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PerformanceCenterPage from "./page";

const mockFetchPerformanceMetrics = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchPerformanceMetrics: (...args: unknown[]) => mockFetchPerformanceMetrics(...args),
  };
});

describe("PerformanceCenterPage", () => {
  beforeEach(() => {
    mockFetchPerformanceMetrics.mockResolvedValue({
      request_count: 12,
      cache: { hits: 8, misses: 4, hit_rate_pct: 66.7 },
      slowest_routes: [{ route: "/api/sites/akarp/snapshot", count: 5, p50_ms: 120, p95_ms: 150 }],
      slowest_requests: [],
      slow_queries: [],
      providers: [{ provider: "heartbeat", calls: 3, avg_ms: 80, errors: 0 }],
      site_snapshots: [
        {
          site_slug: "akarp",
          site_name: "Demo Home",
          age_seconds: 12,
          freshness: "FRESH",
        },
      ],
    });
  });

  it("renders snapshot age per site", async () => {
    render(<PerformanceCenterPage />);
    await waitFor(() => {
      expect(screen.getByText("Snapshot per site")).toBeTruthy();
      expect(screen.getByText("Demo Home")).toBeTruthy();
      expect(screen.getByText("12s")).toBeTruthy();
      expect(screen.getByText("FRESH")).toBeTruthy();
    });
  });
});
