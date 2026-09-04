import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SiteConfigDetail } from "@/components/config/sites/SiteConfigDetail";
import { makeEvCharger, makeSite } from "@/test/fixtures";

const mockFetchSites = vi.fn();
const mockFetchEvChargers = vi.fn();
const mockReplace = vi.fn();
const mockSearchParams = new URLSearchParams();

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
}));

vi.mock("@/lib/api", () => ({
  fetchSites: (...args: unknown[]) => mockFetchSites(...args),
  fetchEvChargers: (...args: unknown[]) => mockFetchEvChargers(...args),
  updateSite: vi.fn(),
  deleteSite: vi.fn(),
  updateEvCharger: vi.fn(),
  deleteEvCharger: vi.fn(),
  syncEvChargers: vi.fn(),
  fetchChargerManufacturers: vi.fn().mockResolvedValue([]),
  fetchChargerModels: vi.fn().mockResolvedValue([]),
  fetchChargerModelDetail: vi.fn().mockResolvedValue({ model: {}, integration_methods: [] }),
}));

vi.mock("@/components/SolarSiteConfigPanel", () => ({
  SolarSiteConfigPanel: ({ siteSlug }: { siteSlug: string }) => (
    <div data-testid={`solar-panel-${siteSlug}`}>Solar panel</div>
  ),
}));

vi.mock("@/components/SpaAdminPanel", () => ({
  SpaAdminPanel: ({ siteSlug }: { siteSlug: string }) => (
    <div data-testid={`spa-admin-${siteSlug}`}>Spa admin</div>
  ),
}));

vi.mock("@/components/MercedesAdminPanel", () => ({
  MercedesAdminPanel: ({ siteSlug }: { siteSlug: string }) => (
    <div data-testid={`mercedes-admin-${siteSlug}`}>Mercedes admin</div>
  ),
}));

vi.mock("@/components/HeartbeatVirtualBridgePanel", () => ({
  HeartbeatVirtualBridgePanel: () => <div data-testid="bridge-panel">Bridge</div>,
}));

describe("SiteConfigDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams.delete("tab");
    mockFetchSites.mockResolvedValue([makeSite()]);
    mockFetchEvChargers.mockResolvedValue([makeEvCharger()]);
  });

  it("renders general tab by default", async () => {
    render(<SiteConfigDetail slug="akarp" />);
    expect(await screen.findByTestId("site-general-akarp")).toBeTruthy();
    expect(screen.queryByTestId("solar-panel-akarp")).toBeNull();
  });

  it("switches to solar tab from query param", async () => {
    mockSearchParams.set("tab", "solar");
    render(<SiteConfigDetail slug="akarp" />);
    expect(await screen.findByTestId("solar-panel-akarp")).toBeTruthy();
    expect(screen.queryByTestId("site-general-akarp")).toBeNull();
  });

  it("changes tab via tab buttons", async () => {
    render(<SiteConfigDetail slug="akarp" />);
    await screen.findByTestId("site-general-akarp");
    fireEvent.click(screen.getByRole("tab", { name: "Spa" }));
    expect(mockReplace).toHaveBeenCalledWith("/config/sites/akarp?tab=spa");
  });

  it("shows not found for unknown slug", async () => {
    mockFetchSites.mockResolvedValue([]);
    mockFetchEvChargers.mockResolvedValue([]);
    render(<SiteConfigDetail slug="missing" />);
    expect(await screen.findByText(/hittades inte/i)).toBeTruthy();
  });
});
