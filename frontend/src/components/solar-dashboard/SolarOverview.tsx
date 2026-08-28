"use client";



import { useState } from "react";

import Link from "next/link";

import { Skeleton } from "@/components/dashboard";

import { formatRelativeTime } from "@/lib/format";

import {

  SolarAccuracyPanel,

  SolarAttributionFooter,

  SolarComparisonPanel,

  SolarDayStatsPanel,

  SolarDistributionPanel,

  SolarForecastSummaryPanel,

  SolarKpiStrip,

  SolarMultiDayPanel,

  SolarProductionChartPanel,

  SolarTomorrowPanel,

  SolarWeatherFactorsPanel,

  SolarWeatherPanel,

} from "./SolarPanels";

import {

  exportSolarCsv,

  todayDateLabel,

  type SolarChartResolution,

} from "./solarDashboardHelpers";

import { SOLAR_SECTION_LABELS } from "./solarSection";

import { useSolarDashboardData } from "./useSolarDashboardData";

import { useSolarSection } from "./useSolarSection";



export function SolarOverview({ siteSlug }: { siteSlug: string }) {

  const [resolution, setResolution] = useState<SolarChartResolution>(15);

  const data = useSolarDashboardData(siteSlug, resolution);

  const { section } = useSolarSection();



  const siteName = data.dashboard?.site.name ?? siteSlug;

  const updatedLabel = data.forecast?.generated_at

    ? formatRelativeTime(data.forecast.generated_at)

    : data.dashboard?.freshness.updated_at

      ? formatRelativeTime(data.dashboard.freshness.updated_at)

      : "—";



  if (data.loading && data.readings.length === 0 && !data.dashboard && !data.config) {
    return <Skeleton lines={16} />;
  }



  if (data.config && data.config.enabled === false) {

    return (

      <section className="sdash-overview" data-testid="solar-overview">

        {data.error ? <p className="sdash-error" role="alert">{data.error}</p> : null}

        <p className="sdash-muted">Solprognos är inte aktiverad för denna anläggning.</p>

        <Link href="/config" className="sdash-link">

          Öppna konfiguration

        </Link>

      </section>

    );

  }



  const renderOverview = () => (

    <>

      <SolarKpiStrip kpi={data.kpi} sparklines={data.sparklines} />

      <div className="sdash-mid-row">

        <SolarProductionChartPanel

          series={data.chartSeries}

          resolution={resolution}

          onResolutionChange={setResolution}

          timezone={data.timezone}

        />

        <SolarDayStatsPanel stats={data.dayStats} />

      </div>

      <div className="sdash-bottom-row">

        <SolarMultiDayPanel rows={data.multiDay} />

        <SolarDistributionPanel slices={data.periodSlices} />

        <SolarComparisonPanel bars={data.comparisonBars} />

        <SolarWeatherFactorsPanel factors={data.weatherFactors} />

      </div>

    </>

  );



  const renderSection = () => {

    switch (section) {

      case "overview":

        return renderOverview();

      case "forecast":

        return (

          <>

            <SolarProductionChartPanel

              series={data.chartSeries}

              resolution={resolution}

              onResolutionChange={setResolution}

              timezone={data.timezone}

            />

            <SolarForecastSummaryPanel forecast={data.forecast} />

            <div className="sdash-bottom-row">

              <SolarMultiDayPanel rows={data.multiDay} />

              <SolarDistributionPanel slices={data.periodSlices} />

            </div>

          </>

        );

      case "tomorrow":

        return (

          <SolarTomorrowPanel
            points={data.tomorrow.points}
            expectedKwh={data.tomorrow.expectedKwh}
            message={data.tomorrow.message}
            stale={data.tomorrow.stale}
          />

        );

      case "weather":

        return (

          <>

            <SolarWeatherPanel weather={data.weather} />

            <SolarWeatherFactorsPanel factors={data.weatherFactors} />

          </>

        );

      case "performance":

        return (

          <>

            <SolarComparisonPanel bars={data.comparisonBars} />

            <SolarDayStatsPanel stats={data.dayStats} />

          </>

        );

      case "accuracy":

        return <SolarAccuracyPanel accuracy={data.accuracy} forecast={data.forecast} />;

      default:

        return renderOverview();

    }

  };



  return (

    <div className="sdash-overview" data-testid="solar-overview">

      <header className="sdash-header">

        <div>

          <h1 className="sdash-title">

            SOLPROGNOS

            <span className="sdash-live-badge">LIVE</span>

          </h1>

          <p className="sdash-subtitle">

            {siteName} · {data.timezone} · Senast uppdaterad {updatedLabel}

          </p>

        </div>

        <div className="sdash-header-controls">

          <span className="sdash-control" data-testid="solar-date-control">

            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">

              <path d="M7 4V2M17 4V2M4 8h16M6 6h12v14H6z" fill="none" stroke="currentColor" strokeWidth="1.4" />

            </svg>

            {todayDateLabel(data.timezone)}

          </span>

          <label className="sdash-control">

            <span>{resolution} min</span>

            <select

              aria-label="Upplösning"

              value={resolution}

              onChange={(e) => setResolution(Number(e.target.value) as SolarChartResolution)}

            >

              <option value={15}>15 min</option>

              <option value={60}>60 min</option>

            </select>

            <span>Upplösning</span>

          </label>

          <button

            type="button"

            className="sdash-export-btn"

            onClick={() => exportSolarCsv(data.chartSeries)}

            disabled={data.chartSeries.length === 0}

          >

            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">

              <path d="M12 4v10M8 11l4 4 4-4M5 20h14" fill="none" stroke="currentColor" strokeWidth="1.6" />

            </svg>

            Exportera data

          </button>

        </div>

      </header>



      {data.error ? <p className="sdash-error" role="alert">{data.error}</p> : null}



      {section !== "overview" ? (

        <p className="sdash-section-label">{SOLAR_SECTION_LABELS[section]}</p>

      ) : null}



      {renderSection()}



      <SolarAttributionFooter provider={data.weather?.provider} />

    </div>

  );

}


