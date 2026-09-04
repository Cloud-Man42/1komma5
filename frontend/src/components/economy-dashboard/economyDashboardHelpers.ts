/**
 * EMIC economy calculations (frontend display layer).
 *
 * Backend source: EnergyReadingRepository.list_financial_stats
 * Docs: docs/ekonomi-berakning.md
 *
 * Per interval (backend):
 * - solar_savings_sek = solar_self_kwh × purchase_price
 * - battery_savings_sek = battery_self_kwh × purchase_price
 * - energy_sale_revenue_sek = export_kwh × effective_sell_price (spot-matched)
 * - grid_benefit_revenue_sek = export_kwh × grid_benefit_rate
 * - export_revenue_sek = energy_sale + grid_benefit (excludes tax credit)
 * - tax_credit_sek = historical skattereduktion (≤2025, allocated by export share)
 * - grid_import_cost_sek = import_kwh × purchase_price
 *
 * Display formulas:
 * - economicBenefit = solar + battery + export (+ optional smart categories)
 * - totalEconomicValue = economicBenefit + taxCredit (historical only)
 * - avoidedCostSavings = solar + battery (+ smart categories) — excludes export
 * - netCost = gridImportCost − exportRevenue (no tax credit)
 * - ytdReturnPct = ytdEconomicBenefit / investment × 100
 * - paybackYears = remainingInvestment / annualizedBenefit (trailing 12m, prognos)
 * - costBreakdown slices = estimated shares of grid_import_cost (56/23/15/6 %)
 */
import type {
  ExportPricingMode,
  FinancialStat,
  MarketPricePoint,
  MarketPricesResponse,
  YearForecastResponse,
} from "@/lib/api";
import {
  marketPointImportSek,
  marketPointSpotSek,
  sekKwhToOre,
  toOrePerKwh,
} from "@/lib/prices";

export type EconomyValueQuality = "ACTUAL" | "CALCULATED" | "ESTIMATED" | "MISSING";

export const SITE_INVESTMENT_SEK: Record<string, number> = {
  akarp: 148_000,
  "summer-house-denmark": 90_000,
};

export function resolveSiteInvestmentSek(siteSlug: string): number | null {
  const value = SITE_INVESTMENT_SEK[siteSlug.trim().toLowerCase()];
  return value != null && value > 0 ? value : null;
}

export const DEFAULT_MONTHLY_BUDGET_SEK = 2_700;

export interface EconomyTotals {
  solarSavingsSek: number;
  batterySavingsSek: number;
  exportRevenueSek: number;
  energySaleRevenueSek: number;
  gridBenefitRevenueSek: number;
  taxCreditSek: number;
  gridImportCostSek: number;
  importedKwh: number;
  exportedKwh: number;
  uncontractedExportedKwh: number;
  solarSelfConsumedKwh: number;
  batterySelfConsumedKwh: number;
  exportSpotPricedFraction: number;
}

export interface EconomyMetricChange {
  value: number;
  previous: number;
  deltaSek: number;
  pct: number | null;
  direction: "up" | "down" | "flat";
}

export interface EconomyDisplayMetrics {
  totalSavingsSek: number;
  avoidedCostSavingsSek: number;
  economicBenefitSek: number;
  gridImportCostSek: number;
  exportRevenueSek: number;
  netCostSek: number;
  ytdReturnPct: number | null;
  ytdEconomicBenefitSek: number;
  lifetimeEconomicBenefitSek: number;
  changes: {
    totalSavings: EconomyMetricChange;
    gridImportCost: EconomyMetricChange;
    exportRevenue: EconomyMetricChange;
    netCost: EconomyMetricChange;
  };
}

