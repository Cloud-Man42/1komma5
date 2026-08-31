"use client";

import { useState, type CSSProperties, type ReactNode } from "react";
import { Sparkline } from "@/components/intelligence-dashboard/Sparkline";
import { CircularGauge } from "@/components/intelligence-dashboard/CircularGauge";
import type {
  EconomyDisplayMetrics,
  ExportRevenueBreakdown,
  PaybackMetrics,
  SavingsBreakdownItem,
} from "./economyDashboardHelpers";
import {
  formatComparisonSubtext,
  formatEconomyKr,
  formatEconomyPct,
  formatMetricValue,
  formatReturnPct,
} from "./economyDashboardHelpers";
import { EconomyInfoTip } from "./EconomyInfoTip";

function MetricCard({
  title,
  info,
  value,
  changePct,
  changeSubtext,
  invertChange = false,
  positiveIsGood = true,
  accent,
  sparkValues,
  gauge,
  expandable,
}: {
  title: string;
  info?: string;
  value: string;
  changePct: number | null;
  changeSubtext: string;
  invertChange?: boolean;
  positiveIsGood?: boolean;
  accent: string;
  sparkValues: number[];
  gauge?: ReactNode;
  expandable?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const pct = formatEconomyPct(changePct, invertChange);
  const isUp = changePct != null && changePct > 0;
  const good = invertChange ? !isUp : positiveIsGood ? isUp : !isUp;
  const badgeClass =
    changePct == null ? "edash-metric-badge-neutral" : good ? "edash-metric-badge-good" : "edash-metric-badge-warn";

  return (
    <article className="edash-metric-card" style={{ "--edash-accent": accent } as CSSProperties}>
      {!gauge ? (
        <div className="edash-metric-spark-bg" aria-hidden="true">
          <Sparkline values={sparkValues} color={accent} className="edash-metric-spark" />
        </div>
      ) : null}
      <p className="edash-metric-label">
        {title}
        {info ? <EconomyInfoTip text={info} /> : null}
      </p>
      <div className="edash-metric-row">
        <strong className="edash-metric-value">{value}</strong>
        {gauge}
        {changePct != null ? <span className={`edash-metric-badge ${badgeClass}`}>{pct}</span> : null}
      </div>
      <p className="edash-metric-sub">{changeSubtext}</p>
      {expandable ? (
        <>
          <button
            type="button"
            className="edash-metric-expand"
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? "Dölj fördelning" : "Visa fördelning"}
          </button>
          {open ? expandable : null}
        </>
      ) : null}
    </article>
  );
}

function SavingsBreakdownList({ breakdown }: { breakdown: SavingsBreakdownItem[] }) {
  if (breakdown.length === 0) {
    return <p className="edash-metric-breakdown-empty">Ingen besparing registrerad för perioden.</p>;
  }
  return (
    <ul className="edash-metric-breakdown">
      {breakdown.map((row) => (
        <li key={row.id}>
          <span>
            <i style={{ background: row.color }} aria-hidden="true" />
            {row.label}
          </span>
          <strong>{formatEconomyKr(row.amountSek)}</strong>
        </li>
      ))}
    </ul>
  );
}

function ExportBreakdownList({ breakdown }: { breakdown: ExportRevenueBreakdown }) {
  if (breakdown.exportedKwh <= 0) {
    return <p className="edash-metric-breakdown-empty">Ingen export registrerad för perioden.</p>;
  }
  return (
    <div className="edash-metric-breakdown" data-testid="export-revenue-breakdown">
      <p className="edash-export-breakdown-meta">
        Såld energi: {breakdown.exportedKwh.toFixed(1)} kWh
        {breakdown.weightedSpotPriceKrKwh != null
          ? ` · Genomsnittligt avtalat pris ${(breakdown.weightedSpotPriceKrKwh * 100).toFixed(1)} öre/kWh`
          : null}
      </p>
      <ul>
        {breakdown.lines.map((line) => (
          <li key={line.id}>
            <span>{line.label}</span>
            <strong>{formatEconomyKr(line.valueSek)}</strong>
          </li>
        ))}
        <li className="edash-export-breakdown-total">
          <span>Totalt (såld el)</span>
          <strong>{formatEconomyKr(breakdown.totalExportRevenueSek)}</strong>
        </li>
      </ul>
      {breakdown.showPreContractExportNotice ? (
        <p className="edash-export-breakdown-note">
          {breakdown.preContractExportedKwh.toFixed(1)} kWh exporterades före exportavtal
          {breakdown.sellContractStartDate ? ` (${breakdown.sellContractStartDate})` : ""} och ger ingen
          intäkt i beräkningen.
        </p>
      ) : null}
      {breakdown.showTaxCreditNotice ? (
        <p className="edash-export-breakdown-note">
          Skattereduktion för mikroproduktion upphörde 2026-01-01.
        </p>
      ) : null}
    </div>
  );
}

