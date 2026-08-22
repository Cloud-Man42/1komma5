import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PriceChart } from "./PriceChart";

describe("PriceChart", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn((query: string) => ({
        matches: query.includes("640px"),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    );
    vi.stubGlobal(
      "ResizeObserver",
      vi.fn(() => ({
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders price summary and chart title", () => {
    render(
      <PriceChart
        prices={{
          slug: "akarp",
          timezone: "Europe/Stockholm",
          resolution: "1h",
          current_price_eur_kwh: 0.22,
          average_all_in_eur_kwh: 0.2,
          highest_all_in_eur_kwh: 0.28,
          lowest_all_in_eur_kwh: 0.14,
          points: [
            {
              timestamp: "2026-08-13T18:00:00Z",
              spot_eur_kwh: 0.12,
              all_in_eur_kwh: 0.22,
            },
            {
              timestamp: "2026-08-13T19:00:00Z",
              spot_eur_kwh: 0.1,
              all_in_eur_kwh: 0.18,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Elpris 24 timmar")).toBeTruthy();
    expect(screen.getByText("22.0 öre/kWh")).toBeTruthy();
    expect(screen.getByText("14.0 öre/kWh")).toBeTruthy();
    expect(screen.getByText("28.0 öre/kWh")).toBeTruthy();
  });

  it("shows empty state when no points are available", () => {
    render(
      <PriceChart
        prices={{
          slug: "akarp",
          timezone: "Europe/Stockholm",
          resolution: "1h",
          current_price_eur_kwh: null,
          average_all_in_eur_kwh: null,
          highest_all_in_eur_kwh: null,
          lowest_all_in_eur_kwh: null,
          points: [],
        }}
      />,
    );

    expect(screen.getByText("Inga elpriser tillgängliga från Heartbeat.")).toBeTruthy();
  });
});
