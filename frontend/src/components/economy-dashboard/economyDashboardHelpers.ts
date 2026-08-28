import type { FinancialStat, MarketPricePoint, YearForecastResponse } from "@/lib/api";

export const DEFAULT_INVESTMENT_SEK = 152_000;

export const SITE_INVESTMENT_SEK: Record<string, number> = {
  akarp: 148_000,
  "summer-house-denmark": 90_000,
};

export function resolveSiteInvestmentSek(siteSlug: string): number {
  return SITE_INVESTMENT_SEK[siteSlug.trim().toLowerCase()] ?? DEFAULT_INVESTMENT_SEK;
}
export const DEFAULT_MONTHLY_BUDGET_SEK = 2_700;

export interface EconomyTotals {
  solarSavingsSek: number;
  batterySavingsSek: number;
  exportRevenueSek: number;
  gridImportCostSek: number;
  importedKwh: number;
  exportedKwh: number;
  solarSelfConsumedKwh: number;
  batterySelfConsumedKwh: number;
}

export interface EconomyMetricChange {
  value: number;
  pct: number | null;
  direction: "up" | "down" | "flat";
}

export interface EconomyDisplayMetrics {
  totalSavingsSek: number;
  gridImportCostSek: number;
  exportRevenueSek: number;
  netCostSek: number;
  ytdReturnPct: number;
  changes: {
    totalSavings: EconomyMetricChange;
    gridImportCost: EconomyMetricChange;
    exportRevenue: EconomyMetricChange;
    netCost: EconomyMetricChange;
  };
}

export interface CostBreakdownSlice {
  id: string;
  label: string;
  amountSek: number;
  pct: number;
  color: string;
}

export interface DailyCostPoint {
  date: string;
  label: string;
  purchasedSek: number;
  gridFeeSek: number;
  taxSek: number;
  soldSek: number;
  netSek: number;
  importedKwh: number;
  exportedKwh: number;
}

export interface PriceAnalysis {
  spotOre: number;
  purchaseOre: number;
  exportOre: number;
  cheapestOre: number;
  cheapestAt: string | null;
  expensiveOre: number;
  expensiveAt: string | null;
}

export interface EconomyInsight {
  id: string;
  text: string;
}

export interface EconomyGoal {
  id: string;
  label: string;
  targetLabel: string;
  valuePct: number;
  displayValue: string;
  tone: "green" | "orange" | "blue";
}

export function aggregateFinancialStats(stats: FinancialStat[]): EconomyTotals {
  return stats.reduce(
    (sum, stat) => ({
      solarSavingsSek: sum.solarSavingsSek + stat.solar_savings_sek,
      batterySavingsSek: sum.batterySavingsSek + stat.battery_savings_sek,
      exportRevenueSek: sum.exportRevenueSek + stat.export_revenue_sek,
      gridImportCostSek: sum.gridImportCostSek + stat.grid_import_cost_sek,
      importedKwh: sum.importedKwh + stat.imported_kwh,
      exportedKwh: sum.exportedKwh + stat.exported_kwh,
      solarSelfConsumedKwh: sum.solarSelfConsumedKwh + stat.solar_self_consumed_kwh,
      batterySelfConsumedKwh: sum.batterySelfConsumedKwh + stat.battery_self_consumed_kwh,
    }),
    {
      solarSavingsSek: 0,
      batterySavingsSek: 0,
      exportRevenueSek: 0,
      gridImportCostSek: 0,
      importedKwh: 0,
      exportedKwh: 0,
      solarSelfConsumedKwh: 0,
      batterySelfConsumedKwh: 0,
    },
  );
}

export function filterStatsForMonth(stats: FinancialStat[], year: number, month: number): FinancialStat[] {
  const prefix = `${year}-${String(month).padStart(2, "0")}`;
  return stats.filter((stat) => stat.period_start.startsWith(prefix));
}

export function computeMetricChange(current: number, previous: number): EconomyMetricChange {
  if (Math.abs(previous) < 0.005) {
    return { value: current, pct: null, direction: "flat" };
  }
  const pct = ((current - previous) / Math.abs(previous)) * 100;
  return {
    value: current,
    pct,
    direction: Math.abs(pct) < 0.5 ? "flat" : pct > 0 ? "up" : "down",
  };
}

export function computeTotalSavings(totals: EconomyTotals, smartChargingSek = 0): number {
  return totals.solarSavingsSek + totals.batterySavingsSek + smartChargingSek;
}

export function computeNetCost(totals: EconomyTotals): number {
  return Math.max(0, totals.gridImportCostSek - totals.exportRevenueSek);
}

export function computeYtdReturnPct(ytdSavingsSek: number, investmentSek = DEFAULT_INVESTMENT_SEK): number {
  if (investmentSek <= 0) return 0;
  return (ytdSavingsSek / investmentSek) * 100;
}

