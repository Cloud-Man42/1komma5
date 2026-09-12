/** Aggregate per-site reading history for multi-site overview charts. */

import type { AggregatedReading, HistoryResponse } from "@/lib/api";
import { fetchSiteHistory } from "@/lib/api";
import { readingTimestamp } from "@/lib/chartTime";

export interface MultiSiteHistoryPoint {
  label: string;
  sortKey: number;
  solarW: number;
  gridImportW: number;
  gridExportW: number;
  batteryChargeW: number;
  batteryDischargeW: number;
  /** Per-site solar production (W) when multiple sites are aggregated. */
  siteSolarW?: Record<string, number>;
}

export function historySiteSolarKey(slug: string): string {
  return `siteSolar_${slug.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
}

function bucketKey(reading: AggregatedReading): string {
  return readingTimestamp(reading);
}

export function aggregateSiteHistories(
  histories: HistoryResponse[],
  timezone = "Europe/Stockholm",
): MultiSiteHistoryPoint[] {
  const merged = new Map<
    string,
    {
      sortKey: number;
      solarW: number;
      gridImportW: number;
      gridExportW: number;
      batteryChargeW: number;
      batteryDischargeW: number;
      siteSolarW: Record<string, number>;
    }
  >();

  for (const history of histories) {
    const slug = history.slug;
    for (const reading of history.readings) {
      const key = bucketKey(reading as AggregatedReading);
      const date = new Date(key);
      const row =
        merged.get(key) ?? {
          sortKey: date.getTime(),
          solarW: 0,
          gridImportW: 0,
          gridExportW: 0,
          batteryChargeW: 0,
          batteryDischargeW: 0,
          siteSolarW: {},
        };
      const solar = reading.solar_production_w ?? 0;
      row.solarW += solar;
      row.siteSolarW[slug] = (row.siteSolarW[slug] ?? 0) + solar;
      row.gridImportW += reading.grid_import_w ?? 0;
      row.gridExportW += reading.grid_export_w ?? 0;
      const battery = reading.battery_power_w ?? 0;
      if (battery > 0) row.batteryChargeW += battery;
      else row.batteryDischargeW += Math.abs(battery);
      merged.set(key, row);
    }
  }

  const multiSite = histories.length > 1;

  return Array.from(merged.values())
    .sort((a, b) => a.sortKey - b.sortKey)
    .map((row) => ({
      label: new Date(row.sortKey).toLocaleTimeString("sv-SE", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: timezone,
      }),
      sortKey: row.sortKey,
      solarW: row.solarW,
      gridImportW: row.gridImportW,
      gridExportW: row.gridExportW,
      batteryChargeW: row.batteryChargeW,
      batteryDischargeW: row.batteryDischargeW,
      ...(multiSite ? { siteSolarW: row.siteSolarW } : {}),
    }));
}

export async function fetchMultiSiteHistory(
  slugs: string[],
  bucket = 15,
  hours = 24,
): Promise<MultiSiteHistoryPoint[]> {
  if (slugs.length === 0) return [];
  const histories = await Promise.all(slugs.map((slug) => fetchSiteHistory(slug, bucket, hours)));
  return aggregateSiteHistories(histories);
}

export function latestHistoryPower(point: MultiSiteHistoryPoint | null): {
  solarW: number;
  gridImportW: number;
  gridExportW: number;
  batteryChargeW: number;
  batteryDischargeW: number;
} {
  if (!point) {
    return { solarW: 0, gridImportW: 0, gridExportW: 0, batteryChargeW: 0, batteryDischargeW: 0 };
  }
  return {
    solarW: point.solarW,
    gridImportW: point.gridImportW,
    gridExportW: point.gridExportW,
    batteryChargeW: point.batteryChargeW,
    batteryDischargeW: point.batteryDischargeW,
  };
}
