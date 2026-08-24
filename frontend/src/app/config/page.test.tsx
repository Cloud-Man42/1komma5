import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

const mockFetchHeartbeat = vi.fn();
const mockFetchChargeAmps = vi.fn();
const mockFetchReadiness = vi.fn();
const mockSaveHeartbeat = vi.fn();

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/components/SitesManager", () => ({
  SitesManager: () => <div data-testid="sites-manager">SitesManager</div>,
}));

vi.mock("@/lib/api", () => ({
  fetchHeartbeatConfig: (...args: unknown[]) => mockFetchHeartbeat(...args),
  fetchChargeAmpsConfig: (...args: unknown[]) => mockFetchChargeAmps(...args),
  fetchChargingReadiness: (...args: unknown[]) => mockFetchReadiness(...args),
  saveHeartbeatConfig: (...args: unknown[]) => mockSaveHeartbeat(...args),
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
  implementation_status: "ok",
  notes: [] as string[],
  sites: [] as { slug: string; external_system_id: string | null }[],
  updated_at: null,
  heartbeat_write_enabled: false,
};

describe("ConfigPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchHeartbeat.mockResolvedValue(heartbeatConfig);
    mockFetchChargeAmps.mockResolvedValue({
      mock: true,
      ready: true,
      api_key_configured: false,
      notes: [],
    });
    mockFetchReadiness.mockResolvedValue({
      ready: true,
      active_bridge_chargers: 0,
      chargeamps_ready: true,
      issues: [],
      notes: [],
    });
    mockSaveHeartbeat.mockResolvedValue({ ...heartbeatConfig });
  });

  it("loads heartbeat config and renders SitesManager outside the form", async () => {
    const ConfigPage = (await import("@/app/config/page")).default;
    render(<ConfigPage />);
    expect(await screen.findByTestId("sites-manager")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Spara konfiguration/i })).toBeTruthy();
  });

  it("saves heartbeat config on submit", async () => {
    const user = userEvent.setup();
    const ConfigPage = (await import("@/app/config/page")).default;
    render(<ConfigPage />);
    await screen.findByTestId("sites-manager");
    await user.click(screen.getByRole("button", { name: /Spara konfiguration/i }));
    await waitFor(() => expect(mockSaveHeartbeat).toHaveBeenCalled());
  });

  it("shows heartbeat write toggle and sends flag on save", async () => {
    const user = userEvent.setup();
    const ConfigPage = (await import("@/app/config/page")).default;
    render(<ConfigPage />);
    await screen.findByText(/Synka laddinställningar till Heartbeat/i);
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /Spara konfiguration/i }));
    await waitFor(() =>
      expect(mockSaveHeartbeat).toHaveBeenCalledWith(
        expect.objectContaining({ heartbeat_write_enabled: true }),
      ),
    );
  });
});
