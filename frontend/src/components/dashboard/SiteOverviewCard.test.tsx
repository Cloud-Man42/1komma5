import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SiteOverviewCard } from "@/components/dashboard/SiteOverviewCard";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("SiteOverviewCard", () => {
  it("renders site summary with status", () => {
    render(
      <SiteOverviewCard
        site={{
          slug: "akarp",
          name: "Åkarp",
          timezone: "Europe/Stockholm",
          fallback_purchase_price_sek_kwh: 2,
          export_compensation_sek_kwh: 0.8,
          latest_reading: {
            recorded_at: "2026-01-01T12:00:00Z",
            solar_production_w: 1500,
            consumption_w: 800,
            grid_import_w: 0,
            grid_export_w: 700,
            battery_soc_pct: 75,
            battery_power_w: 200,
          },
        }}
      />,
    );

    expect(screen.getByRole("link").getAttribute("href")).toBe("/sites/akarp");
    expect(screen.getByText("Åkarp")).toBeTruthy();
    expect(screen.getByText("Normal")).toBeTruthy();
  });
});
