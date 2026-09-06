import type { Reading, SolarForecast } from "@/lib/api";
import {
  formatChartClock,
  inferForecastIntervalMs,
  localDateKey,
  localDayBoundsMs,
  readingTimestamp,
  roundKwh,
  roundKw,
} from "@/lib/chartTime";

export { formatChartClock, inferForecastIntervalMs } from "@/lib/chartTime";

export interface ProductionChartRow {
  timestamp: string;
  time: string;
  sort: number;
  actualKw: number | null;
  forecastKw: number | null;
}

const FINE_CHART_BUCKET_MS = 15 * 60 * 1000;

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function actualKwInBucket(startMs: number, endMs: number, readings: Reading[]): number | null {
  const bucketReadings = readings.filter((reading) => {
    const ts = new Date(readingTimestamp(reading)).getTime();
    return ts >= startMs && ts < endMs;
  });
  if (bucketReadings.length === 0) return null;
  return roundKw(average(bucketReadings.map((reading) => reading.solar_production_w ?? 0)) ?? 0);
}

function forecastKwAt(
  timestampMs: number,
  sortedForecast: SolarForecast["points"],
  forecastStepMs: number,
): number | null {
  if (sortedForecast.length === 0) return null;

  for (let i = sortedForecast.length - 1; i >= 0; i -= 1) {
    const start = new Date(sortedForecast[i].timestamp).getTime();
    const end =
      i + 1 < sortedForecast.length
        ? new Date(sortedForecast[i + 1].timestamp).getTime()
        : start + forecastStepMs;
    if (timestampMs >= start && timestampMs < end) {
      return roundKw(sortedForecast[i].corrected_power_w);
    }
  }

  return null;
}

function resolveChartBucketMs(forecastStepMs: number, bucketMinutes?: number): number {
  if (bucketMinutes != null) {
    return bucketMinutes * 60 * 1000;
  }
  if (forecastStepMs >= 60 * 60 * 1000) {
    return FINE_CHART_BUCKET_MS;
  }
  return forecastStepMs;
}

