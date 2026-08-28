"use client";

import { useEffect, useState } from "react";
import { Skeleton } from "@/components/dashboard";
import { formatRelativeTime } from "@/lib/format";
import {
  EnergyBatteryPanel,
  EnergyFlowChartPanel,
  EnergyMetricStrip,
  EnergyPeaksPanel,
  EnergyPlaceholderSection,
  EnergyQuickOverviewPanel,
} from "./EnergyPanels";
import { exportEnergyCsv, todayDateLabel, type HistoryBucketMinutes } from "./energyDashboardHelpers";
import { ENERGY_SECTION_LABELS } from "./energySection";
import { useEnergyDashboardData } from "./useEnergyDashboardData";
import { useEnergySection } from "./useEnergySection";

export function EnergyOverview({ siteSlug }: { siteSlug: string }) {
  const [bucketMinutes, setBucketMinutes] = useState<HistoryBucketMinutes>(15);
  const data = useEnergyDashboardData(siteSlug, bucketMinutes);
  const { section } = useEnergySection();

  const siteName = data.dashboard?.site.name ?? siteSlug;
  const timezone = data.timezone;
  const updatedLabel = data.dashboard?.freshness.updated_at
    ? formatRelativeTime(data.dashboard.freshness.updated_at)
    : "—";

  useEffect(() => {
    if (section !== "peaks") return;
    document.getElementById("enrg-peaks")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [section]);

  if (data.loading && data.readings.length === 0) {
    return <Skeleton lines={16} />;
  }

  const renderFlowDashboard = () => (
    <>
      <EnergyMetricStrip
        live={data.live}
        today={data.today}
        sparkSolar={data.sparkSolar}
        sparkConsumption={data.sparkConsumption}
        sparkBattery={data.sparkBattery}
        sparkGrid={data.sparkGrid}
      />
      <div className="enrg-mid-row">
        <EnergyFlowChartPanel
          series={data.chartSeries}
          bucketMinutes={bucketMinutes}
          onBucketChange={setBucketMinutes}
        />
        <EnergyBatteryPanel live={data.live} today={data.today} socSeries={data.socSeries} />
        <EnergyQuickOverviewPanel reading={data.latestReading} />
      </div>
      <EnergyPeaksPanel
        peaks={data.peaks}
        period={data.peakPeriod}
        onPeriodChange={data.setPeakPeriod}
        year={data.peakYear}
        onYearChange={data.setPeakYear}
        availableYears={data.availablePeakYears}
        loading={data.peaksLoading}
        error={data.peaksError}
      />
    </>
  );

  const renderSection = () => {
    switch (section) {
      case "flow":
        return renderFlowDashboard();
      case "flows":
        return (
          <>
            <EnergyQuickOverviewPanel reading={data.latestReading} />
            <EnergyFlowChartPanel
              series={data.chartSeries}
              bucketMinutes={bucketMinutes}
              onBucketChange={setBucketMinutes}
            />
          </>
        );
      case "history":
        return (
          <EnergyFlowChartPanel
            series={data.chartSeries}
            bucketMinutes={bucketMinutes}
            onBucketChange={setBucketMinutes}
          />
        );
      case "live":
        return (
          <>
            <EnergyMetricStrip
              live={data.live}
              today={data.today}
              sparkSolar={data.sparkSolar}
              sparkConsumption={data.sparkConsumption}
              sparkBattery={data.sparkBattery}
              sparkGrid={data.sparkGrid}
            />
            <EnergyQuickOverviewPanel reading={data.latestReading} />
          </>
        );
      case "quality":
        return (
          <EnergyPlaceholderSection
            title="KVALITET"
            description={
              data.dashboard?.freshness.stale
                ? "Senaste mätdata är föråldrad. Kontrollera HeartBeat-anslutningen."
                : "All mätdata är färsk och inom normal kvalitet."
            }
          />
        );
      case "peaks":
        return (
          <>
            {renderFlowDashboard()}
          </>
        );
      case "reports":
        return (
          <EnergyPlaceholderSection
            title="RAPPORTER"
            description="Exportera rådata via knappen Exportera data i huvudvyn, eller använd Ekonomi → Rapporter för kostnadsrapporter."
          />
        );
      default:
        return renderFlowDashboard();
    }
  };

  return (
    <div className="enrg-overview" data-testid="energy-overview">
      <header className="enrg-header">
        <div>
          <h1 className="enrg-title">
            ENERGI – FLÖDE &amp; FÖRBRUKNING
            <span className="enrg-live-badge">LIVE</span>
          </h1>
          <p className="enrg-subtitle">
            <span>{siteName}</span>
            <span aria-hidden="true"> · </span>
            <span>{timezone}</span>
            <span aria-hidden="true"> · </span>
            <span>Senast uppdaterad {updatedLabel}</span>
          </p>
        </div>
        <div className="enrg-header-controls">
          <span className="enrg-control" data-testid="energy-date-control">
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
              <path d="M7 4V2M17 4V2M4 8h16M6 6h12v14H6z" fill="none" stroke="currentColor" strokeWidth="1.4" />
            </svg>
            {todayDateLabel(timezone)}
          </span>
          <label className="enrg-control">
            <span>{bucketMinutes} min</span>
            <select
              aria-label="Upplösning"
              value={bucketMinutes}
              onChange={(e) => setBucketMinutes(Number(e.target.value) as HistoryBucketMinutes)}
            >
              <option value={5}>5 min</option>
              <option value={15}>15 min</option>
              <option value={60}>60 min</option>
            </select>
            <span>Upplösning</span>
          </label>
          <button
            type="button"
            className="enrg-export-btn"
            onClick={() => exportEnergyCsv(data.readings)}
            disabled={data.readings.length === 0}
          >
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
              <path d="M12 4v10M8 11l4 4 4-4M5 20h14" fill="none" stroke="currentColor" strokeWidth="1.6" />
            </svg>
            Exportera data
          </button>
        </div>
      </header>

      {data.error ? (
        <p className="enrg-error" role="alert">
          {data.error}
        </p>
      ) : null}

      {section !== "flow" && section !== "peaks" ? (
        <p className="enrg-section-label">{ENERGY_SECTION_LABELS[section]}</p>
      ) : null}

      {renderSection()}
    </div>
  );
}
