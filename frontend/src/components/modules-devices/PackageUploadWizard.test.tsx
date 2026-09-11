import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { PackageUploadWizard } from "@/components/modules-devices/PackageUploadWizard";

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/store/upload",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", () => ({
  validateModulePackage: vi.fn(),
  analyzePackageImpact: vi.fn(),
  installModulePackage: vi.fn(),
  updateModulePackage: vi.fn(),
  fetchPackageStoreDetail: vi.fn(),
}));

import { analyzePackageImpact, installModulePackage, validateModulePackage } from "@/lib/api";

describe("PackageUploadWizard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows validation preview and blocks install when not allowed", async () => {
    vi.mocked(validateModulePackage).mockResolvedValue({
      valid: false,
      errors: ["SIGNATURE_INVALID"],
      warnings: [],
      manifest: {
        module_id: "integration.demo",
        name: "Demo",
        version: "1.0.0",
        publisher: "unknown",
        module_type: "integration",
        description: "",
      },
      signed: false,
      signature_valid: false,
      publisher_trusted: false,
      install_allowed: false,
      permissions: ["device.read"],
      provided_capabilities: ["read_status"],
      required_capabilities: [],
      optional_capabilities: [],
      module_dependencies: [],
      minimum_emic_version: "0.1.0",
      maximum_emic_version: null,
      module_api_version: 1,
      compatible_with_emic: false,
    });
    vi.mocked(analyzePackageImpact).mockResolvedValue({
      module_id: "integration.demo",
      affected_modules: [],
      affected_sites: [],
      affected_devices: [],
      capabilities_added: ["read_status"],
      capabilities_removed: [],
      restart_required: true,
      warnings: [],
    });

    render(<PackageUploadWizard />);
    const input = screen.getByLabelText("Välj .emicpkg");
    const file = new File(["zip"], "demo.emicpkg", { type: "application/zip" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("Ogiltig signatur. Paketet kan inte installeras.")).toBeInTheDocument();
      expect(screen.getByText("Installation blockerad")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Installera paket" })).toBeDisabled();
  });

  it("installs when backend allows", async () => {
    vi.mocked(validateModulePackage).mockResolvedValue({
      valid: true,
      errors: [],
      warnings: [],
      manifest: {
        module_id: "integration.demo",
        name: "Demo",
        version: "1.0.0",
        publisher: "emic-tests",
        module_type: "integration",
        description: "",
      },
      signed: true,
      signature_valid: true,
      publisher_trusted: true,
      install_allowed: true,
      permissions: [],
      provided_capabilities: [],
      required_capabilities: [],
      optional_capabilities: [],
      module_dependencies: [],
      minimum_emic_version: "0.1.0",
      maximum_emic_version: null,
      module_api_version: 1,
      compatible_with_emic: true,
    });
    vi.mocked(analyzePackageImpact).mockResolvedValue({
      module_id: "integration.demo",
      affected_modules: [],
      affected_sites: [],
      affected_devices: [],
      capabilities_added: [],
      capabilities_removed: [],
      restart_required: true,
      warnings: [],
    });
    vi.mocked(installModulePackage).mockResolvedValue({
      module_id: "integration.demo",
      success: true,
      message: "Installed",
      package_state: "installed",
      installed_version: "1.0.0",
      restart_required: true,
      rollback_version: null,
    });

    render(<PackageUploadWizard />);
    const input = screen.getByLabelText("Välj .emicpkg");
    fireEvent.change(input, { target: { files: [new File(["zip"], "demo.emicpkg")] } });

    await waitFor(() => expect(screen.getByRole("button", { name: "Installera paket" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Installera paket" }));

    await waitFor(() => {
      expect(installModulePackage).toHaveBeenCalled();
      expect(screen.getByText(/Application restart required/)).toBeInTheDocument();
    });
  });
});
