import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

const mockFetchHeartbeat = vi.fn();
const mockFetchChargeAmps = vi.fn();
const mockFetchReadiness = vi.fn();
const mockFetchSites = vi.fn();

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  fetchHeartbeatConfig: (...args: unknown[]) => mockFetchHeartbeat(...args),
  fetchChargeAmpsConfig: (...args: unknown[]) => mockFetchChargeAmps(...args),
  fetchChargingReadiness: (...args: unknown[]) => mockFetchReadiness(...args),
  fetchSites: (...args: unknown[]) => mockFetchSites(...args),
}));

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: () => "",
}));

const heartbeatConfig = {
  connection_type: "mock" as const,
  connection_type_label: "Mock",
  host: "",
  port: 443,
  use_tls: true,
  api_path: "/api",
  poll_interval_seconds: 60,
  dashboard_refresh_seconds: 30,
  api_url: null,
  username: "",
  password_configured: false,
  api_token_configured: false,
  connection_mode: "mock",
  contacting_component: "collector",
  implementation_status: "configured",
  notes: [] as string[],
  sites: [] as { slug: string; external_system_id: string | null }[],
  updated_at: null,
};

describe("ConfigOverviewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchHeartbeat.mockResolvedValue(heartbeatConfig);
    mockFetchChargeAmps.mockResolvedValue({
      mock: true,
      ready: true,
      provider: "chargeamps",
      effective_provider: "chargeamps",
      api_key_configured: false,
      notes: [],
    });
    mockFetchReadiness.mockResolvedValue({
      ready: true,
      active_bridge_chargers: 1,
      chargeamps_ready: true,
      issues: [],
      notes: [],
    });
    mockFetchSites.mockResolvedValue([
      {
        slug: "akarp",
        name: "Demo Home",
        timezone: "Europe/Stockholm",
        external_system_id: "uuid",
        fallback_purchase_price_sek_kwh: 1,
        export_compensation_sek_kwh: 0.5,
        main_fuse_a: 25,
        safety_margin_a: 2,
      },
    ]);
  });

  it("renders overview status cards with links", async () => {
    const ConfigPage = (await import("@/app/config/page")).default;
    render(<ConfigPage />);
    expect(await screen.findByTestId("config-overview")).toBeTruthy();
    expect(screen.getByRole("link", { name: /System & Heartbeat/i })).toHaveAttribute(
      "href",
      "/config/system",
    );
    expect(screen.getByRole("link", { name: /Anläggningar/i })).toHaveAttribute(
      "href",
      "/config/sites",
    );
  });

  it("shows readiness issues when present", async () => {
    mockFetchReadiness.mockResolvedValue({
      ready: false,
      active_bridge_chargers: 0,
      chargeamps_ready: false,
      issues: [
        {
          site_slug: "akarp",
          charger_id: 1,
          charger_name: "Halo",
          code: "missing_bridge",
          message: "Bridge saknas",
        },
      ],
      notes: [],
    });
    const ConfigPage = (await import("@/app/config/page")).default;
    render(<ConfigPage />);
    await waitFor(() => expect(screen.getByRole("heading", { name: /Aktuella varningar/i })).toBeTruthy());
    expect(screen.getAllByText(/Bridge saknas/i).length).toBeGreaterThan(0);
  });
});
