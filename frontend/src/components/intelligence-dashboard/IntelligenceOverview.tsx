"use client";

import { AlertBannerList, ErrorState, Skeleton } from "@/components/dashboard";
import type { SiteDashboard } from "@/lib/api";
import { BestSolarWindowPanel, computeBestSolarWindow } from "./BestSolarWindow";
import { ConfidencePanel } from "./ConfidencePanel";
import {
  confidenceTierSv,
  forecastConfidencePct,
  shouldShowModelCalibration,
} from "./confidenceLabels";
import { EnergyFlowStrip } from "./EnergyFlowStrip";
import { LiveGaugeCards } from "./LiveGaugeCards";
import { buildPerformanceMetrics, PerformancePanel } from "./PerformancePanel";
import { ProductionForecastPanel } from "./ProductionForecastPanel";
import { TodayStatsGrid } from "./TodayStatsGrid";
import { WeatherSolarPanel } from "./WeatherSolarPanel";
import {
  buildOverviewReading,
  computePerformanceFromSummary,
  extractSparklines,
  useOverviewExtraData,
} from "./useOverviewData";

export function IntelligenceOverview({
  slug,
  dashboard,
}: {
  slug: string;
  dashboard: SiteDashboard;
}) {
  const extra = useOverviewExtraData(slug);
  const reading = buildOverviewReading(dashboard);
  const sparks = extractSparklines(extra.readings);
  const performance = computePerformanceFromSummary(extra.performance, extra.forecast);
  const performanceMetrics = buildPerformanceMetrics(performance);
  const solarWindow = computeBestSolarWindow({
    points: extra.forecast?.points ?? [],
    timezone: dashboard.site.timezone,
    houseLoadW: dashboard.live?.consumption_w ?? undefined,
  });
  const forecastConfidence = forecastConfidencePct(extra.forecast, dashboard.solar?.confidence_pct);
  const confidenceLabel = confidenceTierSv(forecastConfidence);
  const showModelCalibration = shouldShowModelCalibration(extra.forecast);

  const todayLabel = new Date().toLocaleDateString("sv-SE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <div className="idash-overview">
      <header className="idash-overview-header">
        <div>
          <h1 className="idash-site-title">
            {dashboard.site.name}
            <span className="idash-live-badge">● LIVE</span>
          </h1>
        </div>
        <div className="idash-date-chip">
          <span className="idash-date-chip-label">IDAG</span>
          <strong>{todayLabel}</strong>
        </div>
      </header>

      <AlertBannerList alerts={dashboard.alerts.map((a) => a.message_sv)} />

      {!reading ? (
        <Skeleton lines={8} />
      ) : (
        <>
          <LiveGaugeCards
            reading={reading}
            live={dashboard.live}
            solar={dashboard.solar}
            sparkSolar={sparks.solar}
            sparkHouse={sparks.house}
            sparkGrid={sparks.grid}
          />

          <div className="idash-overview-grid">
            <div className="idash-overview-main">
              <EnergyFlowStrip reading={reading} />
              <TodayStatsGrid today={dashboard.today} />
              {extra.loading ? (
                <Skeleton lines={6} />
              ) : (
                <ProductionForecastPanel
                  readings={extra.readings}
                  forecast={extra.forecast}
                  timezone={dashboard.site.timezone}
                />
              )}
            </div>
            <div className="idash-overview-side">
              <PerformancePanel metrics={performanceMetrics} />
              {extra.loading && !extra.weather ? (
                <Skeleton lines={4} />
              ) : (
                <WeatherSolarPanel
                  weather={extra.weather}
                  timezone={dashboard.site.timezone}
                  error={extra.weatherError}
                />
              )}
              <BestSolarWindowPanel window={solarWindow} />
              <ConfidencePanel
                score={forecastConfidence}
                label={confidenceLabel}
                modelScore={showModelCalibration ? extra.forecast?.confidence_score : null}
                modelState={showModelCalibration ? extra.forecast?.model_state : undefined}
                historicalSamples={
                  showModelCalibration ? extra.forecast?.historical_samples : undefined
                }
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export function IntelligenceOverviewLoader({
  slug,
  dashboard,
  loading,
  error,
}: {
  slug: string;
  dashboard: SiteDashboard | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading && !dashboard) {
    return (
      <div className="idash-overview">
        <Skeleton lines={10} />
      </div>
    );
  }
  if (error && !dashboard) {
    return <ErrorState title="Dashboard otillgänglig" text={error} />;
  }
  if (!dashboard) {
    return <ErrorState title="Dashboard otillgänglig" />;
  }
  return <IntelligenceOverview slug={slug} dashboard={dashboard} />;
}
