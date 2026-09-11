import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SiteModulesPanel } from "./SiteModulesPanel";

const mockFetchSiteModules = vi.fn();
const mockUpdateSiteModule = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchSiteModules: (...args: unknown[]) => mockFetchSiteModules(...args),
  updateSiteModule: (...args: unknown[]) => mockUpdateSiteModule(...args),
}));

describe("SiteModulesPanel", () => {
  beforeEach(() => {
    mockFetchSiteModules.mockResolvedValue({
      site_slug: "akarp",
      modules: [
        {
          module_id: "feature.smart-charging",
          name: "Smart Charging",
          version: "1.0.0",
          module_type: "feature",
          enabled: true,
          activation: "enabled",
          runtime_status: "running",
          health_status: "healthy",
          capabilities_provided: ["smart_charging"],
          capabilities_required: ["ev_charger.start"],
          optional_capabilities: [],
          missing_required_capabilities: [],
          missing_optional_capabilities: [],
          can_start: true,
        },
      ],
    });
    mockUpdateSiteModule.mockResolvedValue({
      module_id: "feature.smart-charging",
      name: "Smart Charging",
      version: "1.0.0",
      module_type: "feature",
      enabled: false,
      activation: "disabled",
      runtime_status: "stopped",
      health_status: "unknown",
      capabilities_provided: ["smart_charging"],
      capabilities_required: ["ev_charger.start"],
      optional_capabilities: [],
      missing_required_capabilities: [],
      missing_optional_capabilities: [],
      can_start: false,
    });
  });

  it("renders module table", async () => {
    render(<SiteModulesPanel siteSlug="akarp" />);
    expect(await screen.findByTestId("site-modules-panel")).toBeTruthy();
    expect(screen.getByText("Smart Charging")).toBeTruthy();
    expect(screen.getByText("feature.smart-charging")).toBeTruthy();
  });

  it("shows API error", async () => {
    mockFetchSiteModules.mockRejectedValueOnce(new Error("offline"));
    render(<SiteModulesPanel siteSlug="akarp" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("offline");
  });

  it("calls update on toggle", async () => {
    render(<SiteModulesPanel siteSlug="akarp" />);
    await screen.findByText("Inaktivera");
    screen.getByRole("button", { name: "Inaktivera" }).click();
    await waitFor(() => {
      expect(mockUpdateSiteModule).toHaveBeenCalledWith("akarp", "feature.smart-charging", false);
    });
  });
});
