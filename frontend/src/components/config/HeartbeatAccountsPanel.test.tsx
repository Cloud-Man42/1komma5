import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HeartbeatAccountsPanel } from "./HeartbeatAccountsPanel";

vi.mock("@/lib/api", () => ({
  fetchHeartbeatAccounts: vi.fn(),
  fetchHeartbeatConfig: vi.fn(),
  saveHeartbeatConfig: vi.fn(),
  runHeartbeatAccountDiagnostics: vi.fn(),
  testHeartbeatAccountConnection: vi.fn(),
  discoverHeartbeatAccount: vi.fn(),
  createHeartbeatAccount: vi.fn(),
  updateHeartbeatAccount: vi.fn(),
  linkHeartbeatAccountSite: vi.fn(),
}));

import {
  createHeartbeatAccount,
  discoverHeartbeatAccount,
  fetchHeartbeatAccounts,
  fetchHeartbeatConfig,
  linkHeartbeatAccountSite,
  runHeartbeatAccountDiagnostics,
  testHeartbeatAccountConnection,
} from "@/lib/api";

const defaultAccount = {
  id: 1,
  slug: "default",
  name: "Default",
  provider: "1komma5",
  connection_type: "cloud",
  host: "",
  port: 443,
  use_tls: true,
  api_path: "/api",
  username_masked: "u***@example.com",
  password_configured: true,
  api_token_configured: false,
  api_url: "https://heartbeat.1komma5grad.com/api",
  refresh_token_configured: false,
  token_expires_at: null,
  is_enabled: true,
  status: "Healthy",
  linked_sites: ["akarp"],
  last_authentication_at: null,
  last_successful_authentication_at: null,
  last_api_call_at: null,
  last_successful_api_call_at: null,
  last_authentication_error: null,
  updated_at: null,
};

function accountListItem() {
  return within(screen.getByRole("list")).getByRole("listitem");
}

