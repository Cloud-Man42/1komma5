import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SiteCard } from "./SiteCard";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("SiteCard", () => {
  it("renders site name and metrics", () => {
    render(
      <SiteCard
        site={{
          slug: "akarp",
          name: "Åkarp",
          timezone: "Europe/Stockholm",
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
    expect(screen.getByLabelText("Energiflöde visualisering")).toBeTruthy();
    expect(screen.getAllByText("1.5 kW").length).toBeGreaterThan(0);
  });
});
