"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchSpaControlConfig,
  fetchSpaEconomics,
  fetchSpaEnergyPeriod,
  fetchSpaHealth,
  fetchSpaHistory,
  fetchSpaPlan,
  fetchSpaStatus,
  type SpaControlConfig,
  type SpaEconomics,
  type SpaEnergyPeriod,
  type SpaHealth,
  type SpaHistory,
  type SpaPlan,
  type SpaStatus,
} from "@/lib/api";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

export interface SpaDashboardData {
  status: SpaStatus | null;
  today: SpaEnergyPeriod | null;
  month: SpaEnergyPeriod | null;
  total: SpaEnergyPeriod | null;
  plan: SpaPlan | null;
  control: SpaControlConfig | null;
  history24h: SpaHistory | null;
  historyToday: SpaHistory | null;
  economics: SpaEconomics | null;
  health: SpaHealth | null;
  loading: boolean;
  error: string | null;
  lastLoadedAt: number | null;
  reload: () => Promise<void>;
}

export function useSpaDashboardData(siteSlug: string): SpaDashboardData {
  const [status, setStatus] = useState<SpaStatus | null>(null);
  const [today, setToday] = useState<SpaEnergyPeriod | null>(null);
  const [month, setMonth] = useState<SpaEnergyPeriod | null>(null);
  const [total, setTotal] = useState<SpaEnergyPeriod | null>(null);
  const [plan, setPlan] = useState<SpaPlan | null>(null);
  const [control, setControl] = useState<SpaControlConfig | null>(null);
  const [history24h, setHistory24h] = useState<SpaHistory | null>(null);
  const [historyToday, setHistoryToday] = useState<SpaHistory | null>(null);
  const [economics, setEconomics] = useState<SpaEconomics | null>(null);
  const [health, setHealth] = useState<SpaHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastLoadedAt, setLastLoadedAt] = useState<number | null>(null);
  const refreshSeconds = useDashboardRefreshSeconds();

  const load = useCallback(async () => {
    try {
      const [spaStatus, spaToday, spaMonth, spaTotal, spaPlan, spaControl, histDay, histToday, spaEco, spaHealth] =
        await Promise.all([
          fetchSpaStatus(siteSlug),
          fetchSpaEnergyPeriod(siteSlug, "today"),
          fetchSpaEnergyPeriod(siteSlug, "month"),
          fetchSpaEnergyPeriod(siteSlug, "total"),
          fetchSpaPlan(siteSlug).catch(() => null),
          fetchSpaControlConfig(siteSlug).catch(() => null),
          fetchSpaHistory(siteSlug, "24h").catch(() => ({ period: "24h", points: [] })),
          fetchSpaHistory(siteSlug, "today").catch(() => ({ period: "today", points: [] })),
          fetchSpaEconomics(siteSlug, "month").catch(() => null),
          fetchSpaHealth(siteSlug).catch(() => null),
        ]);

      setStatus(spaStatus);
      setToday(spaToday);
      setMonth(spaMonth);
      setTotal(spaTotal);
      setPlan(spaPlan);
      setControl(spaControl);
      setHistory24h(histDay);
      setHistoryToday(histToday.points.length > 0 ? histToday : histDay);
      setEconomics(spaEco);
      setHealth(spaHealth);
      setError(null);
      setLastLoadedAt(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda spa");
    } finally {
      setLoading(false);
    }
  }, [siteSlug]);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), refreshSeconds * 1000);
    return () => clearInterval(timer);
  }, [load, refreshSeconds]);

  return {
    status,
    today,
    month,
    total,
    plan,
    control,
    history24h,
    historyToday,
    economics,
    health,
    loading,
    error,
    lastLoadedAt,
    reload: load,
  };
}