export interface PaybackMetrics {
  investmentSek: number | null;
  repaidSek: number;
  remainingSek: number | null;
  repaidPct: number | null;
  paybackYears: number | null;
  annualizedBenefitSek: number | null;
  isForecast: boolean;
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
  dayLabel: string;
  purchasedSek: number;
  gridFeeSek: number;
  taxSek: number;
  soldSek: number;
  netSek: number;
  importedKwh: number;
  exportedKwh: number;
  effectivePriceKrKwh: number | null;
}
export interface PriceAnalysis {
  spotOre: number | null;
  purchaseOre: number | null;
  exportOre: number | null;
  cheapestOre: number | null;
  cheapestAt: string | null;
  expensiveOre: number | null;
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
  tone: "green" | "orange" | "blue" | "warn";
}

export function aggregateFinancialStats(stats: FinancialStat[]): EconomyTotals {
  return stats.reduce(
    (sum, stat) => ({
      solarSavingsSek: sum.solarSavingsSek + stat.solar_savings_sek,
      batterySavingsSek: sum.batterySavingsSek + stat.battery_savings_sek,
      exportRevenueSek: sum.exportRevenueSek + stat.export_revenue_sek,
      energySaleRevenueSek: sum.energySaleRevenueSek + (stat.energy_sale_revenue_sek ?? stat.export_revenue_sek),
      gridBenefitRevenueSek: sum.gridBenefitRevenueSek + (stat.grid_benefit_revenue_sek ?? 0),
      taxCreditSek: sum.taxCreditSek + (stat.tax_credit_sek ?? 0),
      gridImportCostSek: sum.gridImportCostSek + stat.grid_import_cost_sek,
      importedKwh: sum.importedKwh + stat.imported_kwh,
      exportedKwh: sum.exportedKwh + stat.exported_kwh,
      uncontractedExportedKwh: sum.uncontractedExportedKwh + (stat.uncontracted_exported_kwh ?? 0),
      solarSelfConsumedKwh: sum.solarSelfConsumedKwh + stat.solar_self_consumed_kwh,
      batterySelfConsumedKwh: sum.batterySelfConsumedKwh + stat.battery_self_consumed_kwh,
      exportSpotPricedFraction: sum.exportSpotPricedFraction,
    }),
    {
      solarSavingsSek: 0,
      batterySavingsSek: 0,
      exportRevenueSek: 0,
      energySaleRevenueSek: 0,
      gridBenefitRevenueSek: 0,
      taxCreditSek: 0,
      gridImportCostSek: 0,
      importedKwh: 0,
      exportedKwh: 0,
      uncontractedExportedKwh: 0,
      solarSelfConsumedKwh: 0,
      batterySelfConsumedKwh: 0,
      exportSpotPricedFraction: 0,
    },
  );
}

export function computeWeightedEffectiveSellPrice(totals: EconomyTotals): number | null {
  if (totals.exportedKwh <= 0) return null;
  return totals.energySaleRevenueSek / totals.exportedKwh;
}

export interface ExportRevenueBreakdown {
  exportedKwh: number;
  weightedSpotPriceKrKwh: number | null;
  energySaleRevenueSek: number;
  supplierAdjustmentSek: number;
  gridBenefitRevenueSek: number;
  taxCreditSek: number;
  totalExportRevenueSek: number;
  totalEconomicValueSek: number;
  spotPricedFraction: number;
  showTaxCreditNotice: boolean;
  showPreContractExportNotice: boolean;
  preContractExportedKwh: number;
  sellContractStartDate: string | null;
  lines: Array<{
    id: string;
    label: string;
    valueSek: number;
    quality: EconomyValueQuality;
    detail?: string;
  }>;
}

