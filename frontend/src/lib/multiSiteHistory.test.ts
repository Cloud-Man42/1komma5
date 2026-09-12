import { describe, expect, it } from "vitest";
import type { HistoryResponse } from "@/lib/api";
import { aggregateSiteHistories } from "@/lib/multiSiteHistory";

describe("aggregateSiteHistories", () => {
  it("sums power across sites per bucket", () => {
    const akarp: HistoryResponse = {
      slug: "akarp",
      bucket_minutes: 15,
      readings: [
        {
          bucket_start: "2026-09-12T10:00:00Z",
          solar_production_w: 4000,
          consumption_w: 3000,
          grid_import_w: 0,
          grid_export_w: 1000,
          battery_soc_pct: 80,
          battery_power_w: 500,
        },
      ],
    };
    const denmark: HistoryResponse = {
      slug: "summer-house-denmark",
      bucket_minutes: 15,
      readings: [
        {
          bucket_start: "2026-09-12T10:00:00Z",
          solar_production_w: 1600,
          consumption_w: 2100,
          grid_import_w: 500,
          grid_export_w: 0,
          battery_soc_pct: 65,
          battery_power_w: -200,
        },
      ],
    };

    const points = aggregateSiteHistories([akarp, denmark], "UTC");
    expect(points).toHaveLength(1);
    expect(points[0].solarW).toBe(5600);
    expect(points[0].gridImportW).toBe(500);
    expect(points[0].gridExportW).toBe(1000);
    expect(points[0].batteryChargeW).toBe(500);
    expect(points[0].batteryDischargeW).toBe(200);
    expect(points[0].siteSolarW).toEqual({ akarp: 4000, "summer-house-denmark": 1600 });
  });

  it("omits per-site solar map for a single site", () => {
    const akarp: HistoryResponse = {
      slug: "akarp",
      bucket_minutes: 15,
      readings: [
        {
          bucket_start: "2026-09-12T10:00:00Z",
          solar_production_w: 4000,
          consumption_w: 3000,
          grid_import_w: 0,
          grid_export_w: 1000,
          battery_soc_pct: 80,
          battery_power_w: 500,
        },
      ],
    };
    const points = aggregateSiteHistories([akarp], "UTC");
    expect(points[0].siteSolarW).toBeUndefined();
  });

  it("returns empty array when no histories", () => {
    expect(aggregateSiteHistories([])).toEqual([]);
  });
});
