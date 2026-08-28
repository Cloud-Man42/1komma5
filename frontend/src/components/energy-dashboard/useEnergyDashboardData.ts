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
  const [dashboard, setDashboard] = useState<SiteDashboard | null>(null);
  const [readings, setReadings] = useState<(Reading | AggregatedReading)[]>([]);
  const [peaks, setPeaks] = useState<PeakReading[]>([]);
  const [peakPeriod, setPeakPeriod] = useState<PeakPeriod>("day");
  const [peakYear, setPeakYear] = useState(new Date().getFullYear());
  const [availablePeakYears, setAvailablePeakYears] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [peaksLoading, setPeaksLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [peaksError, setPeaksError] = useState<string | null>(null);

  const timezone = dashboard?.site.timezone ?? "Europe/Stockholm";

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, history] = await Promise.all([
        fetchSiteDashboard(siteSlug).catch(() => null),
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
  }, [bucketMinutes, siteSlug]);

  const reloadPeaks = useCallback(async () => {
    setPeaksLoading(true);
    try {
      const yearResponse = await fetchSitePeaks(siteSlug, "year");
      const years = yearResponse.peaks
        .map((p) => Number(p.period_start))
        .filter(Number.isFinite)
        .sort((a, b) => b - a);
      setAvailablePeakYears(years);
      if (years.length > 0 && !years.includes(peakYear)) {
        setPeakYear(years[0]);
      }

      if (peakPeriod === "year") {
        setPeaks(yearResponse.peaks);
      } else {
        const response = await fetchSitePeaks(siteSlug, peakPeriod, peakYear);
        setPeaks(response.peaks);
      }
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
      sparklineFromReadings(
        readings,
        (r) => (r.grid_export_w ?? 0) - (r.grid_import_w ?? 0),
      ),
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
