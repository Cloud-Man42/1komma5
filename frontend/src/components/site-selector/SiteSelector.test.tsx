import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SiteSelector } from "./SiteSelector";

vi.mock("next/navigation", () => ({ usePathname: () => "/sites/akarp" }));

vi.mock("@/lib/SiteSelectionProvider", () => ({
  useSiteSelection: () => ({
    loading: false,
    accessibleSites: [
      { slug: "akarp", name: "Åkarp" },
      { slug: "summer-house-denmark", name: "Danmark" },
    ],
    selectedSlugs: ["akarp", "summer-house-denmark"],
    draftSlugs: ["akarp", "summer-house-denmark"],
    toggleDraft: vi.fn(),
    selectAll: vi.fn(),
    clearAll: vi.fn(),
    applySelection: vi.fn(),
  }),
}));

describe("SiteSelector", () => {
  it("renders all-sites label when every site is selected", () => {
    render(<SiteSelector />);
    expect(screen.getByText(/Alla anläggningar/)).toBeInTheDocument();
  });

  it("opens panel with site list", () => {
    render(<SiteSelector />);
    fireEvent.click(screen.getByText(/Alla anläggningar/));
    expect(screen.getByText("Åkarp")).toBeInTheDocument();
    expect(screen.getByText("Danmark")).toBeInTheDocument();
  });
});
