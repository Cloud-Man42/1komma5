import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OrganizationPolicyPanel } from "@/components/modules-devices/governance/OrganizationPolicyPanel";

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/governance/policy",
}));

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: () => "test-token",
}));

const fetchInstallationPolicy = vi.fn();
const updateInstallationPolicy = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchInstallationPolicy: (...args: unknown[]) => fetchInstallationPolicy(...args),
  updateInstallationPolicy: (...args: unknown[]) => updateInstallationPolicy(...args),
}));

describe("OrganizationPolicyPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchInstallationPolicy.mockResolvedValue({
      policy_scope: "installation",
      policy_version: 1,
      allowed_tiers: ["OFFICIAL", "VERIFIED", "ORG_APPROVED"],
      publisher_allowlist: [],
      publisher_denylist: [],
      module_allowlist: [],
      module_denylist: [],
      blocked_permissions: [],
      control_module_policy: "VERIFIED_OK",
      break_glass_enabled: false,
      updated_by: null,
      updated_at: null,
    });
  });

  it("renders allowed tiers from API", async () => {
    render(<OrganizationPolicyPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("organization-policy-panel")).toBeInTheDocument();
      expect(screen.getByText("OFFICIAL")).toBeInTheDocument();
    });
  });

  it("shows conflict message on version mismatch", async () => {
    updateInstallationPolicy.mockRejectedValue(new Error("409 Policy version conflict"));
    render(<OrganizationPolicyPanel />);
    await screen.findByText("OFFICIAL");
    fireEvent.click(screen.getByRole("button", { name: "Save policy" }));
    await waitFor(() => {
      expect(screen.getByText(/Policy conflict/i)).toBeInTheDocument();
    });
  });
});
