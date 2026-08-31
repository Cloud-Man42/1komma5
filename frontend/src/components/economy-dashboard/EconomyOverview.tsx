"use client";

import { useMemo, useState } from "react";
import { Skeleton } from "@/components/dashboard";
import { formatRelativeTime } from "@/lib/format";
import {
  EconomyBudgetPanel,
  EconomyCashFlowPanel,
  EconomyGoalsPanel,
  EconomyInsightsPanel,
  EconomyInvestmentPanel,
  EconomySavingsPanel,
} from "./EconomyAnalysisPanels";
import { EconomyCostOverviewChart, EconomyDonutPanel, EconomyPricePanel } from "./EconomyChartPanels";
import { EconomyMetricStrip } from "./EconomyMetricStrip";
import { EconomyBudgetSection } from "./EconomyBudgetSection";
import {
  EconomyCashFlowSection,
  EconomyInsightsDetailSection,
  EconomyPriceDetailsSection,
} from "./EconomyDetailSections";
import { EconomyReportsSection } from "./EconomyReportsSection";
import { EconomySettingsSection } from "./EconomySettingsSection";
import {
  ECONOMY_COMPARE_OPTIONS,
  ECONOMY_PERIOD_OPTIONS,
  type EconomyCompareMode,
  type EconomyPeriodId,
} from "./economyPeriods";
import { exportFinancialCsv } from "./economyDashboardHelpers";
import { useEconomyDashboardData } from "./useEconomyDashboardData";
import { useEconomySection } from "./useEconomySection";