export function buildEconomyMetrics(
  current: EconomyTotals,
  previous: EconomyTotals,
  ytdSavingsSek: number,
  smartChargingSek = 0,
): EconomyDisplayMetrics {
  const totalSavingsSek = computeTotalSavings(current, smartChargingSek);
  const prevTotalSavings = computeTotalSavings(previous, smartChargingSek);
  const netCostSek = computeNetCost(current);
  const prevNetCost = computeNetCost(previous);

  return {
    totalSavingsSek,
    gridImportCostSek: current.gridImportCostSek,
    exportRevenueSek: current.exportRevenueSek,
    netCostSek,
    ytdReturnPct: computeYtdReturnPct(ytdSavingsSek),
    changes: {
      totalSavings: computeMetricChange(totalSavingsSek, prevTotalSavings),
      gridImportCost: computeMetricChange(current.gridImportCostSek, previous.gridImportCostSek),
      exportRevenue: computeMetricChange(current.exportRevenueSek, previous.exportRevenueSek),
      netCost: computeMetricChange(netCostSek, prevNetCost),
    },
  };
}

export function buildCostBreakdown(importCostSek: number): CostBreakdownSlice[] {
  const shares = [
    { id: "purchase", label: "Köpt el", pct: 0.56, color: "#a78bfa" },
    { id: "grid", label: "Nätavgift", pct: 0.23, color: "#38bdf8" },
    { id: "tax", label: "Skatt", pct: 0.15, color: "#2dd4bf" },
    { id: "fees", label: "Påslag & avgifter", pct: 0.06, color: "#fb923c" },
  ];
  return shares.map((slice) => ({
    ...slice,
    amountSek: importCostSek * slice.pct,
    pct: slice.pct * 100,
  }));
}

export function buildDailyCostSeries(stats: FinancialStat[]): DailyCostPoint[] {
  return stats.map((stat) => {
    const importCost = stat.grid_import_cost_sek;
    const purchasedSek = importCost * 0.56;
    const gridFeeSek = importCost * 0.23;
    const taxSek = importCost * 0.15;
    const soldSek = stat.export_revenue_sek;
    const netSek = importCost - soldSek;
    const [, month, day] = stat.period_start.split("-").map(Number);
    return {
      date: stat.period_start,
      label: `${day}/${month}`,
      purchasedSek,
      gridFeeSek,
      taxSek,
      soldSek: -soldSek,
      netSek,
      importedKwh: stat.imported_kwh,
      exportedKwh: stat.exported_kwh,
    };
  });
}

const EUR_TO_SEK = 11.2;

export function eurToOre(eurKwh: number): number {
  return eurKwh * EUR_TO_SEK * 100;
}

export function buildPriceAnalysis(
  points: MarketPricePoint[],
  purchasePriceSekKwh: number,
  exportPriceSekKwh: number,
  timezone: string,
): PriceAnalysis {
  const spotValues = points.map((p) => p.spot_eur_kwh).filter((v) => Number.isFinite(v));
  const spotOre = spotValues.length
    ? eurToOre(spotValues.reduce((a, b) => a + b, 0) / spotValues.length)
    : eurToOre(points[0]?.spot_eur_kwh ?? 0.04);

  let cheapest: MarketPricePoint | null = null;
  let expensive: MarketPricePoint | null = null;
  for (const point of points) {
    const price = point.all_in_eur_kwh ?? point.spot_eur_kwh;
    if (!Number.isFinite(price)) continue;
    if (!cheapest || price < (cheapest.all_in_eur_kwh ?? cheapest.spot_eur_kwh)) {
      cheapest = point;
    }
    if (!expensive || price > (expensive.all_in_eur_kwh ?? expensive.spot_eur_kwh)) {
      expensive = point;
    }
  }

  const formatTs = (iso: string | null) => {
    if (!iso) return null;
    return new Date(iso).toLocaleString("sv-SE", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: timezone,
    });
  };

  return {
    spotOre: Math.round(spotOre),
    purchaseOre: Math.round(purchasePriceSekKwh * 100),
    exportOre: Math.round(exportPriceSekKwh * 100),
    cheapestOre: cheapest ? Math.round(eurToOre(cheapest.all_in_eur_kwh ?? cheapest.spot_eur_kwh)) : 0,
    cheapestAt: formatTs(cheapest?.timestamp ?? null),
    expensiveOre: expensive ? Math.round(eurToOre(expensive.all_in_eur_kwh ?? expensive.spot_eur_kwh)) : 0,
    expensiveAt: formatTs(expensive?.timestamp ?? null),
  };
}

export interface SavingsBreakdownItem {
  id: string;
  label: string;
  amountSek: number;
  pct: number;
  color: string;
  description: string;
}

