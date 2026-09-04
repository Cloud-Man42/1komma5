import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IntegrationHealthPanel } from "@/components/IntegrationHealthPanel";

const mockFetchIntegrationHealth = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchIntegrationHealth: (...args: unknown[]) => mockFetchIntegrationHealth(...args),
  };
});

describe("IntegrationHealthPanel", () => {
  beforeEach(() => {
    mockFetchIntegrationHealth.mockReset();
  });

  it("renders provider rows", async () => {
    mockFetchIntegrationHealth.mockResolvedValue({
      slug: "akarp",
      providers: [
        {
          provider: "heartbeat",
          status: "ok",
          last_success_at: "2026-09-03T12:00:00Z",
          last_attempt_at: "2026-09-03T12:00:00Z",
          latency_ms: 120,
          consecutive_failures: 0,
          stale_seconds: 10,
          circuit_breaker_state: "closed",
          last_error_class: null,
        },
      ],
    });

    render(<IntegrationHealthPanel siteSlug="akarp" />);
    expect(await screen.findByTestId("integration-health-row-heartbeat")).toBeInTheDocument();
    expect(screen.getByText(/Alla registrerade providers/i)).toBeInTheDocument();
  });

  it("shows alert when provider has repeated failures", async () => {
    mockFetchIntegrationHealth.mockResolvedValue({
      slug: "akarp",
      providers: [
        {
          provider: "heartbeat",
          status: "ok",
          last_success_at: "2026-09-03T12:00:00Z",
          last_attempt_at: "2026-09-03T12:00:00Z",
          latency_ms: 120,
          consecutive_failures: 3,
          stale_seconds: 10,
          circuit_breaker_state: "closed",
          last_error_class: null,
        },
      ],
    });

    render(<IntegrationHealthPanel siteSlug="akarp" />);
    await waitFor(() => {
      expect(screen.getByTestId("integration-health-alert")).toBeInTheDocument();
    });
  });

  it("shows alert when provider has failures", async () => {
    mockFetchIntegrationHealth.mockResolvedValue({
      slug: "akarp",
      providers: [
        {
          provider: "heartbeat",
          status: "error",
          last_success_at: null,
          last_attempt_at: "2026-09-03T12:00:00Z",
          latency_ms: null,
          consecutive_failures: 3,
          stale_seconds: null,
          circuit_breaker_state: "open",
          last_error_class: "TimeoutError",
        },
      ],
    });

    render(<IntegrationHealthPanel siteSlug="akarp" />);
    await waitFor(() => {
      expect(screen.getByTestId("integration-health-alert")).toBeInTheDocument();
    });
  });

  it("shows error when API fails", async () => {
    mockFetchIntegrationHealth.mockRejectedValue(new Error("offline"));
    render(<IntegrationHealthPanel siteSlug="akarp" />);
    expect(await screen.findByText("offline")).toBeInTheDocument();
  });
});
