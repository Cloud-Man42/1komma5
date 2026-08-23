import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ALL_IN_SERIES_COLOR,
  PRICE_TIER_COLORS,
  PriceChart,
  SPOT_SERIES_COLOR,
  TOOLTIP_BACKGROUND,
  priceColor,
} from "./PriceChart";

function relativeLuminance(hex: string) {
  const channels = [1, 3, 5].map((offset) => {
    const value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(foreground: string, background: string) {
  const a = relativeLuminance(foreground);
  const b = relativeLuminance(background);
  const [lighter, darker] = a > b ? [a, b] : [b, a];
  return (lighter + 0.05) / (darker + 0.05);
}

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
    // Must be a constructible value, not an arrow function: recharts'
    // ResponsiveContainer calls `new ResizeObserver(...)`, and an arrow
    // function has no [[Construct]] slot, so `new` on it throws
    // "is not a constructor". A class literal is used rather than
    // `vi.fn(function () { ... })` because nothing in this file asserts
    // against the observer's calls, so no spy capability is needed.
    vi.stubGlobal(
      "ResizeObserver",
      class ResizeObserverStub {
        observe(): void {}
        unobserve(): void {}
        disconnect(): void {}
      },
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

  it("uses an All-in series colour that is readable on the tooltip background", () => {
    expect(ALL_IN_SERIES_COLOR.toLowerCase()).not.toBe("#000000");
    expect(contrastRatio(ALL_IN_SERIES_COLOR, TOOLTIP_BACKGROUND)).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps the Spot series readable on the tooltip background", () => {
    expect(contrastRatio(SPOT_SERIES_COLOR, TOOLTIP_BACKGROUND)).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps every price tier colour readable on the dark chart surface", () => {
    for (const color of Object.values(PRICE_TIER_COLORS)) {
      expect(contrastRatio(color, TOOLTIP_BACKGROUND)).toBeGreaterThanOrEqual(3);
    }
  });

  it("maps price levels to cheap, normal and expensive tiers", () => {
    expect(priceColor(50, 100)).toBe(PRICE_TIER_COLORS.cheap);
    expect(priceColor(100, 100)).toBe(PRICE_TIER_COLORS.normal);
    expect(priceColor(200, 100)).toBe(PRICE_TIER_COLORS.expensive);
  });
});
