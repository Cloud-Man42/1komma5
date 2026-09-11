import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MarketplaceSecurityPanel } from "./MarketplaceSecurityPanel";

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/marketplace/security",
}));

vi.mock("@/lib/adminAuth", () => ({ getAdminToken: () => "token" }));

const fetchMarketplaceCatalog = vi.fn();
const fetchMarketplaceRelease = vi.fn();
const fetchMarketplaceArtifactSecurity = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchMarketplaceCatalog: (...args: unknown[]) => fetchMarketplaceCatalog(...args),
  fetchMarketplaceRelease: (...args: unknown[]) => fetchMarketplaceRelease(...args),
  fetchMarketplaceArtifactSecurity: (...args: unknown[]) => fetchMarketplaceArtifactSecurity(...args),
}));

describe("MarketplaceSecurityPanel", () => {
  beforeEach(() => {
    fetchMarketplaceCatalog.mockResolvedValue({
      releases: [
        {
          module_id: "integration.demo",
          publisher_id: "emic-tests",
          version: "1.0.0",
          release_id: "integration.demo@1.0.0",
          content_sha256: "abc",
          artifact_size: 100,
          source: "PUBLIC",
        },
      ],
      catalog_version: 2,
    });
    fetchMarketplaceRelease.mockResolvedValue({
      artifact_id: 1,
      state: "STAGED",
      reason_codes: [],
      security_status: "NONE",
      policy_decision: "ALLOW",
      message: "ok",
    });
    fetchMarketplaceArtifactSecurity.mockResolvedValue({
      artifact_id: 1,
      integrity_verified: true,
      sbom_status: "MISSING",
      advisory_status: "TRUSTED",
      highest_severity: "NONE",
      vulnerability_count: 0,
      critical_count: 0,
      high_count: 0,
      security_review_required: false,
      policy_decision: "ALLOW",
      reason_codes: [],
      vulnerabilities: [],
      runtime_blocked: true,
      runtime_message: "Runtime: BLOCKED until Step 5C.5",
    });
  });

  it("lists catalog releases from API", async () => {
    render(<MarketplaceSecurityPanel />);
    expect(await screen.findByTestId("release-integration.demo-1.0.0")).toBeInTheDocument();
  });

  it("shows security detail after fetch", async () => {
    render(<MarketplaceSecurityPanel />);
    await screen.findByTestId("release-integration.demo-1.0.0");
    await userEvent.click(screen.getByRole("button", { name: "Fetch & stage" }));
    await waitFor(() => expect(screen.getByTestId("release-security-detail")).toBeInTheDocument());
    expect(screen.getByTestId("runtime-blocked")).toHaveTextContent("Runtime: BLOCKED until Step 5C.5");
  });

  it("shows error when catalog fetch fails", async () => {
    fetchMarketplaceCatalog.mockRejectedValue(new Error("503 disabled"));
    render(<MarketplaceSecurityPanel />);
    expect(await screen.findByText("503 disabled")).toBeInTheDocument();
  });
});
