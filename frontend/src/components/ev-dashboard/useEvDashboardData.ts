"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ENERGY_BALANCE_HISTORY_MAX_LIMIT,
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
import { useOptionalSiteData } from "@/lib/SiteDataProvider";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";
import {
  buildEnergyMixSlices,
  buildHourlySourceChart,
  buildPlanWindows,
  buildPowerChartFromHistory,
  buildSavingsChart,
  computeCo2SavedKg,
  averageChargingPowerKw,
  maxPowerTodayKw,
  type EvStatsPeriod,
} from "./evDashboardHelpers";

export function useEvDashboardData(siteSlug: string, statsPeriod: EvStatsPeriod = "day") {
  const refreshSeconds = useDashboardRefreshSeconds();
  const shared = useOptionalSiteData();
  const [dashboard, setDashboard] = useState<SiteDashboard | null>(shared?.dashboard ?? null);
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
  const [secondaryLoading, setSecondaryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (shared?.dashboard) {
      setDashboard(shared.dashboard);
    }
  }, [shared?.dashboard]);

  const loadSecondary = useCallback(
    async (primary: EvCharger, dash: SiteDashboard | null) => {
      setSecondaryLoading(true);
      try {
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
          fetchEnergyBalanceHistory(siteSlug, primary.id, ENERGY_BALANCE_HISTORY_MAX_LIMIT, 0).catch(
            (err) => {
              console.warn("EV balance history unavailable", err);
              return { items: [], total: 0 };
            },
          ),
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
        if (dash) setDashboard(dash);
      } finally {
        setSecondaryLoading(false);
      }
    },
    [siteSlug, statsPeriod],
  );

  const reload = useCallback(async () => {
    try {
      const dashboardPromise = shared?.dashboard
        ? Promise.resolve(shared.dashboard)
        : fetchSiteDashboard(siteSlug).catch(() => null);

      const [dash, config, chargerList] = await Promise.all([
        dashboardPromise,
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

      await loadSecondary(primary, dash);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte ladda laddboxdata.");
    } finally {
      setLoading(false);
    }
  }, [loadSecondary, shared?.dashboard, siteSlug]);

  useEffect(() => {
    reload();
    const interval = setInterval(reload, refreshSeconds * 1000);
    return () => clearInterval(interval);
  }, [reload, refreshSeconds]);

  const powerChart = useMemo(() => buildPowerChartFromHistory(balanceItems), [balanceItems]);
  const maxPowerKw = useMemo(() => maxPowerTodayKw(balanceItems), [balanceItems]);
  const avgPowerKw = useMemo(() => averageChargingPowerKw(balanceItems), [balanceItems]);
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
    avgPowerKw,
    energyMix,
    hourlySources,
    savingsChart,
    planWindows,
    co2SavedKg,
    vehicleLabel,
    loading: loading || secondaryLoading,
    error,
    refreshSeconds,
    reload,
    setCharger,
  };
}