export function buildProductionChartData({
  readings,
  forecast,
  timezone,
  now = new Date().toISOString(),
  bucketMinutes,
}: {
  readings: Reading[];
  forecast: SolarForecast | null;
  timezone: string;
  now?: string;
  bucketMinutes?: number;
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

  const sortedForecast = [...forecastPoints].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );
  const forecastStepMs = inferForecastIntervalMs(sortedForecast);
  const bucketMs = resolveChartBucketMs(forecastStepMs, bucketMinutes);

  const { startMs: dayStartMs, endMs: dayEndMs } = localDayBoundsMs(now, timezone);
  const forecastEndMs =
    Math.max(...sortedForecast.map((point) => new Date(point.timestamp).getTime())) + forecastStepMs;
  const readingEndMs =
    todayReadings.length > 0
      ? Math.max(...todayReadings.map((reading) => new Date(readingTimestamp(reading)).getTime())) +
        bucketMs
      : dayStartMs;

  const gridStart = dayStartMs;
  const gridEnd = Math.max(dayEndMs, forecastEndMs, readingEndMs);

  const rows: ProductionChartRow[] = [];
  for (let bucketStart = gridStart; bucketStart < gridEnd; bucketStart += bucketMs) {
    const bucketEnd = bucketStart + bucketMs;
    const actualKw = actualKwInBucket(bucketStart, bucketEnd, todayReadings);
    const forecastKw = forecastKwAt(bucketStart, sortedForecast, forecastStepMs);

    if (actualKw == null && forecastKw == null) continue;

    const iso = new Date(bucketStart).toISOString();
    rows.push({
      timestamp: iso,
      time: formatChartClock(iso, timezone),
      sort: bucketStart,
      actualKw,
      forecastKw,
    });
  }

  return rows;
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

export function hasOverlappingSeries(rows: ProductionChartRow[]): boolean {
  return rows.some(
    (row) => row.actualKw != null && row.forecastKw != null && row.actualKw > 0 && row.forecastKw > 0,
  );
}

export function computeForecastSoFarKwh(
  forecast: SolarForecast | null,
  timezone: string,
  now: string,
): number | null {
  if (!forecast?.points?.length) return null;
  const todayKey = localDateKey(now, timezone);
  const nowMs = new Date(now).getTime();
  const todayPoints = forecast.points.filter(
    (point) =>
      localDateKey(point.timestamp, timezone) === todayKey &&
      new Date(point.timestamp).getTime() <= nowMs,
  );
  if (todayPoints.length === 0) return null;
  return roundKwh(todayPoints.reduce((sum, point) => sum + (point.expected_energy_kwh ?? 0), 0));
}

const MAX_READING_INTERVAL_MS = 5 * 60 * 1000;

function todayReadingPoints(
  readings: Reading[],
  timezone: string,
  now: string,
): Array<{ ts: number; watts: number }> {
  const todayKey = localDateKey(now, timezone);
  const nowMs = new Date(now).getTime();
  const { startMs } = localDayBoundsMs(now, timezone);

  return readings
    .map((reading) => ({
      ts: new Date(readingTimestamp(reading)).getTime(),
      watts: reading.solar_production_w ?? 0,
    }))
    .filter(
      (point) =>
        point.ts >= startMs &&
        point.ts <= nowMs &&
        localDateKey(new Date(point.ts).toISOString(), timezone) === todayKey,
    )
    .sort((a, b) => a.ts - b.ts);
}

export function computeActualTodayKwh(
  readings: Reading[],
  timezone: string,
  now: string,
): number | null {
  const points = todayReadingPoints(readings, timezone, now);
  if (points.length < 2) return null;

  const nowMs = new Date(now).getTime();
  let totalKwh = 0;

  for (let i = 0; i < points.length - 1; i += 1) {
    const durationMs = points[i + 1].ts - points[i].ts;
    if (durationMs <= 0 || durationMs > MAX_READING_INTERVAL_MS) continue;
    totalKwh += (points[i].watts * durationMs) / (3600 * 1000) / 1000;
  }

  const last = points[points.length - 1];
  const tailMs = nowMs - last.ts;
  if (tailMs > 0 && tailMs <= MAX_READING_INTERVAL_MS) {
    totalKwh += (last.watts * tailMs) / (3600 * 1000) / 1000;
  }

  return roundKwh(totalKwh);
}

export interface ProductionIntradayMetrics {
  actualTodayKwh: number | null;
  forecastSoFarKwh: number | null;
  deviationKwh: number | null;
  deviationPct: number | null;
}

export function computeProductionIntradayMetrics({
  readings,
  forecast,
  timezone,
  now,
  producedKwhToday,
}: {
  readings: Reading[];
  forecast: SolarForecast | null;
  timezone: string;
  now: string;
  producedKwhToday?: number | null;
}): ProductionIntradayMetrics {
  const actualFromReadings = computeActualTodayKwh(readings, timezone, now);
  const actualTodayKwh =
    producedKwhToday ??
    actualFromReadings ??
    (forecast?.actual_today_kwh != null ? forecast.actual_today_kwh : null);

  const forecastFromPoints = computeForecastSoFarKwh(forecast, timezone, now);
  const forecastSoFarKwh =
    forecastFromPoints ?? (forecast?.forecast_so_far_kwh != null ? forecast.forecast_so_far_kwh : null);

  const deviationKwh =
    actualTodayKwh != null && forecastSoFarKwh != null && forecastSoFarKwh > 0
      ? actualTodayKwh - forecastSoFarKwh
      : null;
  const deviationPct =
    deviationKwh != null && forecastSoFarKwh != null && forecastSoFarKwh > 0
      ? (deviationKwh / forecastSoFarKwh) * 100
      : null;

  return { actualTodayKwh, forecastSoFarKwh, deviationKwh, deviationPct };
}
