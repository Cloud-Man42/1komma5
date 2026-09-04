import { describe, expect, it } from "vitest";
import type { DisplayOverview } from "@/lib/displayOverview";
import {
  derivePiConnectionState,
  formatLastUpdated,
  loadPiLastKnownGood,
  savePiLastKnownGood,
} from "@/lib/piDashboardStorage";

const sampleOverview = (overrides: Partial<DisplayOverview> = {}): DisplayOverview =>
  ({
    generated_at: "2026-09-03T12:30:00.000Z",
    site: { slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
    freshness: { updated_at: null, data_age_seconds: 10, stale: false, connection_state: "LIVE" },
    live: {},
    sparklines: {},
    weather: { available: true },
    price: { available: true },
    flow: { available: true, nodes: [] },
    vehicle: { available: false },
    charger: { available: false },
    spa: { available: false },
    economy: { available: true, daily: [] },
    highlights: { available: true, items: [] },
    system_status: { available: true, label_sv: "OK" },
    ...overrides,
  }) as DisplayOverview;

describe("piDashboardStorage", () => {
  it("persists and loads last-known-good", () => {
    const overview = sampleOverview();
    savePiLastKnownGood("akarp", overview);
    expect(loadPiLastKnownGood("akarp")?.site.slug).toBe("akarp");
  });

  it("derives LIVE when fresh and connected", () => {
    expect(derivePiConnectionState(sampleOverview(), false)).toBe("CONNECTED");
  });

  it("derives RECONNECTING when fetch fails but cached data exists", () => {
    expect(
      derivePiConnectionState(
        sampleOverview({ freshness: { updated_at: null, data_age_seconds: 300, stale: true, connection_state: "STALE" } }),
        true,
      ),
    ).toBe("RECONNECTING");
  });

  it("derives OFFLINE when fetch fails and no cache", () => {
    expect(derivePiConnectionState(null, true)).toBe("OFFLINE");
  });

  it("formats last updated timestamp", () => {
    expect(formatLastUpdated(sampleOverview())).toMatch(/\d{2}:\d{2}:\d{2}/);
  });
});