export function buildExportRevenueBreakdown(
  totals: EconomyTotals,
  stats: FinancialStat[],
  now = new Date(),
  pricingMode: ExportPricingMode = "spot",
  sellContractStartDate: string | null = null,
): ExportRevenueBreakdown {
  const contractedExportKwh = Math.max(0, totals.exportedKwh - totals.uncontractedExportedKwh);
  const weightedSpot =
    contractedExportKwh > 0 && stats.length > 0
      ? stats.reduce((sum, stat) => {
          const energySale = stat.energy_sale_revenue_sek ?? stat.export_revenue_sek;
          return sum + energySale;
        }, 0) / contractedExportKwh
      : null;
  const spotFraction =
    contractedExportKwh > 0 && stats.length > 0
      ? stats.reduce(
          (sum, stat) =>
            sum + (stat.export_spot_priced_fraction ?? 0) * Math.max(0, stat.exported_kwh - (stat.uncontracted_exported_kwh ?? 0)),
          0,
        ) / contractedExportKwh
      : 0;
  const showTaxCreditNotice = now.getFullYear() >= 2026 && totals.taxCreditSek <= 0;
  const preContractExportedKwh = totals.uncontractedExportedKwh;
  const showPreContractExportNotice = preContractExportedKwh > 0.005;

  const energySaleLabel =
    pricingMode === "feed_in"
      ? "Inmatningstariff"
      : pricingMode === "flat"
        ? "Schablonersättning"
        : "Spotersättning";

  const lines: ExportRevenueBreakdown["lines"] = [
    {
      id: "spot",
      label: energySaleLabel,
      valueSek: totals.energySaleRevenueSek,
      quality: (spotFraction >= 0.99 ? "ACTUAL" : spotFraction > 0 ? "CALCULATED" : "ESTIMATED") as EconomyValueQuality,
      detail: weightedSpot != null ? `${(weightedSpot * 100).toFixed(1)} öre/kWh i snitt` : undefined,
    },
    {
      id: "grid-benefit",
      label: "Nätnytta",
      valueSek: totals.gridBenefitRevenueSek,
      quality: (totals.gridBenefitRevenueSek > 0 ? "CALCULATED" : "MISSING") as EconomyValueQuality,
    },
    {
      id: "tax-credit",
      label: "Skattereduktion",
      valueSek: totals.taxCreditSek,
      quality: (totals.taxCreditSek > 0 ? "CALCULATED" : "MISSING") as EconomyValueQuality,
    },
  ].filter((line) => line.id !== "tax-credit" || line.valueSek > 0.005);

  return {
    exportedKwh: totals.exportedKwh,
    weightedSpotPriceKrKwh: weightedSpot,
    energySaleRevenueSek: totals.energySaleRevenueSek,
    supplierAdjustmentSek: 0,
    gridBenefitRevenueSek: totals.gridBenefitRevenueSek,
    taxCreditSek: totals.taxCreditSek,
    totalExportRevenueSek: totals.exportRevenueSek,
    totalEconomicValueSek: totals.exportRevenueSek + totals.taxCreditSek,
    spotPricedFraction: spotFraction,
    showTaxCreditNotice,
    showPreContractExportNotice,
    preContractExportedKwh,
    sellContractStartDate,
    lines,
  };
}

export function filterStatsForMonth(stats: FinancialStat[], year: number, month: number): FinancialStat[] {
  const prefix = `${year}-${String(month).padStart(2, "0")}`;
  return stats.filter((stat) => stat.period_start.startsWith(prefix));
}

export function computeMetricChange(current: number, previous: number): EconomyMetricChange {
  const deltaSek = current - previous;
  if (Math.abs(previous) < 0.005) {
    return { value: current, previous, deltaSek, pct: null, direction: "flat" };
  }
  const pct = (deltaSek / Math.abs(previous)) * 100;
  return {
    value: current,
    previous,
    deltaSek,
    pct,
    direction: Math.abs(pct) < 0.5 ? "flat" : pct > 0 ? "up" : "down",
  };
}

/** Avoided purchase cost from self-consumed solar + battery (+ smart categories). */
export function computeAvoidedCostSavings(totals: EconomyTotals, smartChargingSek = 0): number {
  return totals.solarSavingsSek + totals.batterySavingsSek + smartChargingSek;
}

