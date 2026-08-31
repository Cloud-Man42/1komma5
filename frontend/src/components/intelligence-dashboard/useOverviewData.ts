"use client";

import { useEffect, useState } from "react";
import { gridFlowState, normalizeFlowValues, readingToFlowValues } from "@/lib/energyFlow";
import { useSolarLayoutData } from "@/lib/SolarLayoutContext";
import {
  fetchSiteHistory,
  fetchSolarConfig,
  fetchSolarForecast,
  fetchSolarPerformance,
  fetchSolarWeather,
  type Reading,
  type SiteDashboard,
  type SolarForecast,
  type SolarPerformance,
  type SolarSiteConfig,
  type SolarWeather,
} from "@/lib/api";

export interface OverviewExtraData {
  forecast: SolarForecast | null;
  config: SolarSiteConfig | null;
  readings: Reading[];
  performance: SolarPerformance | null;
  weather: SolarWeather | null;
  weatherError: string | null;
  loading: boolean;
}

export function useOverviewExtraData(slug: string): OverviewExtraData {
  const layoutSolar = useSolarLayoutData();
  const [forecast, setForecast] = useState<SolarForecast | null>(null);
  const [config, setConfig] = useState<SolarSiteConfig | null>(layoutSolar?.config ?? null);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [performance, setPerformance] = useState<SolarPerformance | null>(null);
  const [weather, setWeather] = useState<SolarWeather | null>(layoutSolar?.weather ?? null);
  const [weatherError, setWeatherError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setConfig(layoutSolar?.config ?? null);
    setWeather(layoutSolar?.weather ?? null);
  }, [layoutSolar?.config, layoutSolar?.weather]);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const cfg =
          layoutSolar?.config ?? (await fetchSolarConfig(slug).catch(() => null));
        if (!active) return;
        setConfig(cfg);

        const hist = await fetchSiteHistory(slug, 5, 24).catch(() => null);
        if (!active) return;
        setReadings(hist?.readings ?? []);

        const forecastPromise = cfg?.complete
          ? fetchSolarForecast(slug).catch(() => null)
          : Promise.resolve(null);
        const perfPromise = cfg?.enabled
          ? fetchSolarPerformance(slug).catch(() => null)
          : Promise.resolve(null);

        let weatherPromise: Promise<{ data: SolarWeather | null; error: string | null }>;
        if (layoutSolar?.weather) {
          weatherPromise = Promise.resolve({ data: layoutSolar.weather, error: null });
        } else if (cfg?.enabled) {
          weatherPromise = fetchSolarWeather(slug).then(
            (data) => ({ data, error: null as string | null }),
            (e: unknown) => ({
              data: null,
              error: e instanceof Error ? e.message : "Väderdata otillgänglig",
            }),
          );
        } else {
          weatherPromise = Promise.resolve({
            data: null,
            error: "Aktivera solprognosen för att visa väder.",
          });
        }

        const [fc, perf, wx] = await Promise.all([forecastPromise, perfPromise, weatherPromise]);
        if (!active) return;
        setForecast(fc);
        setPerformance(perf);
        setWeather(wx.data);
        setWeatherError(wx.error);
      } finally {
        if (active) setLoading(false);
      }
    };

    load();
    const interval = setInterval(load, 60_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [slug, layoutSolar?.config, layoutSolar?.weather]);

  return { forecast, config, readings, performance, weather, weatherError, loading };
}

export function extractSparklines(readings: Reading[]) {
  const solar = readings.map((r) => r.solar_production_w ?? 0);
  const house = readings.map((r) => r.consumption_w ?? 0);
  const grid = readings.map((r) => {
    const normalized = normalizeFlowValues(readingToFlowValues(r));
    return Math.abs(gridFlowState(normalized.gridImportW, normalized.gridExportW).signedW);
  });
  return { solar, house, grid };
}

export function computePerformanceFromSummary(
  performance: SolarPerformance | null,
  forecast: SolarForecast | null,
): {
  headlineRatio: number | null;
  todayDeviation: number | null;
  weekAvg: number | null;
  monthAvg: number | null;
  quarterAvg: number | null;
  ytdAvg: number | null;
} {
  if (performance) {
    return {
      headlineRatio: performance.headline_ratio,
      todayDeviation: performance.today_deviation_pct,
      weekAvg: performance.week_avg,
      monthAvg: performance.month_avg,
      quarterAvg: performance.quarter_avg,
      ytdAvg: performance.ytd_avg,
    };
  }

  const rawSoFar = forecast?.raw_forecast_so_far_kwh;
  const actualToday = forecast?.actual_today_kwh;
  const todayDeviation =
    rawSoFar != null && rawSoFar > 0 && actualToday != null
      ? ((actualToday - rawSoFar) / rawSoFar) * 100
      : null;

  return {
    headlineRatio: null,
    todayDeviation,
    weekAvg: null,
    monthAvg: null,
    quarterAvg: null,
    ytdAvg: null,
  };
}

export function buildOverviewReading(dashboard: SiteDashboard) {
  if (!dashboard.live || !dashboard.freshness.updated_at) return null;
  return {
    recorded_at: dashboard.freshness.updated_at,
    solar_production_w: dashboard.live.solar_production_w ?? 0,
    consumption_w: dashboard.live.consumption_w ?? 0,
    grid_import_w: dashboard.live.grid_import_w ?? 0,
    grid_export_w: dashboard.live.grid_export_w ?? 0,
    battery_soc_pct: dashboard.live.battery_soc_pct ?? 0,
    battery_power_w: dashboard.live.battery_power_w ?? 0,
  };
}
