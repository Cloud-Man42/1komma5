"use client";



import { useCallback, useEffect, useMemo, useState } from "react";

import {

  fetchSiteDashboard,

  fetchSiteHistory,

  fetchSolarAccuracy,

  fetchSolarConfig,

  fetchSolarForecast,

  fetchSolarPerformance,

  fetchSolarWeather,

  type Reading,

  type SiteDashboard,

  type SolarAccuracy,

  type SolarForecast,

  type SolarPerformance,

  type SolarSiteConfig,

  type SolarWeather,

} from "@/lib/api";

import { useOptionalSiteData } from "@/lib/SiteDataProvider";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

import {

  buildComparisonBars,

  buildDayStats,

  buildKpiMetrics,

  buildKpiSparklines,

  buildMultiDayOverview,

  buildPeriodDistribution,

  buildProductionChartSeries,

  buildTomorrowForecast,

  buildWeatherFactors,

  type SolarChartResolution,

  type SolarComparisonBar,

  type SolarDayStats,

  type SolarKpiMetrics,

  type SolarKpiSparklines,

  type SolarMultiDayRow,

  type SolarPeriodSlice,

  type SolarProductionChartPoint,

  type SolarWeatherFactors,

} from "./solarDashboardHelpers";



export function useSolarDashboardData(siteSlug: string, resolution: SolarChartResolution = 15) {

  const refreshSeconds = useDashboardRefreshSeconds();
  const shared = useOptionalSiteData();

  const [dashboard, setDashboard] = useState<SiteDashboard | null>(shared?.dashboard ?? null);

  const [config, setConfig] = useState<SolarSiteConfig | null>(null);

  const [forecast, setForecast] = useState<SolarForecast | null>(null);

  const [performance, setPerformance] = useState<SolarPerformance | null>(null);

  const [weather, setWeather] = useState<SolarWeather | null>(null);

  const [accuracy, setAccuracy] = useState<SolarAccuracy | null>(null);

  const [readings, setReadings] = useState<Reading[]>([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);



  const timezone = dashboard?.site.timezone ?? "Europe/Stockholm";

  const solarEnabled = config?.enabled !== false;

  useEffect(() => {
    if (shared?.dashboard) {
      setDashboard(shared.dashboard);
    }
  }, [shared?.dashboard]);

  const reload = useCallback(async () => {
    const bucketMinutes = resolution === 60 ? 60 : 5;
    const dashboardPromise = shared?.dashboard
      ? Promise.resolve(shared.dashboard)
      : fetchSiteDashboard(siteSlug).catch(() => null);

    try {
      const [dash, solarConfig, history] = await Promise.all([
        dashboardPromise,
        fetchSolarConfig(siteSlug).catch(() => null),
        fetchSiteHistory(siteSlug, bucketMinutes, 24).catch(() => ({ readings: [] as Reading[] })),
      ]);

      setDashboard(dash);
      setConfig(solarConfig);
      setReadings(history.readings ?? []);
      setError(null);
      setLoading(false);

      const enabled = solarConfig?.enabled !== false;
      const [forecastData, performanceData, weatherData, accuracyData] = await Promise.all([
        enabled ? fetchSolarForecast(siteSlug).catch(() => null) : Promise.resolve(null),
        enabled ? fetchSolarPerformance(siteSlug).catch(() => null) : Promise.resolve(null),
        enabled ? fetchSolarWeather(siteSlug).catch(() => null) : Promise.resolve(null),
        enabled ? fetchSolarAccuracy(siteSlug).catch(() => null) : Promise.resolve(null),
      ]);

      setForecast(forecastData);
      setPerformance(performanceData);
      setWeather(weatherData);
      setAccuracy(accuracyData);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte ladda solprognos.");
      setLoading(false);
    }
  }, [shared?.dashboard, siteSlug, resolution]);



  useEffect(() => {

    reload();

    const interval = setInterval(reload, refreshSeconds * 1000);

    return () => clearInterval(interval);

  }, [reload, refreshSeconds]);



  const kpi = useMemo(() => buildKpiMetrics(forecast), [forecast]);

  const chartSeries = useMemo(

    () =>

      buildProductionChartSeries({

        readings,

        forecast,

        performance,

        timezone,

        resolution,

      }),

    [readings, forecast, performance, timezone, resolution],

  );

  const dayStats = useMemo(

    () => buildDayStats({ forecast, readings, weather, config, timezone }),

    [forecast, readings, weather, config, timezone],

  );

  const periodSlices = useMemo(

    () => buildPeriodDistribution(forecast, timezone),

    [forecast, timezone],

  );

  const multiDay = useMemo(() => buildMultiDayOverview(forecast, timezone), [forecast, timezone]);

  const comparisonBars = useMemo(() => buildComparisonBars(performance), [performance]);

  const weatherFactors = useMemo(() => buildWeatherFactors(weather, timezone), [weather, timezone]);

  const sparklines = useMemo(

    () => buildKpiSparklines(chartSeries, kpi.confidencePct),

    [chartSeries, kpi.confidencePct],

  );

  const tomorrow = useMemo(
    () => buildTomorrowForecast(forecast, timezone),
    [forecast, timezone],
  );

  const tomorrowPoints = tomorrow.points;



  return {

    dashboard,

    config,

    forecast,

    performance,

    weather,

    accuracy,

    readings,

    kpi,

    chartSeries,

    dayStats,

    periodSlices,

    multiDay,

    comparisonBars,

    weatherFactors,

    sparklines,

    tomorrowPoints,

    tomorrow,

    timezone,

    solarEnabled,

    loading,

    error,

    refreshSeconds,

    reload,

  };

}



export type SolarDashboardData = ReturnType<typeof useSolarDashboardData>;



export type {

  SolarComparisonBar,

  SolarDayStats,

  SolarKpiMetrics,

  SolarKpiSparklines,

  SolarMultiDayRow,

  SolarPeriodSlice,

  SolarProductionChartPoint,

  SolarWeatherFactors,

};


