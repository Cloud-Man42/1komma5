import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PackageStoreDetailPanel } from "@/components/modules-devices/PackageStoreDetailPanel";

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/store/integration.demo",
}));

const fetchPackageStoreDetail = vi.fn();
const fetchPackageSiteActivations = vi.fn();
const analyzePackageImpact = vi.fn();
const rollbackModulePackage = vi.fn();
const removeModulePackage = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchPackageStoreDetail: (...args: unknown[]) => fetchPackageStoreDetail(...args),
  fetchPackageSiteActivations: (...args: unknown[]) => fetchPackageSiteActivations(...args),
  analyzePackageImpact: (...args: unknown[]) => analyzePackageImpact(...args),
  rollbackModulePackage: (...args: unknown[]) => rollbackModulePackage(...args),
  removeModulePackage: (...args: unknown[]) => removeModulePackage(...args),
}));

const basePackage = {
  module_id: "integration.demo",
  name: "Demo Integration",
  installed_version: "1.0.0",
  publisher: "emic-tests",
  package_state: "installed",
  signature_status: "valid",
  signed: true,
  signature_valid: true,
  publisher_trusted: true,
  publisher_status: "trusted",
  install_allowed: true,
  rollback_version: "0.9.0",
  restart_required: false,
  checksum_sha256: "abc123",
  enabled_sites: ["akarp"],
  runtime_status: "running",
  runtime_version: "1.0.0",
  version_match: true,
  checksum_match: true,
  runtime_checksum: "abc123",
  needs_attention: false,
  attention_reasons: [],
  metadata: { permissions: ["read.metrics"], provided_capabilities: ["demo.cap"] },
};

describe("PackageStoreDetailPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchPackageStoreDetail.mockResolvedValue(basePackage);
    fetchPackageSiteActivations.mockResolvedValue([
      { site_slug: "akarp", site_name: "Demo Home", enabled: true, runtime_status: "running", runtime_version: "1.0.0" },
      { site_slug: "summer-house-denmark", site_name: "Summer House", enabled: false, runtime_status: null, runtime_version: null },
    ]);
    analyzePackageImpact.mockResolvedValue({
      affected_sites: [],
      affected_devices: [],
      affected_modules: [],
      capabilities_removed: [],
      restart_required: true,
    });
  });

  it("renders package detail and site activations", async () => {
    render(<PackageStoreDetailPanel moduleId="integration.demo" />);
    await waitFor(() => {
      expect(screen.getByTestId("package-store-detail")).toBeInTheDocument();
      expect(screen.getByText("Demo Integration")).toBeInTheDocument();
      expect(screen.getByText("Demo Home")).toBeInTheDocument();
      expect(screen.getByText("Summer House")).toBeInTheDocument();
    });
  });

  it("blocks remove when impact analysis reports dependents", async () => {
    analyzePackageImpact.mockResolvedValueOnce({
      affected_sites: ["akarp"],
      affected_devices: ["ev-1"],
      affected_modules: ["integration.demo"],
      capabilities_removed: ["demo.cap"],
      restart_required: true,
    });
    render(<PackageStoreDetailPanel moduleId="integration.demo" />);
    await screen.findByText("Demo Integration");
    fireEvent.click(screen.getByRole("button", { name: /Remove package/i }));
    expect(await screen.findByText(/Remove blocked/)).toBeInTheDocument();
    expect(removeModulePackage).not.toHaveBeenCalled();
  });

  it("shows quarantine error and disables rollback", async () => {
    fetchPackageStoreDetail.mockResolvedValue({
      ...basePackage,
      package_state: "quarantined",
      metadata: { quarantine_reason: "startup_integrity_failed" },
    });
    render(<PackageStoreDetailPanel moduleId="integration.demo" />);
    await waitFor(() => {
      expect(screen.getByText(/quarantine/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Rollback/i })).toBeDisabled();
    });
  });
});
