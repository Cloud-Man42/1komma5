"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchFinancialStats,
  fetchMarketPrices,
  fetchSiteDashboard,
  fetchYearForecast,
  type FinancialStatsResponse,
  type MarketPricesResponse,
  type SiteDashboard,
  type YearForecastResponse,
} from "@/lib/api";
import { useOptionalSiteData } from "@/lib/SiteDataProvider";
import {
  aggregateFinancialStats,
  buildDailyCostSeries,
  buildEconomyGoals,
  buildEconomyInsights,
  buildExtendedEconomyInsights,
  buildEconomyMetrics,
  buildCostBreakdown,
  buildExportRevenueBreakdown,
  buildPriceAnalysis,
  buildSavingsBreakdown,
  computeEconomicBenefit,
  computePaybackMetrics,
  DEFAULT_MONTHLY_BUDGET_SEK,
  forecastMonthCost,
  resolveSiteInvestmentSek,
  type EconomyDisplayMetrics,
  type PaybackMetrics,
} from "./economyDashboardHelpers";
import {
  comparisonPeriodLabel,
  filterStatsByDateRange,
  filterStatsForPeriod,
  resolveComparisonRange,
  resolvePeriodRange,
  type EconomyCompareMode,
  type EconomyPeriodId,
} from "./economyPeriods";

