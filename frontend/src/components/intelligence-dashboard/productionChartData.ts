import type { Reading, SolarForecast } from "@/lib/api";
import { isAggregated } from "@/lib/api";

const INTERVAL_MS = 15 * 60 * 1000;

export interface ProductionChartRow {
  timestamp: string;
  time: string;
  sort: number;
  actualKw: number | null;
  forecastKw: number | null;
}

function localDateKey(iso: string, timezone: string): string {
  return new Date(iso).toLocaleDateString("sv-SE", { timeZone: timezone });
}

export function formatChartClock(iso: string, timezone: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

function readingTimestamp(reading: Reading): string {
  return isAggregated(reading) ? reading.bucket_start : reading.recorded_at;
}

function roundKw(watts: number): number {
  return Math.round((watts / 1000) * 100) / 100;
}

export function buildProductionChartData({
  readings,
  forecast,
  timezone,
  now = new Date().toISOString(),
}: {
  readings: Reading[];
  forecast: SolarForecast | null;
  timezone: string;
  now?: string;
}): ProductionChartRow[] {
  const todayKey = localDateKey(now, timezone);
  const forecastPoints = (forecast?.points ?? []).filter(
    (point) => localDateKey(point.timestamp, timezone) === todayKey,
  );

  const todayReadings = readings.filter(
    (reading) => localDateKey(readingTimestamp(reading), timezone) === todayKey,
  );

  if (forecastPoints.length === 0) {
    return todayReadings
      .map((reading) => {
        const iso = readingTimestamp(reading);
        return {
          timestamp: iso,
          time: formatChartClock(iso, timezone),
          sort: new Date(iso).getTime(),
          actualKw: roundKw(reading.solar_production_w ?? 0),
          forecastKw: null,
        };
      })
      .sort((a, b) => a.sort - b.sort);
  }

  return forecastPoints
    .map((point) => {
      const start = new Date(point.timestamp).getTime();
      const end = start + INTERVAL_MS;
      const bucketReadings = todayReadings.filter((reading) => {
        const ts = new Date(readingTimestamp(reading)).getTime();
        return ts >= start && ts < end;
      });

      const actualKw =
        bucketReadings.length > 0
          ? roundKw(
              bucketReadings.reduce((sum, reading) => sum + (reading.solar_production_w ?? 0), 0) /
                bucketReadings.length,
            )
          : null;

      return {
        timestamp: point.timestamp,
        time: formatChartClock(point.timestamp, timezone),
        sort: start,
        actualKw,
        forecastKw: roundKw(point.corrected_power_w),
      };
    })
    .sort((a, b) => a.sort - b.sort);
}

export function chartYMax(rows: ProductionChartRow[]): number {
  let max = 0;
  for (const row of rows) {
    if (row.actualKw != null) max = Math.max(max, row.actualKw);
    if (row.forecastKw != null) max = Math.max(max, row.forecastKw);
  }
  if (max <= 0) return 4;
  return Math.ceil(max * 1.15 * 10) / 10;
}

export function hasForecastSeries(rows: ProductionChartRow[]): boolean {
  return rows.some((row) => row.forecastKw != null && row.forecastKw > 0);
}