export const SAVINGS_BREAKDOWN_META = [
  {
    id: "solar",
    label: "Självförbrukning",
    color: "#4ade80",
    description: "Solenergi som använts i huset istället för köpt el.",
  },
  {
    id: "battery",
    label: "Batterioptimering",
    color: "#38bdf8",
    description: "Besparing när lagrad el ersätter dyr nätimport.",
  },
  {
    id: "ev",
    label: "Laddsmart optimering",
    color: "#fb923c",
    description: "Besparing från laddning vid låga elpriser.",
  },
] as const;

export function buildSavingsBreakdown(
  totals: EconomyTotals,
  smartChargingSek = 0,
): SavingsBreakdownItem[] {
  const amounts: Record<(typeof SAVINGS_BREAKDOWN_META)[number]["id"], number> = {
    solar: totals.solarSavingsSek,
    battery: totals.batterySavingsSek,
    ev: smartChargingSek,
  };
  const total = Object.values(amounts).reduce((sum, value) => sum + value, 0) || 1;
  return SAVINGS_BREAKDOWN_META.map((meta) => ({
    ...meta,
    amountSek: amounts[meta.id],
    pct: (amounts[meta.id] / total) * 100,
  }));
}

export function computeDailyEconomicResult(stat: FinancialStat): number {
  return (
    stat.solar_savings_sek +
    stat.battery_savings_sek +
    stat.export_revenue_sek -
    stat.grid_import_cost_sek
  );
}

export function computeDailyActivityKwh(stat: FinancialStat): number {
  return (
    stat.solar_self_consumed_kwh +
    stat.battery_self_consumed_kwh +
    stat.imported_kwh +
    stat.exported_kwh
  );
}

const MIN_DAILY_ACTIVITY_KWH = 1;
const PARTIAL_DAY_ACTIVITY_RATIO = 0.35;

export function filterRepresentativeDailyStats(stats: FinancialStat[]): FinancialStat[] {
  const withActivity = stats.filter((stat) => computeDailyActivityKwh(stat) >= MIN_DAILY_ACTIVITY_KWH);
  if (withActivity.length === 0) return [];

  const activities = withActivity.map(computeDailyActivityKwh).sort((a, b) => a - b);
  const median = activities[Math.floor(activities.length / 2)] ?? 0;
  const threshold = Math.max(MIN_DAILY_ACTIVITY_KWH, median * PARTIAL_DAY_ACTIVITY_RATIO);

  return withActivity.filter((stat) => computeDailyActivityKwh(stat) >= threshold);
}

export function findBestEconomyDay(stats: FinancialStat[]): FinancialStat | null {
  const candidates = filterRepresentativeDailyStats(stats);
  if (candidates.length === 0) return null;

  return candidates.reduce((best, current) =>
    computeDailyEconomicResult(current) > computeDailyEconomicResult(best) ? current : best,
  );
}

export function formatDailyEconomicResultLabel(sek: number): string {
  if (Math.abs(sek) < 0.5) return "0 kr netto";
  const sign = sek > 0 ? "+" : "−";
  return `${sign}${formatEconomyKr(Math.abs(sek))} netto`;
}

export function buildEconomyGoals(totals: EconomyTotals): EconomyGoal[] {
  const selfUseKwh = totals.solarSelfConsumedKwh + totals.batterySelfConsumedKwh;
  const producedKwh = selfUseKwh + totals.exportedKwh;
  const selfUsePct = producedKwh > 0 ? (selfUseKwh / producedKwh) * 100 : 0;
  const exportSharePct = producedKwh > 0 ? (totals.exportedKwh / producedKwh) * 100 : 0;
  const co2Kg = Math.round(selfUseKwh * 0.4);

  return [
    {
      id: "cost",
      label: "Minska elkostnad",
      targetLabel: "Target −50%",
      valuePct: 45,
      displayValue: "45%",
      tone: "orange",
    },
    {
      id: "selfuse",
      label: "Öka självförbrukning",
      targetLabel: "Target >70%",
      valuePct: Math.min(100, selfUsePct),
      displayValue: `${Math.round(selfUsePct)}%`,
      tone: "green",
    },
    {
      id: "export",
      label: "Export till nät",
      targetLabel: "Target <20%",
      valuePct: Math.min(100, exportSharePct),
      displayValue: `${Math.round(exportSharePct)}%`,
      tone: "blue",
    },
    {
      id: "co2",
      label: "CO₂-besparing",
      targetLabel: "Target >2000 kg",
      valuePct: Math.min(100, (co2Kg / 2000) * 100),
      displayValue: `${co2Kg.toLocaleString("sv-SE")} kg`,
      tone: "green",
    },
  ];
}

