import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { IntegrationHealthStrip } from "./IntegrationHealthStrip";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  fetchIntegrationHealth: vi.fn(),
}));

import { fetchIntegrationHealth } from "@/lib/api";

describe("IntegrationHealthStrip", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows ok summary", async () => {
    vi.mocked(fetchIntegrationHealth).mockResolvedValue({
      slug: "akarp",
      overall_health_status: "healthy",
      providers: [
        {
          provider: "heartbeat",
          status: "ok",
          health_status: "healthy",
          consecutive_failures: 0,
          last_success_at: null,
          last_attempt_at: null,
          latency_ms: 12,
          stale_seconds: 10,
          circuit_breaker_state: null,
          last_error_class: null,
        },
      ],
    });
    render(<IntegrationHealthStrip siteSlug="akarp" />);
    expect(await screen.findByText(/1 integrationer OK/i)).toBeInTheDocument();
  });

  it("shows alert count", async () => {
    vi.mocked(fetchIntegrationHealth).mockResolvedValue({
      slug: "akarp",
      overall_health_status: "degraded",
      providers: [
        {
          provider: "heartbeat",
          status: "stale",
          health_status: "degraded",
          consecutive_failures: 0,
          last_success_at: null,
          last_attempt_at: null,
          latency_ms: null,
          stale_seconds: 900,
          circuit_breaker_state: null,
          last_error_class: null,
        },
      ],
    });
    render(<IntegrationHealthStrip siteSlug="akarp" />);
    expect(await screen.findByTestId("integration-health-strip-alert")).toBeInTheDocument();
  });
});