export function EconomyOverview({ siteSlug }: { siteSlug: string }) {
  const { section } = useEconomySection();
  const [period, setPeriod] = useState<EconomyPeriodId>("this-month");
  const [compareMode, setCompareMode] = useState<EconomyCompareMode>("previous-period");
  const data = useEconomyDashboardData(siteSlug, period, compareMode);

  const siteName = siteSlug.charAt(0).toUpperCase() + siteSlug.slice(1);
  const updatedLabel = data.dashboard?.freshness.updated_at
    ? formatRelativeTime(data.dashboard.freshness.updated_at)
    : "—";

  const sparkSeries = useMemo(() => {
    const daily = data.dailySeries;
    return [
      daily.map((p) => p.purchasedSek + p.gridFeeSek + p.taxSek + Math.abs(p.soldSek)),
      daily.map((p) => p.purchasedSek + p.gridFeeSek + p.taxSek),
      daily.map((p) => Math.abs(p.soldSek)),
      daily.map((p) => p.netSek),
      daily.map((_, i) => i + 1),
    ];
  }, [data.dailySeries]);

  if (data.loading && !data.dailyStats) {
    return <Skeleton lines={16} />;
  }

  const renderAnalysisDashboard = () => (
    <>
      <EconomyMetricStrip
        metrics={data.metrics}
        payback={data.payback}
        savingsBreakdown={data.savingsBreakdown}
        exportBreakdown={data.exportBreakdown}
        comparisonLabel={data.comparisonLabel}
        sparkSeries={sparkSeries}
      />
      <div className="edash-mid-row">
        <EconomyCostOverviewChart series={data.dailySeries} />
        <EconomyDonutPanel
          totalSek={data.metrics.gridImportCostSek}
          slices={data.costBreakdown.map((s) => ({ label: s.label, pct: s.pct, color: s.color }))}
        />
        <EconomyPricePanel siteSlug={siteSlug} {...data.priceAnalysis} />
      </div>
      <div className="edash-analysis-row">
        <EconomySavingsPanel totalSek={data.metrics.totalSavingsSek} breakdown={data.savingsBreakdown} />
        <EconomyCashFlowPanel
          siteSlug={siteSlug}
          importCost={data.metrics.gridImportCostSek}
          exportRevenue={data.metrics.exportRevenueSek}
          netCost={data.metrics.netCostSek}
          totalSavings={data.metrics.totalSavingsSek}
        />
        <EconomyBudgetPanel
          usedPct={data.budgetUsedPct}
          spentSek={data.metrics.gridImportCostSek}
          budgetSek={data.monthlyBudgetSek}
          forecastSek={data.forecastCost}
          forecastDelta={data.forecastDelta}
          forecastDeltaPct={data.forecastDeltaPct}
        />
        <EconomyInvestmentPanel
          payback={data.payback}
          ytdReturnPct={data.ytdReturnPct}
          ytdBenefitSek={data.metrics.ytdEconomicBenefitSek}
          lifetimeBenefitSek={data.metrics.lifetimeEconomicBenefitSek}
        />
      </div>
      <div className="edash-bottom-row">
        <EconomyGoalsPanel goals={data.goals} />
        <EconomyInsightsPanel siteSlug={siteSlug} insights={data.insights} />
      </div>
    </>
  );

  const renderSection = () => {
    switch (section) {
      case "reports":
        return <EconomyReportsSection stats={data.periodStats} siteSlug={siteSlug} />;
      case "budget":
        return (
          <EconomyBudgetSection
            usedPct={data.budgetUsedPct}
            spentSek={data.metrics.gridImportCostSek}
            budgetSek={data.monthlyBudgetSek}
            forecastSek={data.forecastCost}
            forecastDelta={data.forecastDelta}
            forecastDeltaPct={data.forecastDeltaPct}
            goals={data.goals}
          />
        );
      case "settings":
        return <EconomySettingsSection siteSlug={siteSlug} />;
      case "cashflow":
        return (
          <EconomyCashFlowSection
            stats={data.periodStats}
            siteSlug={siteSlug}
            importCost={data.metrics.gridImportCostSek}
            exportRevenue={data.metrics.exportRevenueSek}
            netCost={data.metrics.netCostSek}
            totalSavings={data.metrics.totalSavingsSek}
          />
        );
      case "insights":
        return <EconomyInsightsDetailSection insights={data.extendedInsights} siteSlug={siteSlug} />;
      case "prices":
        return (
          <EconomyPriceDetailsSection
            siteSlug={siteSlug}
            marketPrices={data.marketPrices}
            priceAnalysis={data.priceAnalysis}
            timezone={data.timezone}
          />
        );
      default:
        return renderAnalysisDashboard();
    }
  };

  return (
    <section className="edash-overview" data-testid="economy-overview">
      <header className="edash-header">
        <div>
          <h1 className="edash-title">
            EKONOMI
            <span className="edash-live-badge">● LIVE</span>
          </h1>
          <p className="edash-subtitle">
            {siteName} • {data.timezone} · Senast uppdaterad {updatedLabel}
          </p>
          {section !== "analysis" ? (
            <p className="edash-section-label">{data.periodRange.label}</p>
          ) : null}
        </div>
        <div className="edash-header-controls">
          <label className="edash-control">
            <span className="edash-control-icon" aria-hidden="true">📅</span>
            <span className="sr-only">Period</span>
            <select
              aria-label="Period"
              value={period}
              onChange={(event) => setPeriod(event.target.value as EconomyPeriodId)}
            >
              {ECONOMY_PERIOD_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {period !== "since-installation" ? (
            <label className="edash-control">
              <span>Jämför med</span>
              <select
                aria-label="Jämförelseperiod"
                value={compareMode}
                onChange={(event) => setCompareMode(event.target.value as EconomyCompareMode)}
              >
                {ECONOMY_COMPARE_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <button
            type="button"
            className="edash-export-btn"
            onClick={() => exportFinancialCsv(data.periodStats)}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
              <path d="M12 3v12m0 0 4-4m-4 4-4-4M5 21h14" fill="none" stroke="currentColor" strokeWidth="1.6" />
            </svg>
            Exportera rapport
          </button>
        </div>
      </header>

      {data.error ? <p className="edash-error">{data.error}</p> : null}

      {renderSection()}
    </section>
  );
}