export function useEconomyDashboardData(
  siteSlug: string,
  period: EconomyPeriodId = "this-month",
  compareMode: EconomyCompareMode = "previous-period",
) {
  const shared = useOptionalSiteData();
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  const [dashboard, setDashboard] = useState<SiteDashboard | null>(shared?.dashboard ?? null);
  const [dailyStats, setDailyStats] = useState<FinancialStatsResponse | null>(null);
  const [forecast, setForecast] = useState<YearForecastResponse | null>(null);
  const [marketPrices, setMarketPrices] = useState<MarketPricesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (shared?.dashboard) {
      setDashboard(shared.dashboard);
    }
  }, [shared?.dashboard]);

  const reload = useCallback(async () => {
    setLoading(true);
    const dashboardPromise = shared?.dashboard
      ? Promise.resolve(shared.dashboard)
      : fetchSiteDashboard(siteSlug).catch(() => null);

    try {
      const dash = await dashboardPromise;
      const timezone = dash?.site.timezone ?? "Europe/Stockholm";
      const [stats, yearForecast, prices] = await Promise.all([
        fetchFinancialStats(siteSlug, "day"),
        fetchYearForecast(siteSlug, currentYear).catch(() => null),
        fetchMarketPrices(siteSlug, 24, timezone).catch(() => null),
      ]);
      setDashboard(dash);
      setDailyStats(stats);
      setForecast(yearForecast);
      setMarketPrices(prices);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte ladda ekonomidata.");
    } finally {
      setLoading(false);
    }
  }, [currentYear, shared?.dashboard, siteSlug]);

  useEffect(() => {
    reload();
  }, [reload]);

  const allStats = dailyStats?.stats ?? [];
  const periodRange = useMemo(() => resolvePeriodRange(period, now), [period, now]);
  const comparisonRange = useMemo(
    () => resolveComparisonRange(period, compareMode, now),
    [compareMode, period, now],
  );
  const comparisonLabel = useMemo(
    () => comparisonPeriodLabel(period, compareMode),
    [compareMode, period],
  );

  const periodStats = useMemo(
    () => filterStatsForPeriod(allStats, period, now),
    [allStats, period, now],
  );
  const comparisonStats = useMemo(() => {
    if (!comparisonRange) return [];
    return filterStatsByDateRange(allStats, comparisonRange.from, comparisonRange.to);
  }, [allStats, comparisonRange]);

  const currentTotals = useMemo(() => aggregateFinancialStats(periodStats), [periodStats]);
  const previousTotals = useMemo(() => aggregateFinancialStats(comparisonStats), [comparisonStats]);

  const ytdStats = useMemo(
    () => filterStatsForPeriod(allStats, "ytd", now),
    [allStats, now],
  );
  const ytdTotals = useMemo(() => aggregateFinancialStats(ytdStats), [ytdStats]);
  const lifetimeTotals = useMemo(() => aggregateFinancialStats(allStats), [allStats]);
  const trailing12mStats = useMemo(
    () => filterStatsForPeriod(allStats, "12m", now),
    [allStats, now],
  );
  const trailing12mTotals = useMemo(
    () => aggregateFinancialStats(trailing12mStats),
    [trailing12mStats],
  );

  const smartChargingSek = 0;
  const investmentSek = resolveSiteInvestmentSek(siteSlug);

  const metrics: EconomyDisplayMetrics = useMemo(
    () =>
      buildEconomyMetrics(
        currentTotals,
        previousTotals,
        ytdTotals,
        lifetimeTotals,
        investmentSek,
        smartChargingSek,
      ),
    [currentTotals, investmentSek, lifetimeTotals, previousTotals, smartChargingSek, ytdTotals],
  );

  const payback: PaybackMetrics = useMemo(
    () =>
      computePaybackMetrics(
        metrics.lifetimeEconomicBenefitSek,
        computeEconomicBenefit(trailing12mTotals, smartChargingSek),
        investmentSek,
      ),
    [investmentSek, metrics.lifetimeEconomicBenefitSek, smartChargingSek, trailing12mTotals],
  );

  const costBreakdown = useMemo(
    () => buildCostBreakdown(currentTotals.gridImportCostSek),
    [currentTotals.gridImportCostSek],
  );
  const dailySeries = useMemo(() => buildDailyCostSeries(periodStats), [periodStats]);
  const savingsBreakdown = useMemo(
    () => buildSavingsBreakdown(currentTotals, smartChargingSek),
    [currentTotals, smartChargingSek],
  );
  const exportBreakdown = useMemo(
    () =>
      buildExportRevenueBreakdown(
        currentTotals,
        periodStats,
        now,
        dailyStats?.sell_pricing_mode ?? "spot",
        dailyStats?.sell_contract_start_date ?? null,
      ),
    [currentTotals, dailyStats?.sell_contract_start_date, dailyStats?.sell_pricing_mode, periodStats, now],
  );
  const goals = useMemo(
    () => buildEconomyGoals(currentTotals, comparisonRange ? previousTotals : null, comparisonLabel),
    [comparisonLabel, comparisonRange, currentTotals, previousTotals],
  );
  const insights = useMemo(
    () => buildEconomyInsights(currentTotals, periodStats, smartChargingSek),
    [currentTotals, periodStats, smartChargingSek],
  );
  const extendedInsights = useMemo(
    () => buildExtendedEconomyInsights(currentTotals, periodStats, smartChargingSek),
    [currentTotals, periodStats, smartChargingSek],
  );

  const purchasePrice = dailyStats?.fallback_purchase_price_sek_kwh ?? 0.58;
  const exportPrice = dailyStats?.export_compensation_sek_kwh ?? 0.29;
  const timezone = dailyStats?.timezone ?? dashboard?.site.timezone ?? "Europe/Stockholm";

  const priceAnalysis = useMemo(
    () => buildPriceAnalysis(marketPrices, exportPrice, timezone),
    [exportPrice, marketPrices, timezone],
  );

  const monthlyBudgetSek = DEFAULT_MONTHLY_BUDGET_SEK;
  const budgetUsedPct =
    monthlyBudgetSek > 0 ? Math.min(100, (currentTotals.gridImportCostSek / monthlyBudgetSek) * 100) : 0;
  const forecastCost =
    forecastMonthCost(forecast, currentYear, currentMonth) ??
    currentTotals.gridImportCostSek * 1.12;
  const forecastDelta = forecastCost - monthlyBudgetSek;
  const forecastDeltaPct = monthlyBudgetSek > 0 ? (forecastDelta / monthlyBudgetSek) * 100 : 0;

  const averagePriceOre = priceAnalysis.purchaseOre ?? Math.round(purchasePrice * 100);
  const avgMarketPricedFraction =
    periodStats.length > 0
      ? periodStats.reduce((sum, stat) => sum + stat.market_priced_fraction, 0) / periodStats.length
      : 0;

  return {
    loading,
    error,
    reload,
    dashboard,
    dailyStats,
    allStats,
    periodStats,
    comparisonStats,
    periodRange,
    comparisonLabel,
    currentTotals,
    previousTotals,
    metrics,
    payback,
    costBreakdown,
    dailySeries,
    savingsBreakdown,
    exportBreakdown,
    goals,
    insights,
    extendedInsights,
    priceAnalysis,
    marketPrices,
    averagePriceOre,
    avgMarketPricedFraction,
    timezone,
    currentYear,
    currentMonth,
    monthlyBudgetSek,
    budgetUsedPct,
    forecastCost,
    forecastDelta,
    forecastDeltaPct,
    investmentSek,
    ytdReturnPct: metrics.ytdReturnPct,
    refreshSeconds: 60,
  };
}
