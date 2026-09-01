import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  fetchChargeFinderStatus: vi.fn(),
  fetchChargeFinderDiagnostics: vi.fn(),
  fetchChargeFinderRawLookup: vi.fn(),
  runChargeFinderTestLookup: vi.fn(),
}));

import ChargeFinderAdminPage from "./page";
import {
  fetchChargeFinderDiagnostics,
  fetchChargeFinderStatus,
} from "@/lib/api";

describe("ChargeFinderAdminPage", () => {
  beforeEach(() => {
    vi.mocked(fetchChargeFinderStatus).mockResolvedValue({
      health_status: "AVAILABLE",
      enabled: true,
      mode: "WEB",
      search_radius_m: 150,
      cache_ttl_seconds: 604800,
      last_success_at: null,
      last_failure_at: null,
      last_lookup_at: null,
      last_latency_ms: null,
      consecutive_failures: 0,
      last_error: null,
      cache_hits: 0,
      cache_misses: 0,
      parser_failures: 0,
      blocked_until: null,
      browser_status: null,
      parsing_version: "1",
      metrics: {},
    });
    vi.mocked(fetchChargeFinderDiagnostics).mockResolvedValue({
      health_status: "AVAILABLE",
      enabled: true,
      mode: "WEB",
      search_radius_m: 150,
      cache_ttl_seconds: 604800,
      last_success_at: null,
      last_failure_at: null,
      last_lookup_at: null,
      last_latency_ms: null,
      consecutive_failures: 0,
      last_error: null,
      cache_hits: 0,
      cache_misses: 0,
      parser_failures: 0,
      blocked_until: null,
      browser_status: null,
      parsing_version: "1",
      metrics: {},
    });
  });

  it("renders ChargeFinder status and test controls", async () => {
    render(<ChargeFinderAdminPage />);
    expect(await screen.findByText("ChargeFinder Integration")).toBeInTheDocument();
    expect(screen.getByText("Test ChargeFinder lookup")).toBeInTheDocument();
    expect(screen.getByText("AVAILABLE")).toBeInTheDocument();
  });
});