export function EconomyMetricStrip({
  metrics,
  payback,
  savingsBreakdown,
  exportBreakdown,
  comparisonLabel,
  sparkSeries,
}: {
  metrics: EconomyDisplayMetrics;
  payback: PaybackMetrics;
  savingsBreakdown: SavingsBreakdownItem[];
  exportBreakdown: ExportRevenueBreakdown;
  comparisonLabel: string;
  sparkSeries: number[][];
}) {
  const compare = (key: keyof EconomyDisplayMetrics["changes"], higherIsGood: boolean, invert = false) =>
    formatComparisonSubtext(metrics.changes[key], comparisonLabel, { higherIsGood, invertGood: invert });

  return (
    <div className="edash-metric-strip" data-testid="economy-metric-strip">
      <MetricCard
        title="NETTOKOSTNAD"
        info="Vad du faktiskt betalat efter intäkter från såld el."
        value={formatMetricValue(metrics.netCostSek, { allowZero: true })}
        changePct={metrics.changes.netCost.pct}
        changeSubtext={compare("netCost", false, true)}
        invertChange
        positiveIsGood={false}
        accent="#38bdf8"
        sparkValues={sparkSeries[3] ?? [3, 2, 4, 2]}
      />
      <MetricCard
        title="TOTAL BESPARING"
        info="Sol- och batteribesparing plus avtalad exportintäkt. Export före exportavtal ingår inte."
        value={formatMetricValue(metrics.totalSavingsSek)}
        changePct={metrics.changes.totalSavings.pct}
        changeSubtext={compare("totalSavings", true)}
        accent="#4ade80"
        sparkValues={sparkSeries[0] ?? [1, 2, 3, 4]}
        expandable={<SavingsBreakdownList breakdown={savingsBreakdown} />}
      />
      <MetricCard
        title="SEDAN INSTALLATION"
        info="Total ekonomisk nytta sedan systemet började mätas."
        value={formatMetricValue(metrics.lifetimeEconomicBenefitSek)}
        changePct={null}
        changeSubtext="Ackumulerad besparing"
        accent="#2dd4bf"
        sparkValues={sparkSeries[4] ?? [2, 3, 4, 5]}
      />
      <MetricCard
        title="AVKASTNING (YTD)"
        info="Ekonomisk nytta i förhållande till investeringskostnaden."
        value={formatReturnPct(metrics.ytdReturnPct)}
        changePct={null}
        changeSubtext={
          payback.investmentSek != null
            ? `${formatEconomyKr(metrics.ytdEconomicBenefitSek)} nytta i år`
            : "Investering ej angiven"
        }
        accent="#4ade80"
        sparkValues={sparkSeries[4] ?? [2, 3, 4, 5]}
        gauge={
          metrics.ytdReturnPct != null ? (
            <CircularGauge
              value={Math.min(100, metrics.ytdReturnPct * 4)}
              label=""
              color="#4ade80"
              size={52}
            />
          ) : null
        }
      />
      <MetricCard
        title="ÅTERBETALNING"
        info="Beräknad tid tills investeringen är återbetald baserat på senaste 12 månaders nytta."
        value={
          payback.paybackYears != null
            ? `${payback.paybackYears.toFixed(1)} år`
            : payback.investmentSek == null
              ? "Investering ej angiven"
              : "Beräknas när mer historik finns"
        }
        changePct={null}
        changeSubtext={
          payback.investmentSek != null
            ? `${Math.round(payback.repaidPct ?? 0)} % återbetalt · ${formatEconomyKr(payback.remainingSek ?? 0)} kvar`
            : "Prognos kräver investeringsbelopp"
        }
        accent="#a78bfa"
        sparkValues={sparkSeries[1] ?? [4, 3, 2, 1]}
      />
      <MetricCard
        title="ELKOSTNAD"
        info="Kostnad för el köpt från nätet före exportintäkter."
        value={formatMetricValue(metrics.gridImportCostSek, { allowZero: true })}
        changePct={metrics.changes.gridImportCost.pct}
        changeSubtext={compare("gridImportCost", false, true)}
        invertChange
        positiveIsGood={false}
        accent="#a78bfa"
        sparkValues={sparkSeries[1] ?? [4, 3, 2, 1]}
      />
      <MetricCard
        title="SÅLD EL-INTÄKT"
        info="Ersättning för avtalad export från exportavtalets startdatum. Export före avtal räknas inte som intäkt."
        value={formatMetricValue(metrics.exportRevenueSek)}
        changePct={metrics.changes.exportRevenue.pct}
        changeSubtext={compare("exportRevenue", true)}
        accent="#4ade80"
        sparkValues={sparkSeries[2] ?? [1, 3, 2, 5]}
        expandable={<ExportBreakdownList breakdown={exportBreakdown} />}
      />
    </div>
  );
}