/** Full economic benefit: avoided cost + export revenue (no tax credit). */
export function computeEconomicBenefit(totals: EconomyTotals, smartChargingSek = 0): number {
  return computeAvoidedCostSavings(totals, smartChargingSek) + totals.exportRevenueSek;
}

/** Total economic value including historical tax credit (shown separately from net cost). */
export function computeTotalEconomicValue(totals: EconomyTotals, smartChargingSek = 0): number {
  return computeEconomicBenefit(totals, smartChargingSek) + totals.taxCreditSek;
}

/** @deprecated alias — use computeAvoidedCostSavings for KPI cards that exclude export */
export function computeTotalSavings(totals: EconomyTotals, smartChargingSek = 0): number {
  return computeEconomicBenefit(totals, smartChargingSek);
}

/** Net grid cost after export compensation: import cost − export revenue. */
export function computeNetCost(totals: EconomyTotals): number {
  return totals.gridImportCostSek - totals.exportRevenueSek;
}

export function computeYtdReturnPct(
  ytdEconomicBenefitSek: number,
  investmentSek: number | null,
): number | null {
  if (investmentSek == null || investmentSek <= 0) return null;
  return (ytdEconomicBenefitSek / investmentSek) * 100;
}

export function computePaybackMetrics(
  lifetimeBenefitSek: number,
  trailing12mBenefitSek: number,
  investmentSek: number | null,
): PaybackMetrics {
  if (investmentSek == null || investmentSek <= 0) {
    return {
      investmentSek: null,
      repaidSek: lifetimeBenefitSek,
      remainingSek: null,
      repaidPct: null,
      paybackYears: null,
      annualizedBenefitSek: trailing12mBenefitSek > 0 ? trailing12mBenefitSek : null,
      isForecast: true,
    };
  }
  const remaining = Math.max(0, investmentSek - lifetimeBenefitSek);
  const repaidPct = Math.min(100, (lifetimeBenefitSek / investmentSek) * 100);
  const annualized = trailing12mBenefitSek > 0 ? trailing12mBenefitSek : null;
  const paybackYears =
    annualized != null && annualized > 0 ? remaining / annualized : null;
  return {
    investmentSek,
    repaidSek: Math.min(lifetimeBenefitSek, investmentSek),
    remainingSek: remaining,
    repaidPct,
    paybackYears,
    annualizedBenefitSek: annualized,
    isForecast: annualized == null,
  };
}

export function buildEconomyMetrics(
  current: EconomyTotals,
  previous: EconomyTotals,
  ytdTotals: EconomyTotals,
  lifetimeTotals: EconomyTotals,
  investmentSek: number | null,
  smartChargingSek = 0,
): EconomyDisplayMetrics {
  const economicBenefitSek = computeEconomicBenefit(current, smartChargingSek);
  const prevBenefit = computeEconomicBenefit(previous, smartChargingSek);
  const netCostSek = computeNetCost(current);
  const prevNetCost = computeNetCost(previous);
  const ytdBenefit = computeEconomicBenefit(ytdTotals, smartChargingSek);

  return {
    totalSavingsSek: economicBenefitSek,
    avoidedCostSavingsSek: computeAvoidedCostSavings(current, smartChargingSek),
    economicBenefitSek,
    gridImportCostSek: current.gridImportCostSek,
    exportRevenueSek: current.exportRevenueSek,
    netCostSek,
    ytdReturnPct: computeYtdReturnPct(ytdBenefit, investmentSek),
    ytdEconomicBenefitSek: ytdBenefit,
    lifetimeEconomicBenefitSek: computeEconomicBenefit(lifetimeTotals, smartChargingSek),
    changes: {
      totalSavings: computeMetricChange(economicBenefitSek, prevBenefit),
      gridImportCost: computeMetricChange(current.gridImportCostSek, previous.gridImportCostSek),
      exportRevenue: computeMetricChange(current.exportRevenueSek, previous.exportRevenueSek),
      netCost: computeMetricChange(netCostSek, prevNetCost),
    },
  };
}

