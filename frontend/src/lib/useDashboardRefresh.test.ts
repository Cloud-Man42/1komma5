import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDashboardRefreshSeconds } from "./useDashboardRefresh";

vi.mock("@/lib/api", () => ({
  fetchHeartbeatConfig: vi.fn(),
}));

import { fetchHeartbeatConfig } from "@/lib/api";

describe("useDashboardRefreshSeconds", () => {
  beforeEach(() => {
    vi.mocked(fetchHeartbeatConfig).mockResolvedValue({
      connection_type: "mock",
      connection_type_label: "Mock",
      host: "",
      port: 443,
      use_tls: true,
      api_path: "/api",
      poll_interval_seconds: 60,
      dashboard_refresh_seconds: 8,
      api_url: null,
      username: "",
      password_configured: false,
      api_token_configured: false,
      connection_mode: "outbound_polling",
      contacting_component: "collector",
      implementation_status: "mock",
      notes: [],
      sites: [],
      updated_at: null,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads refresh interval from config", async () => {
    const { result } = renderHook(() => useDashboardRefreshSeconds());
    await waitFor(() => expect(result.current).toBe(8));
  });
});
