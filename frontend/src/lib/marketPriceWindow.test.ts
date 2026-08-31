import { describe, expect, it, vi } from "vitest";
import { intradayMarketPriceWindow } from "./marketPriceWindow";

describe("marketPriceWindow", () => {
  it("covers the full local calendar day for intraday queries", () => {
    const now = new Date("2026-08-29T04:19:00.000Z"); // 06:19 Stockholm
    const { from, to } = intradayMarketPriceWindow(now, "Europe/Stockholm");
    expect(to.getTime() - now.getTime()).toBeGreaterThan(12 * 60 * 60 * 1000);
    expect(now.getTime() - from.getTime()).toBeGreaterThan(5 * 60 * 60 * 1000);
    expect(to.getTime() - from.getTime()).toBeGreaterThan(22 * 60 * 60 * 1000);
  });
});
