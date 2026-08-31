import type { DisplayOverview } from "@/lib/displayOverview";

export const MISSING = "--";

/**
 * A numeric readout split into a big value and a small unit so the two can be
 * typeset at different sizes without the layout shifting when data is missing.
 */
export interface Reading {
  value: string;
  unit: string;
}

/**
 * Number format used throughout the kiosk: non-breaking-space thousands
 * separators with a decimal point, matching the design reference ("2 846 kr",
 * "3.25 kW"). Swedish `toLocaleString` would emit a decimal comma instead.
 */
export function formatNumber(value: number, digits: number): string {
  const fixed = Math.abs(value).toFixed(digits);
  const [whole, fraction] = fixed.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
  const sign = value < 0 ? "\u2212" : "";
  return fraction ? `${sign}${grouped}.${fraction}` : `${sign}${grouped}`;
}

const sv = formatNumber;

function reading(value: number | null | undefined, unit: string, digits: number): Reading {
  if (value == null || !Number.isFinite(value)) return { value: MISSING, unit: "" };
  return { value: sv(value, digits), unit };
}

export function kwReading(value: number | null | undefined): Reading {
  return reading(value, "kW", 2);
}

export function kwhReading(value: number | null | undefined): Reading {
  return reading(value, "kWh", 1);
}

export function pctReading(value: number | null | undefined): Reading {
  if (value == null || !Number.isFinite(value)) return { value: MISSING, unit: "" };
  return { value: sv(Math.round(value), 0), unit: "%" };
}

export function ampReading(value: number | null | undefined): Reading {
  return reading(value, "A", 1);
}

export function tempReading(value: number | null | undefined): Reading {
  return reading(value, "°C", 1);
}

/** Charger power: watts below 1 kW, kilowatts above, matching the mockup's "0 W". */
export function powerReading(value: number | null | undefined): Reading {
  if (value == null || !Number.isFinite(value)) return { value: MISSING, unit: "" };
  if (Math.abs(value) >= 1000) return { value: sv(value / 1000, 2), unit: "kW" };
  return { value: sv(Math.round(value), 0), unit: "W" };
}

export function krReading(value: number | null | undefined, digits = 0): Reading {
  return reading(value, "kr", digits);
}

/** "2 846 kr" — grouped thousands, no decimals, for the economy KPIs. */
export function formatKr(value: number | null | undefined, digits = 0): string {
  if (value == null || !Number.isFinite(value)) return MISSING;
  return `${sv(value, digits)} kr`;
}

/** Signed variant used for the net figure ("+912 kr"). */
export function formatKrSigned(value: number | null | undefined, digits = 0): string {
  if (value == null || !Number.isFinite(value)) return MISSING;
  const sign = value > 0 ? "+" : "";
  return `${sign}${sv(value, digits)} kr`;
}

export function formatOre(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return MISSING;
  return `${sv(value, 1)} öre/kWh`;
}

export type DeltaDirection = "up" | "down" | "flat";

export function formatDelta(pct: number | null | undefined): { text: string; direction: DeltaDirection } {
  if (pct == null || !Number.isFinite(pct)) return { text: MISSING, direction: "flat" };
  if (Math.abs(pct) < 0.5) return { text: "0%", direction: "flat" };
  const direction: DeltaDirection = pct > 0 ? "up" : "down";
  const arrow = direction === "up" ? "\u2191" : "\u2193";
  const sign = pct > 0 ? "+" : "-";
  return { text: `${arrow} ${sign}${sv(Math.abs(pct), 0)}%`, direction };
}

/**
 * Age of the newest reading in Swedish, for the banner that warns when a site's
 * data has stopped flowing — a site not yet mapped to its Heartbeat system, or a
 * dead integration. Coarse on purpose: the point is the order of magnitude.
 */
export function formatDataAge(seconds: number | null | undefined): string | null {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return null;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) return "under en minut";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "1 dag" : `${days} dagar`;
}

export function formatClockHms(iso: string | null | undefined, timezone: string): string {
  if (!iso) return "--:--:--";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--:--:--";
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

/** "24 aug. 08:00" — the format used by the vehicle/charger/spa panels. */
export function formatDayTime(iso: string | null | undefined, timezone: string): string {
  if (!iso) return MISSING;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return MISSING;
  const day = new Intl.DateTimeFormat("sv-SE", {
    timeZone: timezone,
    day: "numeric",
    month: "short",
  }).format(date);
  const time = new Intl.DateTimeFormat("sv-SE", {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
  return `${day} ${time}`;
}

export function formatHeaderDate(now: Date, timezone: string) {
  return {
    weekday: new Intl.DateTimeFormat("sv-SE", { timeZone: timezone, weekday: "long" }).format(now),
    date: new Intl.DateTimeFormat("sv-SE", {
      timeZone: timezone,
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(now),
    time: new Intl.DateTimeFormat("sv-SE", {
      timeZone: timezone,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(now),
  };
}

export function sparklineValues(data: DisplayOverview | null, key: string): number[] {
  return (data?.sparklines?.[key]?.points ?? []).map((point) => point.value);
}

/** Section text that must degrade to "Data saknas" rather than a fake zero. */
export function sectionText(
  available: boolean | undefined,
  value: string | null | undefined,
  fallback = "Data saknas",
): string {
  if (available === false) return fallback;
  if (value == null || value === "") return MISSING;
  return value;
}

export function flowNode(data: DisplayOverview | null, key: string) {
  return data?.flow?.nodes?.find((node) => node.key === key) ?? null;
}
