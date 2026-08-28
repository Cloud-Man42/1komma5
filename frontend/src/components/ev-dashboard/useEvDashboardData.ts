"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchEnergyBalanceHistory,
  fetchEnergyReasoning,
  fetchEvBridgeStatus,
  fetchEvChargerSavings,
  fetchEvChargers,
  fetchEvChargingSessions,
  fetchEvChargingStats,
  fetchEvSolarChargingPlan,
  fetchSiteDashboard,
  fetchSiteEnergyConfig,
  type EnergyReasoning,
  type EvBridgeStatus,
  type EvCharger,
  type EvChargingSavings,
  type EvChargingSession,
  type EvChargingStats,
  type EvSolarChargingPlan,
  type SiteDashboard,
} from "@/lib/api";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";
import {
  buildEnergyMixSlices,
  buildHourlySourceChart,
  buildPlanWindows,
  buildPowerChartFromHistory,
  buildSavingsChart,
  computeCo2SavedKg,
  maxPowerTodayKw,
  type EvStatsPeriod,
} from "./evDashboardHelpers";

export function useEvDashboardData(siteSlug: string, statsPeriod: EvStatsPeriod = "day") {
  const refreshSeconds = useDashboardRefreshSeconds();
  const [dashboard, setDashboard] = useState<SiteDashboard | null>(null);
  const [energyConfig, setEnergyConfig] = useState<{ ev_vehicle_label: string } | null>(null);
  const [chargers, setChargers] = useState<EvCharger[]>([]);
  const [charger, setCharger] = useState<EvCharger | null>(null);
  const [bridge, setBridge] = useState<EvBridgeStatus | null>(null);
  const [plan, setPlan] = useState<EvSolarChargingPlan | null>(null);
  const [reasoning, setReasoning] = useState<EnergyReasoning | null>(null);
  const [savings, setSavings] = useState<EvChargingSavings | null>(null);
  const [dayStats, setDayStats] = useState<EvChargingStats | null>(null);
  const [periodStats, setPeriodStats] = useState<EvChargingStats | null>(null);
  const [monthStats, setMonthStats] = useState<EvChargingStats | null>(null);
  const [sessions, setSessions] = useState<EvChargingSession[]>([]);
  const [balanceItems, setBalanceItems] = useState<Awaited<ReturnType<typeof fetchEnergyBalanceHistory>>["items"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [dash, config, chargerList] = await Promise.all([
        fetchSiteDashboard(siteSlug).catch(() => null),
        fetchSiteEnergyConfig(siteSlug).catch(() => null),
        fetchEvChargers(siteSlug),
      ]);
      setDashboard(dash);
      setEnergyConfig(config ? { ev_vehicle_label: config.ev_vehicle_label } : null);
      setChargers(chargerList);
      const primary = chargerList[0] ?? null;
      setCharger(primary);
      if (!primary) {
        setError(null);
        setLoading(false);
        return;
      }

      const [
        bridgeStatus,
        solarPlan,
        energyReasoning,
        savingsData,
        statsDay,
        statsPeriodData,
        statsMonth,
        sessionList,
        balanceHistory,
      ] = await Promise.all([
        fetchEvBridgeStatus(siteSlug, primary.id).catch(() => null),
        fetchEvSolarChargingPlan(siteSlug, primary.id).catch(() => null),
        fetchEnergyReasoning(siteSlug, primary.id).catch(() => null),
        fetchEvChargerSavings(siteSlug, primary.id, 30).catch(() => null),
        fetchEvChargingStats(siteSlug, primary.id, "day").catch(() => null),
        fetchEvChargingStats(siteSlug, primary.id, statsPeriod).catch(() => null),
        fetchEvChargingStats(siteSlug, primary.id, "month").catch(() => null),
        fetchEvChargingSessions(siteSlug, primary.id, 20).catch(() => []),
        fetchEnergyBalanceHistory(siteSlug, primary.id, 288, 0).catch(() => ({ items: [], total: 0 })),
      ]);

      setBridge(bridgeStatus);
      setPlan(solarPlan);
      setReasoning(energyReasoning);
      setSavings(savingsData);
      setDayStats(statsDay);
      setPeriodStats(statsPeriodData);
      setMonthStats(statsMonth);
      setSessions(sessionList);
      setBalanceItems(balanceHistory.items);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte ladda laddboxdata.");
    } finally {
      setLoading(false);
    }
  }, [siteSlug, statsPeriod]);

  useEffect(() => {
    reload();
    const interval = setInterval(reload, refreshSeconds * 1000);
    return () => clearInterval(interval);
  }, [reload, refreshSeconds]);

  const powerChart = useMemo(() => buildPowerChartFromHistory(balanceItems), [balanceItems]);
  const maxPowerKw = useMemo(() => maxPowerTodayKw(balanceItems), [balanceItems]);
  const energyMix = useMemo(() => buildEnergyMixSlices(dayStats), [dayStats]);
  const hourlySources = useMemo(() => buildHourlySourceChart(sessions), [sessions]);
  const savingsChart = useMemo(() => buildSavingsChart(sessions), [sessions]);
  const planWindows = useMemo(() => buildPlanWindows(plan, reasoning), [plan, reasoning]);
  const co2SavedKg = useMemo(() => computeCo2SavedKg(monthStats), [monthStats]);

  const vehicleLabel =
    reasoning?.vehicle_display_name ?? energyConfig?.ev_vehicle_label ?? "—";

  return {
    dashboard,
    chargers,
    charger,
    bridge,
    plan,
    reasoning,
    savings,
    dayStats,
    periodStats,
    monthStats,
    sessions,
    powerChart,
    maxPowerKw,
    energyMix,
    hourlySources,
    savingsChart,
    planWindows,
    co2SavedKg,
    vehicleLabel,
    loading,
    error,
    refreshSeconds,
    reload,
    setCharger,
  };
}