export function formatComparisonSubtext(
  change: EconomyMetricChange,
  periodLabel: string,
  options: { invertGood?: boolean; higherIsGood?: boolean } = {},
): string {
  if (!periodLabel) return "Ingen jämförelse tillgänglig";
  if (Math.abs(change.previous) < 0.005 && Math.abs(change.value) < 0.005) {
    return `Ingen data ${periodLabel.toLowerCase()}`;
  }
  if (change.pct == null) {
    if (Math.abs(change.deltaSek) < 0.5) return `Oförändrat ${periodLabel.toLowerCase()}`;
    const dir = change.deltaSek > 0 ? "högre" : "lägre";
    return `${formatEconomyKr(Math.abs(change.deltaSek))} ${dir} ${periodLabel.toLowerCase()}`;
  }

  const pctAbs = Math.abs(Math.round(change.pct));
  const arrow = change.pct >= 0 ? "↑" : "↓";
  const deltaAbs = Math.abs(Math.round(change.deltaSek));
  const deltaDir = change.deltaSek >= 0 ? "högre" : "lägre";
  const higherIsGood = options.higherIsGood ?? !options.invertGood;
  const isGood =
    change.direction === "flat"
      ? true
      : higherIsGood
        ? change.deltaSek >= 0
        : change.deltaSek <= 0;

  void isGood;
  return `${arrow} ${pctAbs} % · ${formatEconomyKr(deltaAbs)} ${deltaDir} ${periodLabel.toLowerCase()}`;
}

export function formatMetricValue(
  amountSek: number | null | undefined,
  options: { allowZero?: boolean } = {},
): string {
  if (amountSek == null || !Number.isFinite(amountSek)) return "Data saknas";
  if (!options.allowZero && Math.abs(amountSek) < 0.005) return "Data saknas";
  return formatEconomyKr(amountSek);
}

export function formatReturnPct(pct: number | null): string {
  if (pct == null || !Number.isFinite(pct)) return "Investering ej angiven";
  return `${pct.toFixed(1)} %`;
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
    const dateObj = new Date(stat.period_start);
    const dayLabel = dateObj.toLocaleDateString("sv-SE", { day: "numeric", month: "long" });
    const effectivePriceKrKwh =
      stat.imported_kwh > 0 ? importCost / stat.imported_kwh : null;
    return {
      date: stat.period_start,
      label: `${day}/${month}`,
      dayLabel,
      purchasedSek,
      gridFeeSek,
      taxSek,
      soldSek: -soldSek,
      netSek,
      importedKwh: stat.imported_kwh,
      exportedKwh: stat.exported_kwh,
      effectivePriceKrKwh,
    };
  });
}
/** Convert SEK/kWh to whole öre/kWh for display. */
export function marketPriceToOre(sekKwh: number): number {
  return sekKwhToOre(sekKwh);
}

export function formatPriceOre(value: number | null): string {
  return value == null ? "—" : `${value} öre/kWh`;
}

