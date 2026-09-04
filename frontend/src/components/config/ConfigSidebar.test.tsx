import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfigSidebar } from "@/components/config/ConfigSidebar";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className} {...rest}>
      {children}
    </a>
  ),
}));

const mockUsePathname = vi.fn(() => "/config");

vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

describe("ConfigSidebar", () => {
  it("marks overview as active on /config", () => {
    mockUsePathname.mockReturnValue("/config");
    render(<ConfigSidebar />);
    const overview = screen.getByRole("link", { name: /Översikt/i });
    expect(overview.className).toContain("config-sidebar-link-active");
    expect(overview).toHaveAttribute("aria-current", "page");
  });

  it("marks sites section active for nested site routes", () => {
    mockUsePathname.mockReturnValue("/config/sites/akarp");
    render(<ConfigSidebar />);
    const sites = screen.getByRole("link", { name: /Anläggningar/i });
    expect(sites.className).toContain("config-sidebar-link-active");
  });

  it("renders all navigation links", () => {
    mockUsePathname.mockReturnValue("/config/system");
    render(<ConfigSidebar />);
    expect(screen.getByRole("link", { name: /System/i })).toHaveAttribute("href", "/config/system");
    expect(screen.getByRole("link", { name: /Display & enheter/i })).toHaveAttribute(
      "href",
      "/config/displays",
    );
    expect(screen.getByRole("link", { name: /Admin & säkerhet/i })).toHaveAttribute(
      "href",
      "/config/admin",
    );
    expect(screen.getByRole("link", { name: "Integrationer Mercedes, ChargeFinder m.m." })).toHaveAttribute(
      "href",
      "/config/integrations",
    );
  });
});
