import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ModuleStoreOverview } from "@/components/modules-devices/ModuleStoreOverview";

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/store",
}));

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: () => "test-token",
}));

const validateCatalogEntry = vi.fn();
const analyzeCatalogImpact = vi.fn();
const installCatalogEntry = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchMarketplaceMetadataStatus: vi.fn().mockResolvedValue({
    enabled: false,
    metadata_health: "uninitialized",
    revocation_freshness: "unavailable",
    last_sync: null,
    last_success: null,
    last_error: null,
    sync_failed: false,
    offline: false,
    root_version: null,
    timestamp_version: null,
    snapshot_version: null,
    targets_version: null,
    catalog_age_seconds: null,
    revocation_age_seconds: null,
    cache_generation: 0,
    catalog_status: "uninitialized",
    revocation_status: "unavailable",
  }),
  fetchStoreOverview: vi.fn().mockResolvedValue({
    installed: [],
    catalog: [
      {
        entry_id: "integration.demo-1.0.0",
        module_id: "integration.demo",
        name: "Demo Integration",
        version: "1.0.0",
        publisher: "EMIC Internal",
        description: "Demo module",
        package_filename: "integration.demo-1.0.0.emicpkg",
        trusted: true,
      },
    ],
    needs_attention: [],
    allow_unsigned_modules: false,
  }),
  validateCatalogEntry: (...args: unknown[]) => validateCatalogEntry(...args),
  analyzeCatalogImpact: (...args: unknown[]) => analyzeCatalogImpact(...args),
  installCatalogEntry: (...args: unknown[]) => installCatalogEntry(...args),
}));

describe("ModuleStoreOverview catalog flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    validateCatalogEntry.mockResolvedValue({
      valid: true,
      errors: [],
      warnings: [],
      manifest: { module_id: "integration.demo", name: "Demo", version: "1.0.0", publisher: "emic" },
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
    analyzeCatalogImpact.mockResolvedValue({
      module_id: "integration.demo",
      affected_modules: [],
      affected_sites: [],
      affected_devices: [],
      capabilities_added: ["read_status"],
      capabilities_removed: [],
      restart_required: true,
      warnings: [],
    });
    installCatalogEntry.mockResolvedValue({
      module_id: "integration.demo",
      success: true,
      message: "Installed",
      package_state: "installed",
      installed_version: "1.0.0",
      restart_required: true,
      rollback_version: null,
    });
  });

  it("reviews catalog package before install", async () => {
    render(<ModuleStoreOverview />);
    await waitFor(() => expect(screen.getByText("Granska katalogpaket")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Granska katalogpaket"));
    await waitFor(() => expect(validateCatalogEntry).toHaveBeenCalledWith("integration.demo-1.0.0"));
    fireEvent.click(screen.getByText("Bekräfta installation"));
    fireEvent.click(screen.getByText("Installera från intern katalog"));
    await waitFor(() => expect(installCatalogEntry).toHaveBeenCalledWith("integration.demo-1.0.0"));
  });
});
