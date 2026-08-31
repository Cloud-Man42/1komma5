"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchSiteDashboard,
  fetchSiteHistory,
  fetchSitePeaks,
  type PeakPeriod,
  type PeakReading,
  type Reading,
  type SiteDashboard,
  type AggregatedReading,
} from "@/lib/api";
import { useOptionalSiteData } from "@/lib/SiteDataProvider";
import { gridFlowState, normalizeFlowValues, readingToFlowValues } from "@/lib/energyFlow";
import {
  buildFlowChartSeries,
  buildLiveMetrics,
  buildSocSeries,
  buildTodayMetrics,
  integrateBatteryKwh,
  sparklineFromReadings,
  type HistoryBucketMinutes,
} from "./energyDashboardHelpers";

export function useEnergyDashboardData(siteSlug: string, bucketMinutes: HistoryBucketMinutes = 15) {
  const shared = useOptionalSiteData();
  const [dashboard, setDashboard] = useState<SiteDashboard | null>(shared?.dashboard ?? null);
  const [readings, setReadings] = useState<(Reading | AggregatedReading)[]>([]);
  const [peaks, setPeaks] = useState<PeakReading[]>([]);
  const [peakPeriod, setPeakPeriod] = useState<PeakPeriod>("day");
  const [peakYear, setPeakYear] = useState(new Date().getFullYear());
  const [availablePeakYears, setAvailablePeakYears] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [peaksLoading, setPeaksLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [peaksError, setPeaksError] = useState<string | null>(null);

  useEffect(() => {
    if (shared?.dashboard) {
      setDashboard(shared.dashboard);
    }
  }, [shared?.dashboard]);

  const timezone = dashboard?.site.timezone ?? "Europe/Stockholm";

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const dashboardPromise = shared?.dashboard
        ? Promise.resolve(shared.dashboard)
        : fetchSiteDashboard(siteSlug).catch(() => null);

      const [dash, history] = await Promise.all([
        dashboardPromise,
        fetchSiteHistory(siteSlug, bucketMinutes, 24),
      ]);
      setDashboard(dash);
      setReadings(history.readings);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte ladda energidata.");
    } finally {
      setLoading(false);
    }
  }, [bucketMinutes, shared?.dashboard, siteSlug]);

  const reloadPeaks = useCallback(async () => {
    setPeaksLoading(true);
    try {
      const yearPromise = fetchSitePeaks(siteSlug, "year");
      const periodPromise =
        peakPeriod === "year" ? yearPromise : fetchSitePeaks(siteSlug, peakPeriod, peakYear);
      const [yearResponse, periodResponse] = await Promise.all([yearPromise, periodPromise]);
      const years = yearResponse.peaks
        .map((p) => Number(p.period_start))
        .filter(Number.isFinite)
        .sort((a, b) => b - a);
      setAvailablePeakYears(years);
      if (years.length > 0 && !years.includes(peakYear)) {
        setPeakYear(years[0]);
      }
      setPeaks(periodResponse.peaks);
      setPeaksError(null);
    } catch (reason) {
      setPeaks([]);
      setPeaksError(reason instanceof Error ? reason.message : "Kunde inte läsa peakvärden.");
    } finally {
      setPeaksLoading(false);
    }
  }, [peakPeriod, peakYear, siteSlug]);

  useEffect(() => {
    reload();
    const interval = setInterval(reload, 60_000);
    return () => clearInterval(interval);
  }, [reload]);

  useEffect(() => {
    reloadPeaks();
  }, [reloadPeaks]);

  const batteryKwh = useMemo(() => integrateBatteryKwh(readings), [readings]);
  const live = useMemo(() => buildLiveMetrics(dashboard?.live), [dashboard?.live]);
  const today = useMemo(
    () => buildTodayMetrics(dashboard?.today, batteryKwh),
    [batteryKwh, dashboard?.today],
  );
  const chartSeries = useMemo(
    () => buildFlowChartSeries(readings, timezone),
    [readings, timezone],
  );
  const socSeries = useMemo(() => buildSocSeries(readings), [readings]);
  const sparkSolar = useMemo(
    () => sparklineFromReadings(readings, (r) => r.solar_production_w ?? 0),
    [readings],
  );
  const sparkConsumption = useMemo(
    () => sparklineFromReadings(readings, (r) => r.consumption_w ?? 0),
    [readings],
  );
  const sparkBattery = useMemo(
    () => sparklineFromReadings(readings, (r) => r.battery_power_w ?? 0),
    [readings],
  );
  const sparkGrid = useMemo(
    () =>
      sparklineFromReadings(readings, (r) => {
        const normalized = normalizeFlowValues(readingToFlowValues(r as Reading));
        return Math.abs(gridFlowState(normalized.gridImportW, normalized.gridExportW).signedW);
      }),
    [readings],
  );

  const latestReading = useMemo((): Reading | null => {
    if (readings.length === 0) return null;
    const last = readings[readings.length - 1];
    if ("bucket_start" in last) {
      return {
        recorded_at: last.bucket_start,
        solar_production_w: last.solar_production_w,
        consumption_w: last.consumption_w,
        grid_import_w: last.grid_import_w,
        grid_export_w: last.grid_export_w,
        battery_soc_pct: last.battery_soc_pct,
        battery_power_w: last.battery_power_w,
      };
    }
    return last;
  }, [readings]);

  return {
    dashboard,
    readings,
    peaks,
    peakPeriod,
    setPeakPeriod,
    peakYear,
    setPeakYear,
    availablePeakYears,
    loading,
    peaksLoading,
    error,
    peaksError,
    timezone,
    live,
    today,
    chartSeries,
    socSeries,
    sparkSolar,
    sparkConsumption,
    sparkBattery,
    sparkGrid,
    latestReading,
    reload,
    reloadPeaks,
  };
}
