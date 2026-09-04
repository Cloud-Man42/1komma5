import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DisplayOverview } from "@/lib/displayOverview";
import { usePiDashboardData } from "@/lib/usePiDashboardData";

const mockFetchDisplayOverview = vi.fn();

vi.mock("@/lib/displayOverview", async () => {
  const actual = await vi.importActual<typeof import("@/lib/displayOverview")>("@/lib/displayOverview");
  return {
    ...actual,
    fetchDisplayOverview: (...args: unknown[]) => mockFetchDisplayOverview(...args),
  };
});

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  withCredentials: boolean;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string, options?: { withCredentials?: boolean }) {
    this.url = url;
    this.withCredentials = options?.withCredentials ?? false;
    MockEventSource.instances.push(this);
  }

  close() {}
}

const sampleOverview = (): DisplayOverview =>
  ({
    generated_at: "2026-09-03T12:30:00.000Z",
    site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
    freshness: { updated_at: null, data_age_seconds: 10, stale: false, connection_state: "LIVE" },
    live: {},
    sparklines: {},
    weather: { available: true },
    price: { available: true },
    flow: { available: true, nodes: [] },
    vehicle: { available: false },
    charger: { available: false },
    spa: { available: false },
    economy: { available: true, daily: [] },
    highlights: { available: true, items: [] },
    system_status: { status_sv: "OK", detail_sv: "", healthy: true },
  }) as DisplayOverview;

describe("usePiDashboardData", () => {
  beforeEach(() => {
    sessionStorage.clear();
    MockEventSource.instances = [];
    mockFetchDisplayOverview.mockReset();
    mockFetchDisplayOverview.mockResolvedValue(sampleOverview());
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads overview via initial fetch", async () => {
    const { result } = renderHook(() => usePiDashboardData("akarp"));
    await waitFor(() => {
      expect(result.current.data?.site.slug).toBe("akarp");
    });
    expect(mockFetchDisplayOverview).toHaveBeenCalledWith("akarp");
  });

  it("opens display SSE stream with credentials", async () => {
    renderHook(() => usePiDashboardData("akarp"));
    await waitFor(() => {
      expect(MockEventSource.instances.length).toBeGreaterThan(0);
    });
    expect(MockEventSource.instances[0]?.url).toBe("/api/v1/display/overview/akarp/stream");
    expect(MockEventSource.instances[0]?.withCredentials).toBe(true);
  });
});
