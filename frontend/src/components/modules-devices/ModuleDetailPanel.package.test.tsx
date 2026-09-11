import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ModuleDetailPanel } from "@/components/modules-devices/ModuleDetailPanel";

vi.mock("@/lib/api", () => ({
  fetchSiteModuleDetail: vi.fn(async () => ({
    module_id: "integration.demo",
    name: "Integration Demo",
    version: "1.0.0",
    module_type: "integration",
    enabled: false,
    activation: "disabled",
    runtime_status: "stopped",
    health_status: "unavailable",
    capabilities_provided: ["read.status"],
    capabilities_required: [],
    optional_capabilities: [],
    missing_required_capabilities: [],
    missing_optional_capabilities: [],
    can_start: false,
    can_disable: true,
    package_source: "installed",
    installed_version: "1.0.0",
    publisher: "emic-tests",
    package_state: "installed",
    rollback_available: true,
    update_available: false,
  })),
  fetchModuleConfig: vi.fn(async () => ({
    module_id: "integration.demo",
    config: {},
    configured_fields: {},
    restart_required: "none",
  })),
  updateModuleConfig: vi.fn(),
  applyModuleConfiguration: vi.fn(),
  testModuleConnection: vi.fn(),
}));

describe("ModuleDetailPanel package metadata", () => {
  it("shows installed package metadata", async () => {
    render(<ModuleDetailPanel siteSlug="akarp" moduleId="integration.demo" />);
    expect(await screen.findByTestId("module-package-metadata")).toBeInTheDocument();
    expect(screen.getByText("emic-tests")).toBeInTheDocument();
    expect(screen.getByText(/Rollback till tidigare version/)).toBeInTheDocument();
  });
});
