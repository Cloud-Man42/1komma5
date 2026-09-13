import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { HomeDashboardButton } from "./HomeDashboardButton";

const navigateToAllSystemsHome = vi.fn(async () => {});

vi.mock("next/navigation", () => ({
  usePathname: () => "/sites/akarp/energy",
}));

vi.mock("@/lib/SiteSelectionProvider", () => ({
  useSiteSelection: () => ({
    loading: false,
    accessibleSites: [
      { slug: "akarp", name: "Åkarp" },
      { slug: "summer-house-denmark", name: "Danmark" },
    ],
    selectedSlugs: ["akarp"],
    navigateToAllSystemsHome,
  }),
}));

describe("HomeDashboardButton", () => {
  it("navigates to all-systems home on click", () => {
    render(<HomeDashboardButton />);
    fireEvent.click(screen.getByRole("button", { name: "Hem — alla anläggningar" }));
    expect(navigateToAllSystemsHome).toHaveBeenCalledTimes(1);
  });
});
