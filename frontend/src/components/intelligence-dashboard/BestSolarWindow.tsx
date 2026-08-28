import type { SolarForecastPoint } from "@/lib/api";

const INTERVAL_HOURS = 0.25;
const DAYLIGHT_MIN_W = 100;
const DEFAULT_WINDOW_POINTS = 5;
const DEFAULT_HOUSE_LOAD_W = 1500;

export interface SolarWindow {
  start: string;
  end: string;
  expectedSurplusKwh: number;
  expectedProductionKwh: number;
  bars: number[];
}

export interface BestSolarWindowInput {
  points: SolarForecastPoint[];
  timezone?: string;
  /** Typical house load (W) used to estimate surplus in the window. */
  houseLoadW?: number | null;
  /** Number of consecutive 15-min forecast points in the window. */
  windowPoints?: number;
  /** Reference instant for selecting today's forecast points (ISO). */
  now?: string;
}

function localDateKey(iso: string, timezone: string): string {
  return new Date(iso).toLocaleDateString("sv-SE", { timeZone: timezone });
}

function formatClock(iso: string, timezone: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

function intervalEnd(iso: string): string {
  return new Date(new Date(iso).getTime() + INTERVAL_HOURS * 3_600_000).toISOString();
}

function houseKwhPerInterval(houseLoadW: number): number {
  return (houseLoadW / 1000) * INTERVAL_HOURS;
}

function surplusKwhForPoint(point: SolarForecastPoint, houseLoadW: number): number {
  const solarKwh = point.expected_energy_kwh ?? 0;
  return Math.max(0, solarKwh - houseKwhPerInterval(houseLoadW));
}

export function computeBestSolarWindow(input: BestSolarWindowInput): SolarWindow | null {
  const { points, timezone = "Europe/Stockholm", houseLoadW = DEFAULT_HOUSE_LOAD_W } = input;
  if (points.length === 0) return null;

  const loadW = houseLoadW ?? DEFAULT_HOUSE_LOAD_W;
  const todayKey = localDateKey(input.now ?? new Date().toISOString(), timezone);
  const todayPoints = [...points]
    .filter((p) => localDateKey(p.timestamp, timezone) === todayKey)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  const daylight = todayPoints.filter((p) => p.corrected_power_w >= DAYLIGHT_MIN_W);
  if (daylight.length === 0) return null;

  const windowSize = Math.min(input.windowPoints ?? DEFAULT_WINDOW_POINTS, daylight.length);
  let bestStart = 0;
  let bestScore = -1;

  for (let i = 0; i <= daylight.length - windowSize; i += 1) {
    const slice = daylight.slice(i, i + windowSize);
    const score = slice.reduce((acc, p) => acc + surplusKwhForPoint(p, loadW), 0);
    if (score > bestScore) {
      bestScore = score;
      bestStart = i;
    }
  }

  // If house load consumes all production (score 0 everywhere), pick strongest power window.
  if (bestScore <= 0) {
    let bestPower = 0;
    for (let i = 0; i <= daylight.length - windowSize; i += 1) {
      const slice = daylight.slice(i, i + windowSize);
      const avgPower = slice.reduce((acc, p) => acc + p.corrected_power_w, 0) / slice.length;
      if (avgPower > bestPower) {
        bestPower = avgPower;
        bestStart = i;
      }
    }
  }

  const window = daylight.slice(bestStart, bestStart + windowSize);
  const maxPower = Math.max(...window.map((p) => p.corrected_power_w), 1);
  const productionKwh = window.reduce((acc, p) => acc + (p.expected_energy_kwh ?? 0), 0);
  const surplusKwh = window.reduce((acc, p) => acc + surplusKwhForPoint(p, loadW), 0);

  return {
    start: formatClock(window[0].timestamp, timezone),
    end: formatClock(intervalEnd(window[window.length - 1].timestamp), timezone),
    expectedSurplusKwh: surplusKwh,
    expectedProductionKwh: productionKwh,
    bars: window.map((p) => Math.max(0.12, p.corrected_power_w / maxPower)),
  };
}

export function BestSolarWindowPanel({ window }: { window: SolarWindow | null }) {
  if (!window) {
    return (
      <section className="idash-panel idash-solar-window-panel">
        <h2 className="idash-panel-title">BÄSTA SOLFÖNSTER</h2>
        <p className="idash-muted">Ingen prognos tillgänglig</p>
      </section>
    );
  }

  return (
    <section className="idash-panel idash-solar-window-panel">
      <h2 className="idash-panel-title">BÄSTA SOLFÖNSTER</h2>
      <p className="idash-solar-window-range">
        {window.start} – {window.end}
      </p>
      <div className="idash-solar-window-bars" aria-hidden="true">
        {window.bars.map((height, index) => (
          <span key={index} style={{ height: `${Math.min(100, height * 100)}%` }} />
        ))}
      </div>
      <p className="idash-solar-window-surplus">
        Förväntat överskott{" "}
        <strong>
          {window.expectedSurplusKwh.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh
        </strong>
      </p>
    </section>
  );
}
