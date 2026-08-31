import type { MarketPricePoint, MarketPricesResponse } from "@/lib/api";
import { toOrePerKwh } from "@/lib/prices";

export interface TodayPricePoint {
  timestamp: string;
  hour: number;
  ore: number;
  isCurrent: boolean;
}

export interface PriceTrendMessage {
  direction: "falling" | "rising" | "stable";
  deltaOre: number;
  atHourLabel: string;
  text: string;
}

export interface SidebarElectricityPriceModel {
  timezone: string;
  points: TodayPricePoint[];
  currentOre: number;
  lowestOre: number;
  highestOre: number;
  currentIndex: number;
  yMax: number;
  yMin: number;
  trend: PriceTrendMessage | null;
  segmentCount: number;
}

export function pointOre(point: MarketPricePoint): number {
  return Math.round(toOrePerKwh(point.all_in_eur_kwh ?? point.spot_eur_kwh));
}

export function localDayKey(iso: string, timezone: string): string {
  return new Date(iso).toLocaleDateString("sv-SE", { timeZone: timezone });
}

export function hourFraction(iso: string, timezone: string): number {
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: timezone,
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  }).formatToParts(new Date(iso));
  const hour = Number(parts.find((p) => p.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value ?? 0);
  return hour + minute / 60;
}

export function formatHourLabel(iso: string, timezone: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

export function lineColorForOre(ore: number, min: number, max: number): string {
  if (max <= min) return "#4ade80";
  const t = (ore - min) / (max - min);
  if (t <= 0.35) return "#4ade80";
  if (t <= 0.6) return "#fbbf24";
  if (t <= 0.8) return "#fb923c";
  return "#f87171";
}

export function buildPriceTrend(
  points: TodayPricePoint[],
  currentIndex: number,
  timezone: string,
): PriceTrendMessage | null {
  if (currentIndex < 0 || points.length < 2) return null;
  const current = points[currentIndex];
  if (!current) return null;

  let bestCheaper: TodayPricePoint | null = null;
  let bestCostlier: TodayPricePoint | null = null;
  for (const point of points.slice(currentIndex + 1)) {
    if (point.ore < current.ore && (!bestCheaper || point.ore < bestCheaper.ore)) {
      bestCheaper = point;
    }
    if (point.ore > current.ore && (!bestCostlier || point.ore > bestCostlier.ore)) {
      bestCostlier = point;
    }
  }

  if (bestCheaper) {
    const deltaOre = current.ore - bestCheaper.ore;
    const atHourLabel = formatHourLabel(bestCheaper.timestamp, timezone);
    return {
      direction: "falling",
      deltaOre,
      atHourLabel,
      text: `Pris sjunker · ${deltaOre} öre billigare kl. ${atHourLabel}`,
    };
  }

  if (bestCostlier) {
    const deltaOre = bestCostlier.ore - current.ore;
    const atHourLabel = formatHourLabel(bestCostlier.timestamp, timezone);
    return {
      direction: "rising",
      deltaOre,
      atHourLabel,
      text: `Pris stiger · ${deltaOre} öre dyrare kl. ${atHourLabel}`,
    };
  }

  return {
    direction: "stable",
    deltaOre: 0,
    atHourLabel: "",
    text: "Priset är stabilt resten av dagen",
  };
}

export function buildSidebarElectricityPriceModel(
  prices: MarketPricesResponse | null,
  now = new Date(),
): SidebarElectricityPriceModel | null {
  if (!prices?.points.length) return null;

  const timezone = prices.timezone;
  const todayKey = now.toLocaleDateString("sv-SE", { timeZone: timezone });
  const todayPoints = prices.points.filter((p) => localDayKey(p.timestamp, timezone) === todayKey);
  if (todayPoints.length < 2) return null;

  const nowMs = now.getTime();
  const mapped: TodayPricePoint[] = todayPoints.map((point) => ({
    timestamp: point.timestamp,
    hour: hourFraction(point.timestamp, timezone),
    ore: pointOre(point),
    isCurrent: Math.abs(new Date(point.timestamp).getTime() - nowMs) < 45 * 60 * 1000,
  }));

  mapped.sort((a, b) => a.hour - b.hour);
  const filled = fillHourlyCurve(mapped);

  const ores = filled.map((p) => p.ore);
  const lowestOre = Math.min(...ores);
  const highestOre = Math.max(...ores);
  let currentIndex = filled.findIndex((p) => p.isCurrent);
  if (currentIndex < 0) {
    currentIndex = filled.reduce(
      (best, point, idx) =>
        Math.abs(new Date(point.timestamp).getTime() - nowMs) <
        Math.abs(new Date(filled[best].timestamp).getTime() - nowMs)
          ? idx
          : best,
      0,
    );
  }
  const currentOre = filled[currentIndex]?.ore ?? lowestOre;
  const padding = Math.max(4, Math.round((highestOre - lowestOre) * 0.12));
  const yMin = Math.max(0, lowestOre - padding);
  const yMax = Math.max(highestOre + padding, lowestOre + 8);

  return {
    timezone,
    points: filled,
    currentOre,
    lowestOre,
    highestOre,
    currentIndex,
    yMin,
    yMax,
    trend: buildPriceTrend(filled, currentIndex, timezone),
    segmentCount: Math.max(0, filled.length - 1),
  };
}

/** Ensure 24 hourly slots (0–23) so the chart spans the full day. */
export function fillHourlyCurve(points: TodayPricePoint[]): TodayPricePoint[] {
  if (points.length < 2) return points;

  const byHour = new Map<number, TodayPricePoint>();
  for (const point of points) {
    const hour = Math.min(23, Math.max(0, Math.round(point.hour)));
    byHour.set(hour, { ...point, hour });
  }

  const filled: TodayPricePoint[] = [];
  let last = points[0];
  for (let hour = 0; hour < 24; hour += 1) {
    const hit = byHour.get(hour);
    if (hit) {
      last = hit;
      filled.push(hit);
      continue;
    }
    filled.push({
      ...last,
      hour,
      isCurrent: false,
    });
  }
  return filled;
}

export type ChartPriceRow = TodayPricePoint & Record<string, number | null | string | boolean>;

export function enrichPointsWithSegments(points: TodayPricePoint[]): ChartPriceRow[] {
  const segmentCount = Math.max(0, points.length - 1);
  return points.map((point, idx) => {
    const row: ChartPriceRow = { ...point };
    for (let seg = 0; seg < segmentCount; seg += 1) {
      row[`seg${seg}`] = idx === seg || idx === seg + 1 ? point.ore : null;
    }
    return row;
  });
}
