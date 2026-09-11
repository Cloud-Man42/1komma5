import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { InstallWizard } from "./InstallWizard";

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: vi.fn(() => "token"),
}));

vi.mock("@/components/modules-devices/ModulesDevicesNav", () => ({
  ModulesDevicesNav: () => <nav data-testid="nav" />,
}));

vi.mock("@/components/modules-devices/store/ModuleStoreShell", () => ({
  ModuleStoreShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/lib/api", () => ({
  fetchStoreModuleDetail: vi.fn(async () => ({
    summary: {
      display_name: "Sensibo Climate",
      latest_version: "1.0.0",
    },
  })),
  fetchStorePreflight: vi.fn(async () => ({
    display_name: "Sensibo Climate",
    trust_tier: "OFFICIAL",
    publisher_status: "ACTIVE",
    policy: { decision: "ALLOW", explanation: "Read-only module allowed" },
    permissions: [{ permission: "network.external", label: "External network", risk_level: "medium" }],
    compatibility: { compatible: true, reasons: [] },
    sites: [{ site_slug: "akarp", site_name: "Åkarp" }],
    configuration_schema: {},
    install_allowed: true,
    primary_action: "INSTALL",
    runtime_blocked: true,
    runtime_message: "Runtime execution is currently disabled by system policy.",
  })),
  fetchExternalModuleConfig: vi.fn(async () => ({
    module_id: "integration.sensibo",
    site_slug: "akarp",
    credential_configured: false,
    poll_interval_seconds: 300,
    selected_device_ids: [],
  })),
  installStoreModule: vi.fn(),
  testModuleConnection: vi.fn(),
  discoverModuleDevices: vi.fn(),
  upsertExternalModuleConfig: vi.fn(),
}));

describe("InstallWizard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows Sensibo credential step labels", async () => {
    render(<InstallWizard moduleId="integration.sensibo" />);
    expect(await screen.findByText(/Install Sensibo Climate/i)).toBeInTheDocument();
    expect(screen.getByText("Credential")).toBeInTheDocument();
    expect(screen.getByText("Connectivity")).toBeInTheDocument();
    expect(screen.getByText("Discovery")).toBeInTheDocument();
  });

  it("uses default steps for built-in modules", async () => {
    render(<InstallWizard moduleId="integration.heartbeat" />);
    expect(await screen.findByText("Configuration")).toBeInTheDocument();
    expect(screen.queryByText("Credential")).not.toBeInTheDocument();
  });
});
