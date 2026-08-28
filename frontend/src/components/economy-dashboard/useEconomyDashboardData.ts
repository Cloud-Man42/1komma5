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
import {
  aggregateFinancialStats,
  buildDailyCostSeries,
  buildEconomyGoals,
  buildEconomyInsights,
  buildExtendedEconomyInsights,
  buildEconomyMetrics,
  buildCostBreakdown,
  buildPriceAnalysis,
  buildSavingsBreakdown,
  DEFAULT_MONTHLY_BUDGET_SEK,
  filterStatsForMonth,
  forecastMonthCost,
  resolveSiteInvestmentSek,
  type EconomyDisplayMetrics,
} from "./economyDashboardHelpers";

export function useEconomyDashboardData(siteSlug: string) {
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  const previousMonthDate = new Date(currentYear, currentMonth - 2, 1);
  const previousYear = previousMonthDate.getFullYear();
  const previousMonth = previousMonthDate.getMonth() + 1;

  const [dashboard, setDashboard] = useState<SiteDashboard | null>(null);
  const [dailyStats, setDailyStats] = useState<FinancialStatsResponse | null>(null);
  const [forecast, setForecast] = useState<YearForecastResponse | null>(null);
  const [marketPrices, setMarketPrices] = useState<MarketPricesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, stats, yearForecast, prices] = await Promise.all([
        fetchSiteDashboard(siteSlug).catch(() => null),
        fetchFinancialStats(siteSlug, "day", currentYear),
        fetchYearForecast(siteSlug, currentYear).catch(() => null),
        fetchMarketPrices(siteSlug, 24 * 31).catch(() => null),
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
  }, [currentYear, siteSlug]);

  useEffect(() => {
    reload();
  }, [reload]);

  const currentMonthStats = useMemo(
    () => filterStatsForMonth(dailyStats?.stats ?? [], currentYear, currentMonth),
    [currentMonth, currentYear, dailyStats],
  );
  const previousMonthStats = useMemo(
    () => filterStatsForMonth(dailyStats?.stats ?? [], previousYear, previousMonth),
    [dailyStats, previousMonth, previousYear],
  );

  const currentTotals = useMemo(() => aggregateFinancialStats(currentMonthStats), [currentMonthStats]);
  const previousTotals = useMemo(() => aggregateFinancialStats(previousMonthStats), [previousMonthStats]);

  const ytdStats = useMemo(
    () => filterStatsForMonth(dailyStats?.stats ?? [], currentYear, 1).concat(currentMonthStats),
    [currentMonthStats, currentYear, dailyStats],
  );
  const ytdTotals = useMemo(() => {
    const allYtd = (dailyStats?.stats ?? []).filter((s) => s.period_start.startsWith(String(currentYear)));
    return aggregateFinancialStats(allYtd);
  }, [currentYear, dailyStats]);

  const smartChargingSek = 0;

  const metrics: EconomyDisplayMetrics = useMemo(
    () =>
      buildEconomyMetrics(
        currentTotals,
        previousTotals,
        ytdTotals.solarSavingsSek + ytdTotals.batterySavingsSek,
        smartChargingSek,
      ),
    [currentTotals, previousTotals, smartChargingSek, ytdTotals],
  );

  const costBreakdown = useMemo(
    () => buildCostBreakdown(currentTotals.gridImportCostSek),
    [currentTotals.gridImportCostSek],
  );
  const dailySeries = useMemo(() => buildDailyCostSeries(currentMonthStats), [currentMonthStats]);
  const savingsBreakdown = useMemo(
    () => buildSavingsBreakdown(currentTotals, smartChargingSek),
    [currentTotals, smartChargingSek],
  );
  const goals = useMemo(() => buildEconomyGoals(currentTotals), [currentTotals]);
  const insights = useMemo(
    () => buildEconomyInsights(currentTotals, currentMonthStats, smartChargingSek),
    [currentMonthStats, currentTotals, smartChargingSek],
  );
  const extendedInsights = useMemo(
    () => buildExtendedEconomyInsights(currentTotals, currentMonthStats, smartChargingSek),
    [currentMonthStats, currentTotals, smartChargingSek],
  );

  const purchasePrice = dailyStats?.fallback_purchase_price_sek_kwh ?? 0.58;
  const exportPrice = dailyStats?.export_compensation_sek_kwh ?? 0.29;
  const timezone = dailyStats?.timezone ?? dashboard?.site.timezone ?? "Europe/Stockholm";

  const priceAnalysis = useMemo(
    () =>
      buildPriceAnalysis(
        marketPrices?.points ?? [],
        purchasePrice,
        exportPrice,
        timezone,
      ),
    [exportPrice, marketPrices, purchasePrice, timezone],
  );

  const monthlyBudgetSek = DEFAULT_MONTHLY_BUDGET_SEK;
  const budgetUsedPct =
    monthlyBudgetSek > 0 ? Math.min(100, (currentTotals.gridImportCostSek / monthlyBudgetSek) * 100) : 0;
  const forecastCost =
    forecastMonthCost(forecast, currentYear, currentMonth) ??
    currentTotals.gridImportCostSek * 1.12;
  const forecastDelta = forecastCost - monthlyBudgetSek;
  const forecastDeltaPct = monthlyBudgetSek > 0 ? (forecastDelta / monthlyBudgetSek) * 100 : 0;

  const investmentSek = resolveSiteInvestmentSek(siteSlug);
  const expectedAnnualSaving =
    (forecast?.total.solar_savings_sek ?? 0) +
    (forecast?.total.battery_savings_sek ?? 0) +
    (forecast?.total.export_revenue_sek ?? 0);
  const paybackYears = expectedAnnualSaving > 0 ? investmentSek / expectedAnnualSaving : 0;

  const averagePriceOre = Math.round(purchasePrice * 100);

  return {
    loading,
    error,
    reload,
    dashboard,
    dailyStats,
    currentMonthStats,
    previousMonthStats,
    currentTotals,
    metrics,
    costBreakdown,
    dailySeries,
    savingsBreakdown,
    goals,
    insights,
    extendedInsights,
    priceAnalysis,
    marketPrices,
    averagePriceOre,
    timezone,
    currentYear,
    currentMonth,
    monthlyBudgetSek,
    budgetUsedPct,
    forecastCost,
    forecastDelta,
    forecastDeltaPct,
    investmentSek,
    expectedAnnualSaving,
    paybackYears,
    ytdReturnPct: metrics.ytdReturnPct,
    refreshSeconds: 60,
  };
}