describe("HeartbeatAccountsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchHeartbeatAccounts).mockResolvedValue([defaultAccount]);
    vi.mocked(fetchHeartbeatConfig).mockResolvedValue({
      connection_type: "cloud",
      host: "",
      port: 443,
      use_tls: true,
      api_path: "/api",
      poll_interval_seconds: 60,
      dashboard_refresh_seconds: 30,
      username: "",
      password_configured: false,
      api_token_configured: false,
      api_url: "https://heartbeat.1komma5grad.com/api",
      sites: [],
      notes: [],
      implementation_status: "configured",
      contacting_component: "collector",
      connection_type_label: "Cloud",
    });
    vi.mocked(createHeartbeatAccount).mockResolvedValue({
      ...defaultAccount,
      id: 2,
      slug: "denmark",
      name: "Danmark",
      username_masked: "d***@example.com",
    });
    vi.mocked(linkHeartbeatAccountSite).mockResolvedValue({
      site_slug: "summer-house-denmark",
      heartbeat_account_id: 2,
    });
  });

  it("renders accounts from API", async () => {
    render(<HeartbeatAccountsPanel />);
    const item = await screen.findByRole("listitem");
    expect(within(item).getByText("(default)")).toBeInTheDocument();
    expect(within(item).getByText(/u\*\*\*@example.com/)).toBeInTheDocument();
  });

  it("shows diagnostics result", async () => {
    vi.mocked(runHeartbeatAccountDiagnostics).mockResolvedValue({
      account_id: 1,
      slug: "default",
      token_ok: true,
      token_expires_at: null,
      last_authentication_error: null,
      linked_sites: ["akarp"],
      probes: [{ path: "/systems/x/live-overview", ok: true }],
    });

    render(<HeartbeatAccountsPanel />);
    await screen.findByRole("listitem");
    await userEvent.click(within(accountListItem()).getByRole("button", { name: "Diagnostik" }));

    await waitFor(() => {
      expect(within(accountListItem()).getByText(/live-overview: OK/)).toBeInTheDocument();
    });
  });

  it("creates account from generic form", async () => {
    render(<HeartbeatAccountsPanel />);
    await screen.findByText("Nytt konto");

    await userEvent.type(screen.getByPlaceholderText("akarp"), "denmark");
    await userEvent.type(screen.getByPlaceholderText("Åkarp"), "Danmark");
    await userEvent.type(screen.getByPlaceholderText("user@example.com"), "dk@example.com");
    await userEvent.type(screen.getByPlaceholderText("Lösenord"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Skapa konto" }));

    await waitFor(() => {
      expect(createHeartbeatAccount).toHaveBeenCalledWith(
        expect.objectContaining({
          slug: "denmark",
          username: "dk@example.com",
          password: "secret123",
        }),
      );
    });
  });

  it("requires password when creating account", async () => {
    render(<HeartbeatAccountsPanel />);
    await screen.findByText("Nytt konto");

    await userEvent.type(screen.getByPlaceholderText("akarp"), "denmark");
    await userEvent.type(screen.getByPlaceholderText("Åkarp"), "Danmark");
    await userEvent.type(screen.getByPlaceholderText("user@example.com"), "dk@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Skapa konto" }));

    expect(await screen.findByText("Lösenord krävs när kontot skapas.")).toBeInTheDocument();
    expect(createHeartbeatAccount).not.toHaveBeenCalled();
  });

  it("runs test connection", async () => {
    vi.mocked(testHeartbeatAccountConnection).mockResolvedValue({
      account_id: 1,
      slug: "default",
      connected: true,
      provider: "1komma5",
      api_url: "https://heartbeat.1komma5grad.com/api",
      probe_path: "/account",
      visible_installations: 1,
      last_authentication_error: null,
    });

    render(<HeartbeatAccountsPanel />);
    await screen.findByRole("listitem");
    await userEvent.click(within(accountListItem()).getByRole("button", { name: "Test" }));

    await waitFor(() => {
      expect(testHeartbeatAccountConnection).toHaveBeenCalledWith(1);
      expect(within(accountListItem()).getByText(/Ansluten/)).toBeInTheDocument();
    });
  });

  it("runs discovery and links site", async () => {
    vi.mocked(discoverHeartbeatAccount).mockResolvedValue({
      account_id: 1,
      slug: "default",
      provider: "gridx",
      api_url: "https://api.gridx.de",
      authentication_ok: true,
      installations: [
        {
          name: "Denmark",
          system_id: "91a0e8fc-6e8d-4131-bc49-245d7f3369d9",
          site_id: null,
          asset_id: null,
          device_id: null,
          gateway_id: "40a3b35b-5b7d-4de1-b045-e4f1728cfe74",
          serial_number: "K183-600-000-021-000-P-X",
        },
      ],
      serial_matches: [],
      paths_probed: ["/account"],
    });

    render(<HeartbeatAccountsPanel />);
    await screen.findByRole("listitem");

    const linkForm = screen.getByTestId("heartbeat-link-form");
    const selects = within(linkForm).getAllByRole("combobox");
    await userEvent.selectOptions(selects[0], "1");
    await userEvent.click(within(linkForm).getByRole("button", { name: "Discover" }));

    await waitFor(() => {
      expect(discoverHeartbeatAccount).toHaveBeenCalled();
      expect(screen.getByText(/K183-600-000-021-000-P-X/)).toBeInTheDocument();
    });

    await userEvent.click(within(linkForm).getByRole("button", { name: "Koppla site" }));
    await waitFor(() => {
      expect(linkHeartbeatAccountSite).toHaveBeenCalled();
    });
  });

  it("shows load error", async () => {
    vi.mocked(fetchHeartbeatAccounts).mockRejectedValue(new Error("Network fail"));
    render(<HeartbeatAccountsPanel />);
    expect(await screen.findByText("Network fail")).toBeInTheDocument();
  });
});
