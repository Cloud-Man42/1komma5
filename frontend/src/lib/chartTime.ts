import type { AggregatedReading, Reading } from "@/lib/api";
import { isAggregated } from "@/lib/api";

const DEFAULT_INTERVAL_MS = 15 * 60 * 1000;

/** Calendar date in site timezone (`YYYY-MM-DD` via sv-SE locale). */
export function localDateKey(iso: string, timezone: string): string {
  return new Date(iso).toLocaleDateString("sv-SE", { timeZone: timezone });
}

/** Hour:minute label for chart axes in site timezone. */
export function formatChartClock(iso: string, timezone: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

export function readingTimestamp(reading: Reading | AggregatedReading): string {
  return isAggregated(reading) ? reading.bucket_start : reading.recorded_at;
}

export function roundKw(watts: number): number {
  return Math.round((watts / 1000) * 100) / 100;
}

export function roundKwh(value: number): number {
  return Math.round(value * 10) / 10;
}

/** Start/end of the site-local calendar day containing `iso` (UTC epoch ms). */
export function localDayBoundsMs(iso: string, timezone: string): { startMs: number; endMs: number } {
  const dayKey = localDateKey(iso, timezone);
  const [year, month, day] = dayKey.split("-").map(Number);
  const guess = Date.UTC(year, month - 1, day, 12, 0, 0);

  let startMs = guess;
  for (let offsetMs = -14 * 60 * 60 * 1000; offsetMs <= 14 * 60 * 60 * 1000; offsetMs += 60 * 1000) {
    const probeMs = guess + offsetMs;
    const probeIso = new Date(probeMs).toISOString();
    if (localDateKey(probeIso, timezone) === dayKey && formatChartClock(probeIso, timezone) === "00:00") {
      startMs = probeMs;
      break;
    }
  }

  return { startMs, endMs: startMs + 24 * 60 * 60 * 1000 };
}

/** Infer forecast step from consecutive point timestamps (15-min vs hourly). */
export function inferForecastIntervalMs(points: { timestamp: string }[]): number {
  if (points.length < 2) return DEFAULT_INTERVAL_MS;

  const deltas: number[] = [];
  for (let i = 1; i < Math.min(points.length, 8); i += 1) {
    const delta =
      new Date(points[i].timestamp).getTime() - new Date(points[i - 1].timestamp).getTime();
    if (delta > 0) deltas.push(delta);
  }
  if (deltas.length === 0) return DEFAULT_INTERVAL_MS;

  deltas.sort((a, b) => a - b);
  return deltas[Math.floor(deltas.length / 2)] ?? DEFAULT_INTERVAL_MS;
}

export function sumEnergyKwh(
  points: { corrected_power_w: number; expected_energy_kwh?: number }[],
  hoursPerPoint: number,
): number {
  if (
    points.length > 0 &&
    points.every((p) => p.expected_energy_kwh != null && !Number.isNaN(p.expected_energy_kwh))
  ) {
    return points.reduce((sum, p) => sum + (p.expected_energy_kwh ?? 0), 0);
  }
  return points.reduce((sum, p) => sum + (p.corrected_power_w * hoursPerPoint) / 1000, 0);
}
