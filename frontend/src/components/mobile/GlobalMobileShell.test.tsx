import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GlobalMobileShell } from "./GlobalMobileShell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/sites/akarp",
}));

vi.mock("@/lib/useMobileShell", () => ({
  useMobileShell: () => true,
}));

vi.mock("@/lib/MobileShellProvider", () => ({
  useMobileShellContext: () => ({ freshnessLabel: "Live" }),
}));

vi.mock("@/lib/authContext", () => ({
  useAuth: () => ({
    user: { displayName: "Test" },
    loading: false,
    can: () => true,
  }),
}));

vi.mock("@/lib/SiteSelectionProvider", () => ({
  useSiteSelection: () => ({
    loading: false,
    accessibleSites: [{ slug: "akarp", name: "Åkarp" }],
    selectedSlugs: ["akarp"],
    draftSlugs: ["akarp"],
    setDraftSlugs: vi.fn(),
    selectAll: vi.fn(),
    clearAll: vi.fn(),
    toggleDraft: vi.fn(),
    applySelection: vi.fn(),
    navigateToAllSystemsHome: vi.fn(),
    refresh: vi.fn(),
  }),
}));

describe("GlobalMobileShell", () => {
  it("wraps site routes with mobile shell on mobile viewport", () => {
    render(
      <GlobalMobileShell>
        <p>Site content</p>
      </GlobalMobileShell>,
    );
    expect(screen.getByText("Site content")).toBeInTheDocument();
    expect(screen.getByLabelText("Huvudnavigering")).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
  });
});
