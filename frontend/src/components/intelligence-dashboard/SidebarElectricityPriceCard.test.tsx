import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SidebarElectricityPriceCard } from "@/components/intelligence-dashboard/SidebarElectricityPriceCard";
import type { MarketPricesResponse } from "@/lib/api";

const prices: MarketPricesResponse = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  resolution: "1h",
  current_price_eur_kwh: 0.84,
  average_all_in_eur_kwh: 0.95,
  highest_all_in_eur_kwh: 1.87,
  lowest_all_in_eur_kwh: 0.22,
  points: [
    { timestamp: "2026-08-28T00:00:00+02:00", spot_eur_kwh: 0.22, all_in_eur_kwh: 0.22 },
    { timestamp: "2026-08-28T06:00:00+02:00", spot_eur_kwh: 0.35, all_in_eur_kwh: 0.35 },
    { timestamp: "2026-08-28T09:00:00+02:00", spot_eur_kwh: 0.84, all_in_eur_kwh: 0.84 },
    { timestamp: "2026-08-28T14:00:00+02:00", spot_eur_kwh: 0.43, all_in_eur_kwh: 0.43 },
    { timestamp: "2026-08-28T18:00:00+02:00", spot_eur_kwh: 1.87, all_in_eur_kwh: 1.87 },
  ],
};

describe("SidebarElectricityPriceCard", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders empty state without prices", () => {
    render(<SidebarElectricityPriceCard prices={null} />);
    expect(screen.getByText("ELPRIS IDAG")).toBeTruthy();
    expect(screen.getByText(/Inga elpriser tillgängliga/i)).toBeTruthy();
  });

  it("renders stats and trend for today prices", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-28T09:15:00+02:00"));
    render(<SidebarElectricityPriceCard prices={prices} />);
    expect(screen.getByText("22 öre")).toBeTruthy();
    expect(screen.getByText("187 öre")).toBeTruthy();
    expect(screen.getByText("Lägst")).toBeTruthy();
    expect(screen.getByText("Nu")).toBeTruthy();
    expect(screen.getByText("Högst")).toBeTruthy();
    expect(screen.getByTestId("sidebar-elprice-trend")).toBeTruthy();
  });
});
