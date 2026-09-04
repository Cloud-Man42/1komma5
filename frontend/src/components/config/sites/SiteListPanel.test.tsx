import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SiteListPanel } from "@/components/config/sites/SiteListPanel";
import { makeEvCharger, makeSite } from "@/test/fixtures";

const mockFetchSites = vi.fn();
const mockFetchEvChargers = vi.fn();
const mockCreateSite = vi.fn();

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  fetchSites: (...args: unknown[]) => mockFetchSites(...args),
  fetchEvChargers: (...args: unknown[]) => mockFetchEvChargers(...args),
  createSite: (...args: unknown[]) => mockCreateSite(...args),
  updateSite: vi.fn(),
  deleteSite: vi.fn(),
  updateEvCharger: vi.fn(),
  deleteEvCharger: vi.fn(),
  syncEvChargers: vi.fn(),
}));

describe("SiteListPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchSites.mockResolvedValue([makeSite()]);
    mockFetchEvChargers.mockResolvedValue([makeEvCharger()]);
    mockCreateSite.mockResolvedValue(makeSite({ slug: "new-site", name: "New Site" }));
  });

  it("renders site rows with configure links", async () => {
    render(<SiteListPanel />);
    expect(await screen.findByTestId("site-row-akarp")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Konfigurera/i })).toHaveAttribute(
      "href",
      "/config/sites/akarp",
    );
  });

  it("shows empty state when no sites exist", async () => {
    mockFetchSites.mockResolvedValue([]);
    mockFetchEvChargers.mockResolvedValue([]);
    render(<SiteListPanel />);
    expect(await screen.findByText(/Inga anläggningar ännu/i)).toBeTruthy();
  });

  it("creates a site via button click", async () => {
    const user = userEvent.setup();
    render(<SiteListPanel />);
    await screen.findByTestId("site-row-akarp");

    const createForm = screen.getByPlaceholderText("min-anlaggning").closest(".site-create-form") as HTMLElement;
    await user.type(screen.getByPlaceholderText("min-anlaggning"), "new-site");
    await user.type(within(createForm).getByLabelText("Namn"), "New Site");
    await user.click(screen.getByRole("button", { name: /Lägg till anläggning/i }));

    await waitFor(() => {
      expect(mockCreateSite).toHaveBeenCalledWith(
        expect.objectContaining({ slug: "new-site", name: "New Site" }),
      );
    });
  });
});
