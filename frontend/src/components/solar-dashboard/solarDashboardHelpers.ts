import type {

  Reading,

  SolarForecast,

  SolarPerformance,

  SolarSiteConfig,

  SolarWeather,

} from "@/lib/api";

import { buildProductionChartData, type ProductionChartRow } from "@/components/intelligence-dashboard/productionChartData";
import { forecastConfidencePct } from "@/components/intelligence-dashboard/confidenceLabels";
import {
  formatChartClock,
  inferForecastIntervalMs,
  localDateKey,
  readingTimestamp,
  roundKwh,
  roundKw,
  sumEnergyKwh,
} from "@/lib/chartTime";



export type SolarChartResolution = 15 | 60;



const INTERVAL_MS = 15 * 60 * 1000;



export interface SolarKpiMetrics {

  forecastTodayKwh: number | null;

  producedSoFarKwh: number | null;

  forecastAtNowKwh: number | null;

  confidencePct: number | null;

  intervalLabel: string;

  nextHourForecastKw: number | null;

}



export interface SolarProductionChartPoint {

  label: string;

  sortKey: number;

  forecastKw: number | null;

  actualKw: number | null;

  yesterdayKw: number | null;

  batterySocPct: number | null;

}



export interface SolarDayStats {

  sunrise: string | null;

  sunset: string | null;

  maxForecastKw: number | null;

  maxActualKw: number | null;

  avgForecastKw: number | null;

  avgActualKw: number | null;

  specificYieldWhPerWp: number | null;

}



export interface SolarPeriodSlice {

  id: string;

  label: string;

  kwh: number;

  pct: number;

  color: string;

}



export interface SolarMultiDayRow {

  dateKey: string;

  label: string;

  expectedKwh: number | null;

  pointCount: number;

  isPartial: boolean;

}



export interface SolarComparisonBar {

  label: string;

  dateKey: string;

  actualKwh: number | null;

  expectedKwh: number | null;

  ratioPct: number | null;

}



export interface SolarWeatherFactors {

  maxGhi: number | null;

  avgGhi: number | null;

  maxTempC: number | null;

  avgTempC: number | null;

  maxWindMs: number | null;

  avgWindMs: number | null;

  avgCloudPct: number | null;

  totalPrecipMm: number | null;

}



export interface SolarKpiSparklines {

  forecast: number[];

  actual: number[];

  confidence: number[];

}



export function nextDateKey(dateKey: string): string {

  const [y, m, d] = dateKey.split("-").map(Number);

  const dt = new Date(Date.UTC(y, m - 1, d + 1));

  return `${dt.getUTCFullYear()}-${String(dt.getUTCMonth() + 1).padStart(2, "0")}-${String(dt.getUTCDate()).padStart(2, "0")}`;

}



export function tomorrowDateKey(now: string, timezone: string): string {

  return nextDateKey(localDateKey(now, timezone));

}



export function isForecastStale(
  generatedAt: string | null | undefined,
  maxAgeHours = 12,
  now: string | Date = new Date(),
): boolean {

  if (!generatedAt) return true;

  const referenceMs = typeof now === "string" ? new Date(now).getTime() : now.getTime();

  return referenceMs - new Date(generatedAt).getTime() > maxAgeHours * 3_600_000;

}



function avg(values: number[]): number | null {

  if (values.length === 0) return null;

  return values.reduce((sum, v) => sum + v, 0) / values.length;

}