export function buildEconomyInsights(
  totals: EconomyTotals,
  dailyStats: FinancialStat[],
  smartChargingSek: number,
): EconomyInsight[] {
  const selfUseKwh = totals.solarSelfConsumedKwh + totals.batterySelfConsumedKwh;
  const producedKwh = selfUseKwh + totals.exportedKwh;
  const selfUsePct = producedKwh > 0 ? Math.round((selfUseKwh / producedKwh) * 100) : 0;

  const bestDay = findBestEconomyDay(dailyStats);
  const bestDayLabel = bestDay
    ? new Date(bestDay.period_start).toLocaleDateString("sv-SE", { day: "numeric", month: "short" })
    : null;
  const bestDayNet = bestDay ? computeDailyEconomicResult(bestDay) : null;

  const insights: EconomyInsight[] = [
    { id: "peak", text: "Du köpte mest el mellan 17:00–20:00." },
    {
      id: "selfuse",
      text: `${selfUsePct}% av solenergin användes själv eller lagrades.`,
    },
    {
      id: "battery",
      text: `Batteriet tjänade dig ${Math.round(totals.batterySavingsSek).toLocaleString("sv-SE")} kr denna månad.`,
    },
  ];

  if (bestDay && bestDayLabel && bestDayNet != null) {
    insights.push({
      id: "bestday",
      text: `Bästa dagen: ${bestDayLabel} (${formatDailyEconomicResultLabel(bestDayNet)}).`,
    });
  }

  if (smartChargingSek > 0) {
    insights.push({
      id: "ev",
      text: `Smart laddning sparade ${Math.round(smartChargingSek).toLocaleString("sv-SE")} kr.`,
    });
  }

  return insights.slice(0, 4);
}

export function buildExtendedEconomyInsights(
  totals: EconomyTotals,
  dailyStats: FinancialStat[],
  smartChargingSek: number,
): EconomyInsight[] {
  const quick = buildEconomyInsights(totals, dailyStats, smartChargingSek);
  const importTotal = formatEconomyKr(totals.gridImportCostSek);
  const exportTotal = formatEconomyKr(totals.exportRevenueSek);
  const solarTotal = formatEconomyKr(totals.solarSavingsSek);
  const extra: EconomyInsight[] = [
    { id: "import-month", text: `Total elkostnad denna månad: ${importTotal}.` },
    { id: "export-month", text: `Total intäkt från såld el: ${exportTotal}.` },
    { id: "solar-month", text: `Solbesparing denna månad: ${solarTotal}.` },
    {
      id: "net",
      text: `Netto efter intäkter: ${formatEconomyKr(computeNetCost(totals))}.`,
    },
  ];
  const seen = new Set(quick.map((item) => item.id));
  return [...quick, ...extra.filter((item) => !seen.has(item.id))];
}

export function formatEconomyKr(amountSek: number): string {
  return `${Math.round(amountSek).toLocaleString("sv-SE")} kr`;
}

export function formatEconomyPct(pct: number | null, invertGood = false): string {
  if (pct == null || !Number.isFinite(pct)) return "—";
  const abs = Math.abs(Math.round(pct));
  const arrow = pct >= 0 ? "↑" : "↓";
  if (invertGood) {
    return pct <= 0 ? `↓ ${abs}%` : `↑ ${abs}%`;
  }
  return `${arrow} ${abs}%`;
}

export function monthRangeLabel(year: number, month: number, dayCount?: number): string {
  const start = new Date(year, month - 1, 1);
  const endDay = dayCount ?? new Date(year, month, 0).getDate();
  const end = new Date(year, month - 1, endDay);
  const fmt = new Intl.DateTimeFormat("sv-SE", { day: "numeric", month: "short", year: "numeric" });
  return `${fmt.format(start).replace(".", " ").replace(" ", " ")} – ${fmt.format(end).replace(".", " ")}`;
}

export function forecastMonthCost(forecast: YearForecastResponse | null, year: number, month: number): number | null {
  const key = `${year}-${String(month).padStart(2, "0")}`;
  const row = forecast?.months.find((m) => m.month === key);
  if (!row) return null;
  return row.total.grid_import_cost_sek - row.total.export_revenue_sek;
}

export function exportFinancialCsv(stats: FinancialStat[], filename = "ekonomi-rapport.csv"): void {
  if (typeof window === "undefined" || stats.length === 0) return;
  const header = [
    "period",
    "solar_savings_sek",
    "battery_savings_sek",
    "export_revenue_sek",
    "grid_import_cost_sek",
    "imported_kwh",
    "exported_kwh",
  ];
  const rows = stats.map((stat) =>
    [
      stat.period_start,
      stat.solar_savings_sek,
      stat.battery_savings_sek,
      stat.export_revenue_sek,
      stat.grid_import_cost_sek,
      stat.imported_kwh,
      stat.exported_kwh,
    ].join(","),
  );
  const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
  if (typeof URL.createObjectURL !== "function") return;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
