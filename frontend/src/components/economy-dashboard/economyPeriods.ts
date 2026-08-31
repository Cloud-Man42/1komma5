import type { FinancialStat } from "@/lib/api";

/** Periods available in the economy dashboard selector. */
export type EconomyPeriodId =
  | "today"
  | "7d"
  | "this-month"
  | "previous-month"
  | "ytd"
  | "12m"
  | "since-installation";

export type EconomyCompareMode = "previous-period" | "previous-year";

export const ECONOMY_PERIOD_OPTIONS: { id: EconomyPeriodId; label: string }[] = [
  { id: "today", label: "Idag" },
  { id: "7d", label: "7 dagar" },
  { id: "this-month", label: "Denna månad" },
  { id: "previous-month", label: "Förra månaden" },
  { id: "ytd", label: "YTD" },
  { id: "12m", label: "12 månader" },
  { id: "since-installation", label: "Sedan installation" },
];

export const ECONOMY_COMPARE_OPTIONS: { id: EconomyCompareMode; label: string }[] = [
  { id: "previous-period", label: "Föregående period" },
  { id: "previous-year", label: "Föregående år" },
];

function localDateKey(isoDate: string): string {
  return isoDate.slice(0, 10);
}

function addDays(date: Date, days: number): Date {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function formatIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export interface EconomyPeriodRange {
  from: string;
  to: string;
  label: string;
}

export function resolvePeriodRange(period: EconomyPeriodId, now = new Date()): EconomyPeriodRange {
  const today = formatIsoDate(now);
  const year = now.getFullYear();
  const month = now.getMonth() + 1;

  switch (period) {
    case "today":
      return { from: today, to: today, label: "Idag" };
    case "7d": {
      const from = formatIsoDate(addDays(now, -6));
      return { from, to: today, label: "Senaste 7 dagarna" };
    }
    case "this-month": {
      const from = formatIsoDate(startOfMonth(now));
      return { from, to: today, label: "Denna månad" };
    }
    case "previous-month": {
      const prev = new Date(year, now.getMonth() - 1, 1);
      const from = formatIsoDate(startOfMonth(prev));
      const to = formatIsoDate(endOfMonth(prev));
      const fmt = new Intl.DateTimeFormat("sv-SE", { month: "long", year: "numeric" });
      return { from, to, label: fmt.format(prev) };
    }
    case "ytd":
      return { from: `${year}-01-01`, to: today, label: `YTD ${year}` };
    case "12m": {
      const from = formatIsoDate(addDays(now, -364));
      return { from, to: today, label: "Senaste 12 månaderna" };
    }
    case "since-installation":
      return { from: "1970-01-01", to: today, label: "Sedan installation" };
    default:
      return { from: `${year}-${String(month).padStart(2, "0")}-01`, to: today, label: "Denna månad" };
  }
}

export function filterStatsByDateRange(
  stats: FinancialStat[],
  from: string,
  to: string,
): FinancialStat[] {
  return stats.filter((stat) => {
    const key = localDateKey(stat.period_start);
    return key >= from && key <= to;
  });
}

export function filterStatsForPeriod(
  stats: FinancialStat[],
  period: EconomyPeriodId,
  now = new Date(),
): FinancialStat[] {
  const range = resolvePeriodRange(period, now);
  return filterStatsByDateRange(stats, range.from, range.to);
}

export function resolveComparisonRange(
  period: EconomyPeriodId,
  compareMode: EconomyCompareMode,
  now = new Date(),
): EconomyPeriodRange | null {
  if (compareMode === "previous-year") {
    const current = resolvePeriodRange(period, now);
    const shiftYear = (iso: string) => {
      const [y, m, d] = iso.split("-").map(Number);
      return formatIsoDate(new Date(y - 1, m - 1, d));
    };
    return {
      from: shiftYear(current.from),
      to: shiftYear(current.to),
      label: "Samma period förra året",
    };
  }

  switch (period) {
    case "today": {
      const yesterday = formatIsoDate(addDays(now, -1));
      return { from: yesterday, to: yesterday, label: "Igår" };
    }
    case "7d": {
      const to = formatIsoDate(addDays(now, -7));
      const from = formatIsoDate(addDays(now, -13));
      return { from, to, label: "Föregående 7 dagar" };
    }
    case "this-month": {
      const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const from = formatIsoDate(startOfMonth(prev));
      const to = formatIsoDate(endOfMonth(prev));
      const day = now.getDate();
      const cappedTo = formatIsoDate(new Date(prev.getFullYear(), prev.getMonth(), Math.min(day, endOfMonth(prev).getDate())));
      return { from, to: cappedTo, label: "Föregående månad" };
    }
    case "previous-month": {
      const twoBack = new Date(now.getFullYear(), now.getMonth() - 2, 1);
      const from = formatIsoDate(startOfMonth(twoBack));
      const to = formatIsoDate(endOfMonth(twoBack));
      return { from, to, label: "Månaden före" };
    }
    case "ytd": {
      const year = now.getFullYear() - 1;
      const to = formatIsoDate(new Date(year, now.getMonth(), now.getDate()));
      return { from: `${year}-01-01`, to, label: "YTD förra året" };
    }
    case "12m": {
      const to = formatIsoDate(addDays(now, -365));
      const from = formatIsoDate(addDays(now, -729));
      return { from, to, label: "Föregående 12 månader" };
    }
    case "since-installation":
      return null;
    default:
      return null;
  }
}

export function comparisonPeriodLabel(
  period: EconomyPeriodId,
  compareMode: EconomyCompareMode,
): string {
  if (period === "since-installation") return "";
  const range = resolveComparisonRange(period, compareMode);
  return range?.label ?? "Föregående period";
}
