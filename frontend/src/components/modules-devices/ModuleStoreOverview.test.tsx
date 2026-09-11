import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ModuleStoreOverview } from "@/components/modules-devices/ModuleStoreOverview";

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/store",
}));

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: () => "test-token",
}));

vi.mock("@/lib/api", () => ({
  fetchMarketplaceMetadataStatus: vi.fn().mockResolvedValue({
    enabled: true,
    metadata_health: "healthy",
    revocation_freshness: "fresh",
    last_sync: "2026-09-07T12:00:00Z",
    last_success: "2026-09-07T12:00:00Z",
    last_error: null,
    sync_failed: false,
    offline: false,
    root_version: 2,
    timestamp_version: 1,
    snapshot_version: 1,
    targets_version: 1,
    catalog_age_seconds: 10,
    revocation_age_seconds: 10,
    cache_generation: 1,
    catalog_status: "healthy",
    revocation_status: "fresh",
  }),
  fetchStoreOverview: vi.fn().mockResolvedValue({
    installed: [
      {
        module_id: "integration.demo",
        name: "Demo Integration",
        installed_version: "1.0.0",
        publisher: "emic-tests",
        package_state: "installed",
        signature_status: "unsigned",
        signed: false,
        signature_valid: false,
        publisher_trusted: false,
        publisher_status: "unsigned",
        install_allowed: true,
        rollback_version: null,
        restart_required: true,
        checksum_sha256: "abc",
        enabled_sites: ["akarp"],
        runtime_status: null,
        runtime_version: null,
        version_match: null,
        checksum_match: null,
        runtime_checksum: null,
        needs_attention: false,
        attention_reasons: [],
        metadata: {},
      },
    ],
    catalog: [
      {
        entry_id: "demo-1.0.0",
        module_id: "integration.demo",
        name: "Demo Integration",
        version: "1.0.0",
        publisher: "EMIC Internal",
        description: "Demo module",
        package_filename: "integration.demo-1.0.0.emicpkg",
        trusted: true,
      },
    ],
    needs_attention: [
      {
        module_id: "integration.broken",
        name: "Broken",
        installed_version: "1.0.0",
        publisher: "emic-tests",
        package_state: "quarantined",
        signature_status: "invalid",
        signed: true,
        signature_valid: false,
        publisher_trusted: false,
        install_allowed: false,
        rollback_version: "0.9.0",
        restart_required: true,
        checksum_sha256: "def",
        enabled_sites: [],
        runtime_status: null,
        runtime_version: null,
        version_match: null,
        checksum_match: null,
        runtime_checksum: null,
        needs_attention: true,
        attention_reasons: ["quarantined"],
        metadata: { quarantine_reason: "startup_integrity_failed" },
      },
    ],
    allow_unsigned_modules: true,
  }),
  installCatalogEntry: vi.fn(),
}));

describe("ModuleStoreOverview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders installed, catalog and needs-attention sections", async () => {
    render(<ModuleStoreOverview />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Module Store" })).toBeInTheDocument();
      expect(screen.getAllByText("Demo Integration").length).toBeGreaterThan(0);
      expect(screen.getByTestId("store-package-integration.demo")).toBeInTheDocument();
      expect(screen.getByTestId("catalog-entry-demo-1.0.0")).toBeInTheDocument();
      expect(screen.getByText("Installerade")).toBeInTheDocument();
      expect(screen.getByText("Tillgängliga betrodda paket")).toBeInTheDocument();
      expect(screen.getByText("Behöver uppmärksamhet")).toBeInTheDocument();
      expect(screen.getByText("Karantän")).toBeInTheDocument();
      expect(screen.getByTestId("marketplace-metadata-status")).toBeInTheDocument();
      expect(screen.getByText("Marketplace metadata")).toBeInTheDocument();
    });
  });
});