function averagePrice(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function localDayKey(iso: string, timezone: string): string {
  return new Date(iso).toLocaleDateString("sv-SE", { timeZone: timezone });
}

function formatPriceTimestamp(iso: string | null, timezone: string): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleString("sv-SE", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

export function buildPriceAnalysis(
  marketPrices: MarketPricesResponse | null,
  exportPriceSekKwh: number,
  timezone: string,
  now = new Date(),
): PriceAnalysis {
  const allPoints = marketPrices?.points ?? [];
  const todayKey = now.toLocaleDateString("sv-SE", { timeZone: timezone });
  const todayPoints = allPoints.filter((point) => localDayKey(point.timestamp, timezone) === todayKey);
  const points = todayPoints.length > 0 ? todayPoints : allPoints;

  const spotValues = points
    .map((point) => marketPointSpotSek(point))
    .filter((value): value is number => value != null);
  const importValues = points
    .map((point) => marketPointImportSek(point))
    .filter((value): value is number => value != null);

  let cheapest: MarketPricePoint | null = null;
  let expensive: MarketPricePoint | null = null;
  for (const point of points) {
    const price = marketPointImportSek(point);
    if (price == null) continue;
    if (!cheapest || price < (marketPointImportSek(cheapest) ?? Number.POSITIVE_INFINITY)) {
      cheapest = point;
    }
    if (!expensive || price > (marketPointImportSek(expensive) ?? Number.NEGATIVE_INFINITY)) {
      expensive = point;
    }
  }

  const spotAverage = averagePrice(spotValues);
  const purchaseAverage =
    averagePrice(importValues) ?? marketPrices?.average_import_sek_kwh ?? null;
  const cheapestPrice =
    cheapest != null
      ? marketPointImportSek(cheapest)
      : marketPrices?.lowest_import_sek_kwh ?? null;
  const expensivePrice =
    expensive != null
      ? marketPointImportSek(expensive)
      : marketPrices?.highest_import_sek_kwh ?? null;

  return {
    spotOre: spotAverage != null ? sekKwhToOre(spotAverage) : null,
    purchaseOre: purchaseAverage != null ? sekKwhToOre(purchaseAverage) : null,
    exportOre: Number.isFinite(exportPriceSekKwh) ? sekKwhToOre(exportPriceSekKwh) : null,
    cheapestOre: cheapestPrice != null ? sekKwhToOre(cheapestPrice) : null,
    cheapestAt: formatPriceTimestamp(cheapest?.timestamp ?? null, timezone),
    expensiveOre: expensivePrice != null ? sekKwhToOre(expensivePrice) : null,
    expensiveAt: formatPriceTimestamp(expensive?.timestamp ?? null, timezone),
  };
}

export interface SavingsBreakdownItem {
  id: string;
  label: string;
  amountSek: number;
  pct: number;
  color: string;
  description: string;
  quality: EconomyValueQuality;
}

export const SAVINGS_BREAKDOWN_META = [
  {
    id: "solar",
    label: "Egenanvänd solel",
    color: "#4ade80",
    description: "Solenergi som använts i huset istället för köpt el.",
    quality: "CALCULATED" as EconomyValueQuality,
  },
  {
    id: "battery",
    label: "Batterioptimering",
    color: "#38bdf8",
    description: "Besparing när lagrad el ersätter dyr nätimport.",
    quality: "CALCULATED" as EconomyValueQuality,
  },
  {
    id: "export",
    label: "Såld el",
    color: "#a78bfa",
    description: "Intäkt från el som matats ut på nätet.",
    quality: "CALCULATED" as EconomyValueQuality,
  },
  {
    id: "ev",
    label: "EV-laddningsoptimering",
    color: "#fb923c",
    description: "Besparing från laddning vid låga elpriser.",
    quality: "MISSING" as EconomyValueQuality,
  },
] as const;

export function buildSavingsBreakdown(
  totals: EconomyTotals,
  smartChargingSek = 0,
): SavingsBreakdownItem[] {
  const amounts: Record<(typeof SAVINGS_BREAKDOWN_META)[number]["id"], number> = {
    solar: totals.solarSavingsSek,
    battery: totals.batterySavingsSek,
    export: totals.exportRevenueSek,
    ev: smartChargingSek,
  };
  const visible = SAVINGS_BREAKDOWN_META.filter((meta) => {
    if (meta.id === "ev") return smartChargingSek > 0;
    return amounts[meta.id] > 0.005;
  });
  const total = visible.reduce((sum, meta) => sum + amounts[meta.id], 0) || 1;
  return visible.map((meta) => ({
    ...meta,
    amountSek: amounts[meta.id],
    pct: (amounts[meta.id] / total) * 100,
    quality: meta.id === "ev" && smartChargingSek > 0 ? "ESTIMATED" : meta.quality,
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

export function buildCostReductionGoal(
  current: EconomyTotals,
  previous: EconomyTotals | null,
  comparisonLabel: string,
): EconomyGoal {
  if (!previous || previous.gridImportCostSek <= 0) {
    const budgetPct =
      current.gridImportCostSek > 0 && DEFAULT_MONTHLY_BUDGET_SEK > 0
        ? Math.min(100, (current.gridImportCostSek / DEFAULT_MONTHLY_BUDGET_SEK) * 100)
        : 0;
    return {
      id: "cost",
      label: "Minska elkostnad",
      targetLabel: comparisonLabel || "Kräver jämförelseperiod",
      valuePct: budgetPct,
      displayValue:
        current.gridImportCostSek > 0
          ? `${formatEconomyKr(current.gridImportCostSek)} i perioden`
          : "Data saknas",
      tone: "orange",
    };
  }

  const change = computeMetricChange(current.gridImportCostSek, previous.gridImportCostSek);
  const lowerIsBetter = change.deltaSek <= 0;
  const barPct =
    change.pct != null
      ? Math.min(100, Math.max(4, Math.abs(change.pct)))
      : Math.abs(change.deltaSek) >= 0.5
        ? 8
        : 0;

  let displayValue = "Oförändrat";
  if (change.pct != null) {
    const arrow = change.pct <= 0 ? "↓" : "↑";
    displayValue = `${arrow} ${Math.abs(Math.round(change.pct))} % · ${formatEconomyKr(Math.abs(Math.round(change.deltaSek)))} ${change.deltaSek <= 0 ? "lägre" : "högre"}`;
  } else if (Math.abs(change.deltaSek) >= 0.5) {
    displayValue = formatComparisonSubtext(change, comparisonLabel, { higherIsGood: false, invertGood: true });
  }

  return {
    id: "cost",
    label: "Minska elkostnad",
    targetLabel: comparisonLabel,
    valuePct: barPct,
    displayValue,
    tone: change.direction === "flat" ? "orange" : lowerIsBetter ? "green" : "warn",
  };
}

export function buildEconomyGoals(
  totals: EconomyTotals,
  previousTotals: EconomyTotals | null,
  comparisonLabel = "Föregående period",
): EconomyGoal[] {
  const selfUseKwh = totals.solarSelfConsumedKwh + totals.batterySelfConsumedKwh;
  const producedKwh = selfUseKwh + totals.exportedKwh;
  const selfUsePct = producedKwh > 0 ? (selfUseKwh / producedKwh) * 100 : 0;
  const exportSharePct = producedKwh > 0 ? (totals.exportedKwh / producedKwh) * 100 : 0;
  const co2Kg = Math.round(selfUseKwh * 0.4);

  return [
    buildCostReductionGoal(totals, previousTotals, comparisonLabel),
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

  const peakImportDay = dailyStats.reduce<FinancialStat | null>((best, current) => {
    if (current.grid_import_cost_sek <= 0) return best;
    if (!best || current.grid_import_cost_sek > best.grid_import_cost_sek) return current;
    return best;
  }, null);

  const insights: EconomyInsight[] = [];

  if (peakImportDay && peakImportDay.grid_import_cost_sek > 0) {
    const peakLabel = new Date(peakImportDay.period_start).toLocaleDateString("sv-SE", {
      day: "numeric",
      month: "short",
    });
    insights.push({
      id: "peak",
      text: `Högsta elkostnad: ${peakLabel} (${formatEconomyKr(peakImportDay.grid_import_cost_sek)}).`,
    });
  }

  insights.push({
    id: "selfuse",
    text: `${selfUsePct}% av solenergin användes själv eller lagrades.`,
  });

  if (totals.batterySavingsSek > 0) {
    insights.push({
      id: "battery",
      text: `Batteriet bidrog med ${formatEconomyKr(totals.batterySavingsSek)} i besparing.`,
    });
  }
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