export function formatSolarKwh(value: number | null | undefined, digits = 1): string {

  if (value == null || Number.isNaN(value)) return "—";

  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: digits, minimumFractionDigits: digits })} kWh`;

}



export function formatSolarKw(value: number | null | undefined): string {

  if (value == null || Number.isNaN(value)) return "—";

  const abs = Math.abs(value);

  if (abs >= 1000) return `${(value / 1000).toFixed(2)} kW`;

  return `${Math.round(value)} W`;

}



export function todayDateLabel(timezone = "Europe/Stockholm"): string {

  const now = new Date();

  const date = now.toLocaleDateString("sv-SE", {

    day: "numeric",

    month: "short",

    year: "numeric",

    timeZone: timezone,

  });

  return `${date} Idag`;

}



export function weatherAttribution(provider: string | undefined | null): string {

  const p = (provider ?? "").toLowerCase();

  if (p.includes("dmi")) return "Väderdata: DMI";

  if (p.includes("smhi")) return "Väderdata: SMHI";

  if (!provider) return "Väderdata: —";

  return `Väderdata: ${provider}`;

}



export function buildKpiMetrics(

  forecast: SolarForecast | null,

  now = new Date(),

): SolarKpiMetrics {

  const intervalLabel =

    forecast != null

      ? `${formatSolarKwh(forecast.lower_today_kwh)} – ${formatSolarKwh(forecast.upper_today_kwh)}`

      : "—";



  let nextHourForecastKw: number | null = null;

  if (forecast?.points.length) {

    const endMs = now.getTime() + 60 * 60 * 1000;

    const startMs = now.getTime();

    const windowPoints = forecast.points.filter((p) => {

      const ts = new Date(p.timestamp).getTime();

      return ts >= startMs && ts < endMs;

    });

    const powers = windowPoints.map((p) => p.corrected_power_w);

    nextHourForecastKw = powers.length > 0 ? roundKw(avg(powers) ?? 0) : null;

  }



  return {

    forecastTodayKwh: forecast?.expected_today_kwh ?? null,

    producedSoFarKwh: forecast?.actual_today_kwh ?? null,

    forecastAtNowKwh: forecast?.forecast_so_far_kwh ?? null,

    confidencePct: forecastConfidencePct(forecast),

    intervalLabel,

    nextHourForecastKw,

  };

}



function aggregateChartRows(

  rows: ProductionChartRow[],

  resolution: SolarChartResolution,

  timezone: string,

): ProductionChartRow[] {

  if (resolution === 15) return rows;

  const bucketMs = resolution * 60 * 1000;

  const buckets = new Map<number, { forecast: number[]; actual: number[]; sort: number; timestamp: string }>();



  for (const row of rows) {

    const bucketStart = Math.floor(row.sort / bucketMs) * bucketMs;

    const entry = buckets.get(bucketStart) ?? {

      forecast: [],

      actual: [],

      sort: bucketStart,

      timestamp: new Date(bucketStart).toISOString(),

    };

    if (row.forecastKw != null) entry.forecast.push(row.forecastKw);

    if (row.actualKw != null) entry.actual.push(row.actualKw);

    buckets.set(bucketStart, entry);

  }



  return [...buckets.values()]

    .map((entry) => ({

      timestamp: entry.timestamp,

      time: formatChartClock(entry.timestamp, timezone),

      sort: entry.sort,

      actualKw: entry.actual.length > 0 ? Math.round((avg(entry.actual) ?? 0) * 100) / 100 : null,

      forecastKw: entry.forecast.length > 0 ? Math.round((avg(entry.forecast) ?? 0) * 100) / 100 : null,

    }))

    .sort((a, b) => a.sort - b.sort);

}



function yesterdayReadingsBySlot(

  readings: Reading[],

  timezone: string,

  now: string,

): Map<number, number> {

  const todayKey = localDateKey(now, timezone);

  const yesterdayDate = new Date(now);

  yesterdayDate.setDate(yesterdayDate.getDate() - 1);

  const yesterdayKey = yesterdayDate.toLocaleDateString("sv-SE", { timeZone: timezone });



  const map = new Map<number, number>();

  for (const reading of readings) {

    const iso = readingTimestamp(reading);

    if (localDateKey(iso, timezone) !== yesterdayKey) continue;

    void todayKey;

    const timeOfDay = new Date(iso).toLocaleTimeString("sv-SE", {

      hour: "2-digit",

      minute: "2-digit",

      timeZone: timezone,

    });

    const [h, m] = timeOfDay.split(":").map(Number);

    const key = h * 60 + m;

    map.set(key, roundKw(reading.solar_production_w ?? 0));

  }

  return map;

}



function scaledYesterdayFromPerformance(

  forecast: SolarForecast | null,

  performance: SolarPerformance | null,

  timezone: string,

  now: string,

): Map<number, number> {

  const map = new Map<number, number>();

  if (!forecast?.points.length || !performance?.days.length) return map;



  const yesterdayDate = new Date(now);

  yesterdayDate.setDate(yesterdayDate.getDate() - 1);

  const yesterdayKey = yesterdayDate.toLocaleDateString("sv-SE", { timeZone: timezone });

  const perfDay = performance.days.find((d) => d.date === yesterdayKey);

  if (perfDay?.expected_kwh == null || perfDay.expected_kwh <= 0) return map;



  const todayKey = localDateKey(now, timezone);

  const todayPoints = forecast.points.filter(

    (p) => localDateKey(p.timestamp, timezone) === todayKey,

  );

  if (todayPoints.length === 0) return map;



  const hoursPerPoint = inferForecastIntervalMs(todayPoints) / 3_600_000;

  const templateEnergy = sumEnergyKwh(todayPoints, hoursPerPoint);

  if (templateEnergy <= 0) return map;



  const scale = perfDay.expected_kwh / templateEnergy;

  for (const point of todayPoints) {

    const timeOfDay = formatChartClock(point.timestamp, timezone);

    const [h, m] = timeOfDay.split(":").map(Number);

    map.set(h * 60 + m, roundKw(point.corrected_power_w * scale));

  }

  return map;

}



function batterySocForTimestamp(

  readings: Reading[],

  timestamp: string,

  timezone: string,

  intervalMs = INTERVAL_MS,

): number | null {

  const targetMs = new Date(timestamp).getTime();

  const start = targetMs;

  const end = start + intervalMs;

  const bucket = readings.filter((r) => {

    const ts = new Date(readingTimestamp(r)).getTime();

    return ts >= start && ts < end;

  });

  const values = bucket.map((r) => r.battery_soc_pct).filter((v): v is number => v != null);

  if (values.length === 0) return null;

  return Math.round(avg(values) ?? 0);

}



export function buildProductionChartSeries({

  readings,

  forecast,

  performance,

  timezone,

  resolution = 15,

  now = new Date().toISOString(),

}: {

  readings: Reading[];

  forecast: SolarForecast | null;

  performance: SolarPerformance | null;

  timezone: string;

  resolution?: SolarChartResolution;

  now?: string;

}): SolarProductionChartPoint[] {

  const baseRows = buildProductionChartData({ readings, forecast, timezone, now });

  const rows = aggregateChartRows(baseRows, resolution, timezone);

  const todayKey = localDateKey(now, timezone);

  const todayForecast = (forecast?.points ?? []).filter(

    (p) => localDateKey(p.timestamp, timezone) === todayKey,

  );

  const chartIntervalMs = inferForecastIntervalMs(todayForecast);



  const yesterdayActual = yesterdayReadingsBySlot(readings, timezone, now);

  const yesterdayScaled =

    yesterdayActual.size > 0

      ? yesterdayActual

      : scaledYesterdayFromPerformance(forecast, performance, timezone, now);



  const hasBattery = readings.some((r) => r.battery_soc_pct != null);



  return rows.map((row) => {

    const [h, m] = row.time.split(":").map(Number);

    const slotKey = h * 60 + m;

    return {

      label: formatChartClock(row.timestamp, timezone),

      sortKey: row.sort,

      forecastKw: row.forecastKw,

      actualKw: row.actualKw,

      yesterdayKw: yesterdayScaled.get(slotKey) ?? null,

      batterySocPct: hasBattery ? batterySocForTimestamp(readings, row.timestamp, timezone, chartIntervalMs) : null,

    };

  });

}



export function buildDayStats({

  forecast,

  readings,

  weather,

  config,

  timezone,

  now = new Date().toISOString(),

}: {

  forecast: SolarForecast | null;

  readings: Reading[];

  weather: SolarWeather | null;

  config: SolarSiteConfig | null;

  timezone: string;

  now?: string;

}): SolarDayStats {

  const todayKey = localDateKey(now, timezone);

  const todayPoints = (forecast?.points ?? []).filter(

    (p) => localDateKey(p.timestamp, timezone) === todayKey,

  );

  const todayReadings = readings.filter(

    (r) => localDateKey(readingTimestamp(r), timezone) === todayKey,

  );



  const forecastPowers = todayPoints.map((p) => p.corrected_power_w);

  const actualPowers = todayReadings.map((r) => r.solar_production_w ?? 0);



  const formatSun = (iso: string | null | undefined) => {

    if (!iso) return null;

    return new Date(iso).toLocaleTimeString("sv-SE", {

      hour: "2-digit",

      minute: "2-digit",

      timeZone: timezone,

    });

  };



  const producedKwh = forecast?.actual_today_kwh ?? 0;

  const peakKw = config?.installed_peak_power_kw;

  let specificYield: number | null = null;

  if (peakKw != null && peakKw > 0 && producedKwh > 0) {

    specificYield = Math.round((producedKwh * 1000) / peakKw);

  }



  return {

    sunrise: formatSun(weather?.sunrise),

    sunset: formatSun(weather?.sunset),

    maxForecastKw: forecastPowers.length ? roundKw(Math.max(...forecastPowers)) : null,

    maxActualKw: actualPowers.length ? roundKw(Math.max(...actualPowers)) : null,

    avgForecastKw: forecastPowers.length ? roundKw(avg(forecastPowers) ?? 0) : null,

    avgActualKw: actualPowers.length ? roundKw(avg(actualPowers) ?? 0) : null,

    specificYieldWhPerWp: specificYield,

  };

}



const PERIOD_DEFS: { id: string; label: string; startH: number; endH: number; color: string }[] = [

  { id: "morning", label: "Morgon", startH: 6, endH: 10, color: "#fbbf24" },

  { id: "midday", label: "Middag", startH: 10, endH: 14, color: "#fb923c" },

  { id: "afternoon", label: "Eftermiddag", startH: 14, endH: 18, color: "#f97316" },

  { id: "evening", label: "Kväll", startH: 18, endH: 22, color: "#ea580c" },

];



export function buildPeriodDistribution(

  forecast: SolarForecast | null,

  timezone: string,

  now = new Date().toISOString(),

): SolarPeriodSlice[] {

  const todayKey = localDateKey(now, timezone);

  const todayPoints = (forecast?.points ?? []).filter(

    (p) => localDateKey(p.timestamp, timezone) === todayKey,

  );

  const hoursPerPoint = inferForecastIntervalMs(todayPoints) / 3_600_000;



  const buckets = PERIOD_DEFS.map((def) => ({ ...def, kwh: 0 }));

  for (const point of todayPoints) {

    const hour = Number(

      new Date(point.timestamp).toLocaleTimeString("sv-SE", {

        hour: "2-digit",

        hour12: false,

        timeZone: timezone,

      }),

    );

    const bucket = buckets.find((b) => hour >= b.startH && hour < b.endH);

    if (bucket) {

      bucket.kwh +=

        point.expected_energy_kwh ?? (point.corrected_power_w * hoursPerPoint) / 1000;

    }

  }



  const total = buckets.reduce((sum, b) => sum + b.kwh, 0) || 1;

  return buckets.map((b) => ({

    id: b.id,

    label: b.label,

    kwh: roundKwh(b.kwh),

    pct: (b.kwh / total) * 100,

    color: b.color,

  }));

}



export function buildMultiDayOverview(

  forecast: SolarForecast | null,

  timezone: string,

  now = new Date().toISOString(),

): SolarMultiDayRow[] {

  if (!forecast?.points.length) return [];



  const hoursPerPoint = inferForecastIntervalMs(forecast.points) / 3_600_000;

  const byDate = new Map<string, typeof forecast.points>();



  for (const point of forecast.points) {

    const key = localDateKey(point.timestamp, timezone);

    const list = byDate.get(key) ?? [];

    list.push(point);

    byDate.set(key, list);

  }



  const todayKey = localDateKey(now, timezone);

  const tomorrowKey = tomorrowDateKey(now, timezone);



  const rows: SolarMultiDayRow[] = [...byDate.entries()]

    .filter(([dateKey]) => dateKey >= todayKey)

    .sort(([a], [b]) => a.localeCompare(b))

    .slice(0, 7)

    .map(([dateKey, points]) => {

      let expectedKwh = roundKwh(sumEnergyKwh(points, hoursPerPoint));

      const isHourly = points.length <= 24;

      let isPartial = isHourly ? points.length < 20 : points.length < 80;



      if (dateKey === todayKey && forecast.expected_today_kwh != null) {

        expectedKwh = roundKwh(forecast.expected_today_kwh);

        isPartial = false;

      } else if (dateKey === tomorrowKey && forecast.expected_tomorrow_kwh != null) {

        expectedKwh = roundKwh(forecast.expected_tomorrow_kwh);

      }



      const date = new Date(`${dateKey}T12:00:00`);

      const label =

        dateKey === todayKey

          ? "Idag"

          : dateKey === tomorrowKey

            ? "Imorgon"

            : date.toLocaleDateString("sv-SE", { weekday: "short", day: "numeric", month: "short" });



      return { dateKey, label, expectedKwh, pointCount: points.length, isPartial };

    });



  return rows;

}



export function buildComparisonBars(performance: SolarPerformance | null): SolarComparisonBar[] {

  if (!performance?.days.length) return [];



  return performance.days

    .slice(-7)

    .map((day) => {

      const date = new Date(`${day.date}T12:00:00`);

      const ratioPct =

        day.actual_kwh != null && day.expected_kwh != null && day.expected_kwh > 0

          ? (day.actual_kwh / day.expected_kwh) * 100

          : null;

      return {

        label: date.toLocaleDateString("sv-SE", { weekday: "short", day: "numeric", month: "short" }),

        dateKey: day.date,

        actualKwh: day.actual_kwh,

        expectedKwh: day.expected_kwh,

        ratioPct,

      };

    });

}



export function buildWeatherFactors(

  weather: SolarWeather | null,

  timezone: string,

  now = new Date().toISOString(),

): SolarWeatherFactors {

  if (!weather?.hours.length) {

    return {

      maxGhi: null,

      avgGhi: null,

      maxTempC: null,

      avgTempC: null,

      maxWindMs: null,

      avgWindMs: null,

      avgCloudPct: null,

      totalPrecipMm: null,

    };

  }



  const todayKey = localDateKey(now, timezone);

  const hours = weather.hours.filter((h) => localDateKey(h.timestamp, timezone) === todayKey);

  if (hours.length === 0) {

    return {

      maxGhi: null,

      avgGhi: null,

      maxTempC: null,

      avgTempC: null,

      maxWindMs: null,

      avgWindMs: null,

      avgCloudPct: null,

      totalPrecipMm: null,

    };

  }



  const ghi = hours.map((h) => h.ghi_wm2).filter((v): v is number => v != null);

  const temps = hours.map((h) => h.temperature_c).filter((v): v is number => v != null);

  const winds = hours.map((h) => h.wind_speed_ms).filter((v): v is number => v != null);

  const clouds = hours.map((h) => h.cloud_cover_pct).filter((v): v is number => v != null);

  const precip = hours.map((h) => h.precipitation_mm ?? 0);



  return {

    maxGhi: ghi.length ? Math.max(...ghi) : null,

    avgGhi: ghi.length ? Math.round(avg(ghi) ?? 0) : null,

    maxTempC: temps.length ? Math.max(...temps) : null,

    avgTempC: temps.length ? Math.round((avg(temps) ?? 0) * 10) / 10 : null,

    maxWindMs: winds.length ? Math.max(...winds) : null,

    avgWindMs: winds.length ? Math.round((avg(winds) ?? 0) * 10) / 10 : null,

    avgCloudPct: clouds.length ? Math.round(avg(clouds) ?? 0) : null,

    totalPrecipMm: precip.length ? Math.round(precip.reduce((s, v) => s + v, 0) * 10) / 10 : null,

  };

}



export function buildKpiSparklines(

  chartSeries: SolarProductionChartPoint[],

  confidencePct: number | null,

): SolarKpiSparklines {

  return {

    forecast: chartSeries.map((p) => (p.forecastKw ?? 0) * 1000),

    actual: chartSeries.map((p) => (p.actualKw ?? 0) * 1000),

    confidence: chartSeries.map(() => confidencePct ?? 0),

  };

}



export function chartYMax(rows: SolarProductionChartPoint[]): number {

  let max = 0;

  for (const row of rows) {

    if (row.actualKw != null) max = Math.max(max, row.actualKw);

    if (row.forecastKw != null) max = Math.max(max, row.forecastKw);

    if (row.yesterdayKw != null) max = Math.max(max, row.yesterdayKw);

  }

  if (max <= 0) return 4;

  return Math.ceil(max * 1.15 * 10) / 10;

}



export function exportSolarCsv(

  chartSeries: SolarProductionChartPoint[],

  filename = "solprognos-export.csv",

): void {

  if (typeof window === "undefined" || chartSeries.length === 0) return;

  if (typeof URL.createObjectURL !== "function") return;



  const header = ["time", "forecast_kw", "actual_kw", "yesterday_kw", "battery_soc_pct"];

  const rows = chartSeries.map((row) =>

    [row.label, row.forecastKw ?? "", row.actualKw ?? "", row.yesterdayKw ?? "", row.batterySocPct ?? ""].join(

      ",",

    ),

  );

  const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });

  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");

  anchor.href = url;

  anchor.download = filename;

  anchor.click();

  URL.revokeObjectURL(url);

}



export function tomorrowForecastPoints(

  forecast: SolarForecast | null,

  timezone: string,

  now = new Date().toISOString(),

): { label: string; forecastKw: number; energyKwh: number }[] {

  if (!forecast?.points.length) return [];

  const tomorrowKey = tomorrowDateKey(now, timezone);

  const tomorrowPoints = forecast.points.filter((p) => localDateKey(p.timestamp, timezone) === tomorrowKey);

  const hoursPerPoint = inferForecastIntervalMs(tomorrowPoints.length ? tomorrowPoints : forecast.points) / 3_600_000;



  return tomorrowPoints

    .map((p) => ({

      label: formatChartClock(p.timestamp, timezone),

      forecastKw: roundKw(p.corrected_power_w),

      energyKwh: roundKwh(p.expected_energy_kwh ?? (p.corrected_power_w * hoursPerPoint) / 1000),

    }));

}



export function buildTomorrowForecast(

  forecast: SolarForecast | null,

  timezone: string,

  now = new Date().toISOString(),

): {

  points: { label: string; forecastKw: number; energyKwh: number }[];

  expectedKwh: number | null;

  stale: boolean;

  message: string | null;

} {

  if (!forecast) {

    return {

      points: [],

      expectedKwh: null,

      stale: true,

      message: "Ingen solprognos tillgänglig.",

    };

  }



  const stale = isForecastStale(forecast.generated_at, 12, now);

  const points = tomorrowForecastPoints(forecast, timezone, now);

  const fromPoints =

    points.length > 0 ? roundKwh(points.reduce((sum, point) => sum + point.energyKwh, 0)) : null;

  const apiValue =

    forecast.expected_tomorrow_kwh != null ? roundKwh(forecast.expected_tomorrow_kwh) : null;

  const expectedKwh = fromPoints ?? (stale ? null : apiValue);



  if (expectedKwh == null) {

    return {

      points,

      expectedKwh: null,

      stale,

      message: stale

        ? "Prognosen är inaktuell och innehåller inga timmar för imorgon. Vänta på ny prognos."

        : "Ingen imorgon-prognos tillgänglig ännu — prognoshorisonten räcker inte till imorgon.",

    };

  }



  return {

    points,

    expectedKwh,

    stale,

    message: stale

      ? "Prognosen är inaktuell — imorgon-värdet kan vara ungefärligt tills ny prognos körs."

      : points.length === 0

        ? "Total dagsprognos finns, men detaljerad timkurva saknas i nuvarande prognosdata."

        : null,

  };

}


