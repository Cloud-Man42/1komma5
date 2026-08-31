import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MercedesAdminPage from "./page";

vi.mock("@/lib/api", () => ({
  fetchVehicleIntegrationStatus: vi.fn(async () => ({
    site_slug: "akarp",
    provider: "mercedes",
    enabled: true,
    region: "Europe",
    username: "user@example.com",
    password_configured: true,
    connection_state: "CONNECTED",
    commands_enabled: false,
    token_expires_at: null,
    last_error: null,
    last_error_at: null,
    backoff_until: null,
    blocked_since: null,
    reconnect_count: 0,
    http_429_count: 0,
    decode_failure_count: 0,
    health: "HEALTHY",
  })),
  fetchVehicleIntegrationDiagnostics: vi.fn(async () => ({
    site_slug: "akarp",
    health_status: "CONNECTED",
    connection_state: "CONNECTED",
    consecutive_failures: 0,
    recent_events: [],
  })),
  fetchVehicleRawAttributes: vi.fn(async () => ({
    site_slug: "akarp",
    observations: [
      {
        attribute_name: "soc",
        source: "WS",
        value_type: "int",
        masked_sample: "72",
        first_seen_at: "2026-08-31T12:00:00Z",
        last_seen_at: "2026-08-31T12:00:00Z",
        sample_count: 3,
      },
    ],
  })),
  runVehicleIntegrationAction: vi.fn(async () => ({ success: true, message: "ok" })),
}));

describe("MercedesAdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders diagnostics and masked raw attributes", async () => {
    render(<MercedesAdminPage />);
    expect(await screen.findByText("Mercedes Integration")).toBeInTheDocument();
    expect(await screen.findByText("soc")).toBeInTheDocument();
    expect(screen.getByText("72")).toBeInTheDocument();
  });
});
