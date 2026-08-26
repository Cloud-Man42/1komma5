/** Geometry and helpers for analog boost-style power gauges. */

export const GAUGE_MIN_ANGLE = -132;
export const GAUGE_MAX_ANGLE = 132;
export const GAUGE_SWEEP = GAUGE_MAX_ANGLE - GAUGE_MIN_ANGLE;
export const DEFAULT_GAUGE_MAX_W = 10_000;
export const GAUGE_ACTIVE_THRESHOLD_W = 25;

const GAUGE_MAX_STEPS_KW = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 15, 20] as const;

/** Round up to a readable full-scale value in watts for analog gauges. */
export function niceGaugeMaxW(...candidates: Array<number | null | undefined>): number {
  const values = candidates.filter((value): value is number => value != null && value > 0);
  const targetKw = Math.max(...values, 1200) / 1000;
  const step = GAUGE_MAX_STEPS_KW.find((value) => value >= targetKw * 1.05) ?? 20;
  return step * 1000;
}

export function formatGaugeScaleKw(maxW: number): string {
  const kw = maxW / 1000;
  return Number.isInteger(kw) ? `${kw}` : kw.toFixed(1);
}

export interface GaugeScaleSet {
  solarMaxW: number;
  houseMaxW: number;
  batteryMaxW: number;
  gridMaxW: number;
}

export function resolveGaugeScales(input: {
  solarW: number;
  houseW: number;
  batteryW: number;
  gridW: number;
  solarPeakW?: number | null;
  inverterMaxKw?: number | null;
  mainFuseA?: number | null;
}): GaugeScaleSet {
  const fuseMaxW =
    input.mainFuseA != null && input.mainFuseA > 0
      ? Math.round(input.mainFuseA * 230 * Math.sqrt(3))
      : null;
  const inverterMaxW =
    input.inverterMaxKw != null && input.inverterMaxKw > 0 ? input.inverterMaxKw * 1000 : null;

  return {
    solarMaxW:
      inverterMaxW ??
      niceGaugeMaxW(input.solarPeakW, input.solarW * 1.15, 5000),
    houseMaxW: niceGaugeMaxW(input.houseW * 1.35, fuseMaxW != null ? fuseMaxW * 0.6 : null, 3000),
    batteryMaxW: niceGaugeMaxW(Math.abs(input.batteryW) * 1.35, inverterMaxW != null ? inverterMaxW * 0.8 : null, 5000),
    gridMaxW: niceGaugeMaxW(Math.abs(input.gridW) * 1.35, fuseMaxW, input.houseW + Math.abs(input.gridW), 5000),
  };
}

export type GaugeScaleMode = "positive" | "bidirectional";

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Map watts to needle angle (degrees, 0 = straight up). */
export function needleAngleForWatts(
  watts: number,
  maxW: number,
  mode: GaugeScaleMode = "positive",
): number {
  const max = Math.max(maxW, 1);
  if (mode === "bidirectional") {
    const ratio = clamp(watts / max, -1, 1);
    return ratio * GAUGE_MAX_ANGLE;
  }
  const ratio = clamp(Math.abs(watts) / max, 0, 1);
  return GAUGE_MIN_ANGLE + ratio * GAUGE_SWEEP;
}

export function gaugeFillRatio(watts: number, maxW: number, mode: GaugeScaleMode = "positive"): number {
  const max = Math.max(maxW, 1);
  if (mode === "bidirectional") {
    return clamp(Math.abs(watts) / max, 0, 1);
  }
  return clamp(Math.max(0, watts) / max, 0, 1);
}

export function isGaugeActive(watts: number, mode: GaugeScaleMode = "positive"): boolean {
  if (mode === "bidirectional") {
    return Math.abs(watts) >= GAUGE_ACTIVE_THRESHOLD_W;
  }
  return watts >= GAUGE_ACTIVE_THRESHOLD_W;
}

/** Polar coords with 0° at top (12 o'clock). */
export function polar(cx: number, cy: number, radius: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad),
  };
}

export function describeArc(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number,
): string {
  const start = polar(cx, cy, radius, startAngle);
  const end = polar(cx, cy, radius, endAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${start.x.toFixed(2)} ${start.y.toFixed(2)} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x.toFixed(2)} ${end.y.toFixed(2)}`;
}

export function formatGaugeKw(watts: number): string {
  const kw = Math.abs(watts) / 1000;
  if (kw >= 10) return `${kw.toFixed(1)}`;
  if (kw >= 1) return `${kw.toFixed(2)}`;
  return `${kw.toFixed(2)}`;
}

export function tickAngles(count: number): number[] {
  if (count <= 1) return [GAUGE_MIN_ANGLE];
  const step = GAUGE_SWEEP / (count - 1);
  return Array.from({ length: count }, (_, i) => GAUGE_MIN_ANGLE + step * i);
}
