import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SitesManager } from "@/components/SitesManager";
import { makeEvCharger, makeSite } from "@/test/fixtures";

const mockFetchSites = vi.fn();
const mockFetchEvChargers = vi.fn();
const mockCreateSite = vi.fn();
const mockUpdateSite = vi.fn();
const mockDeleteSite = vi.fn();
const mockCreateEvCharger = vi.fn();
const mockUpdateEvCharger = vi.fn();
const mockDeleteEvCharger = vi.fn();
const mockSyncEvChargers = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchSites: (...args: unknown[]) => mockFetchSites(...args),
  fetchEvChargers: (...args: unknown[]) => mockFetchEvChargers(...args),
  createSite: (...args: unknown[]) => mockCreateSite(...args),
  updateSite: (...args: unknown[]) => mockUpdateSite(...args),
  deleteSite: (...args: unknown[]) => mockDeleteSite(...args),
  createEvCharger: (...args: unknown[]) => mockCreateEvCharger(...args),
  updateEvCharger: (...args: unknown[]) => mockUpdateEvCharger(...args),
  deleteEvCharger: (...args: unknown[]) => mockDeleteEvCharger(...args),
  syncEvChargers: (...args: unknown[]) => mockSyncEvChargers(...args),
  fetchChargerManufacturers: vi.fn().mockResolvedValue([
    { id: "charge-amps", name: "Charge Amps", model_count: 5 },
  ]),
  fetchChargerModels: vi.fn().mockResolvedValue([
    {
      id: "halo",
      manufacturer_id: "charge-amps",
      name: "Halo",
      status: "FULL",
      supported_protocols: ["CLOUD_API"],
      integration_methods: ["CHARGE_AMPS_CLOUD"],
      capabilities: {},
    },
  ]),
  fetchChargerModelDetail: vi.fn().mockResolvedValue({
    model: { id: "halo", name: "Halo", status: "FULL" },
    integration_methods: [
      {
        id: "CHARGE_AMPS_CLOUD",
        label: "Charge Amps Cloud API",
        connection_type: "CLOUD",
        recommended: true,
      },
    ],
  }),
}));

vi.mock("@/components/SolarSiteConfigPanel", () => ({
  SolarSiteConfigPanel: ({ siteSlug }: { siteSlug: string }) => (
    <div data-testid={`solar-panel-${siteSlug}`}>Solar panel</div>
  ),
}));

describe("SitesManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchSites.mockResolvedValue([makeSite()]);
    mockFetchEvChargers.mockResolvedValue([makeEvCharger()]);
    mockCreateSite.mockResolvedValue(makeSite({ slug: "new-site", name: "New Site" }));
  });

  it("renders sites and solar config panels outside nested forms", async () => {
    render(<SitesManager />);
    expect(await screen.findByDisplayValue("Åkarp")).toBeTruthy();
    expect(screen.getByTestId("solar-panel-akarp")).toBeTruthy();
  });

  it("creates a site via button click without form submit", async () => {
    const user = userEvent.setup();
    render(<SitesManager />);
    await screen.findByDisplayValue("Åkarp");

    await user.type(screen.getByPlaceholderText("min-anlaggning"), "new-site");
    await user.type(screen.getAllByLabelText("Namn")[0], "New Site");
    await user.click(screen.getByRole("button", { name: /Lägg till anläggning/i }));

    await waitFor(() => {
      expect(mockCreateSite).toHaveBeenCalledWith(
        expect.objectContaining({ slug: "new-site", name: "New Site" }),
      );
    });
  });

  it("shows API error when loading fails", async () => {
    mockFetchSites.mockRejectedValueOnce(new Error("Network error"));
    render(<SitesManager />);
    expect(await screen.findByText("Network error")).toBeTruthy();
  });
});
