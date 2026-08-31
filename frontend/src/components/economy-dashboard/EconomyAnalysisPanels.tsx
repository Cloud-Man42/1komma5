"use client";

import type { CostBreakdownSlice, EconomyGoal, EconomyInsight, SavingsBreakdownItem } from "./economyDashboardHelpers";
import type { PaybackMetrics } from "./economyDashboardHelpers";
import { formatEconomyKr } from "./economyDashboardHelpers";
import { navigateEconomySection } from "./economySection";

export function EconomySavingsPanel({
  totalSek,
  breakdown,
}: {
  totalSek: number;
  breakdown: SavingsBreakdownItem[];
}) {
  return (
    <article className="edash-panel edash-panel-savings" data-testid="economy-savings-panel">
      <header>
        <h3>BESPARING JÄMFÖRT MED UTAN SOL &amp; BATTERI</h3>
        <p className="edash-panel-kicker">{formatEconomyKr(totalSek)} Total besparing</p>
      </header>

      <div
        className="edash-savings-stacked-bar"
        role="img"
        aria-label={`Besparing: ${breakdown.map((row) => `${row.label} ${Math.round(row.pct)}%`).join(", ")}`}
      >
        {breakdown.map((row) =>
          row.pct > 0 ? (
            <span
              key={row.id}
              className="edash-savings-stacked-segment"
              style={{ width: `${row.pct}%`, background: row.color }}
              title={`${row.label}: ${formatEconomyKr(row.amountSek)} (${Math.round(row.pct)}%)`}
            />
          ) : null,
        )}
      </div>

      <ul className="edash-savings-list">
        {breakdown.map((row) => (
          <li key={row.id}>
            <span className="edash-savings-row-label">
              <i className="edash-savings-swatch" style={{ background: row.color }} aria-hidden="true" />
              {row.label}
            </span>
            <strong>{formatEconomyKr(row.amountSek)}</strong>
            <em>{Math.round(row.pct)}%</em>
          </li>
        ))}
      </ul>

      <div className="edash-cylinder-wrap">
        <p className="edash-savings-chart-label">Andel per kategori</p>
        <div className="edash-cylinder" aria-hidden="true">
          {breakdown.map((row) => (
            <div key={row.id} className="edash-cylinder-item">
              <div
                className="edash-cylinder-segment"
                style={{
                  height: `${Math.max(14, row.pct * 0.85)}%`,
                  background: row.color,
                  boxShadow: `0 0 12px ${row.color}44`,
                }}
              />
              <span className="edash-cylinder-pct">{Math.round(row.pct)}%</span>
            </div>
          ))}
        </div>
      </div>

      <ul className="edash-savings-legend" aria-label="Förklaring av färger">
        {breakdown.map((row) => (
          <li key={`legend-${row.id}`}>
            <i className="edash-savings-swatch" style={{ background: row.color }} aria-hidden="true" />
            <div>
              <strong>{row.label}</strong>
              <span>{row.description}</span>
            </div>
          </li>
        ))}
      </ul>
    </article>
  );
}

export function EconomyCashFlowPanel({
  siteSlug,
  importCost,
  exportRevenue,
  netCost,
  totalSavings,
}: {
  siteSlug: string;
  importCost: number;
  exportRevenue: number;
  netCost: number;
  totalSavings: number;
}) {
  const rows = [
    { label: "Totala kostnader", value: -importCost },
    { label: "Såld el-intäkter", value: exportRevenue },
    { label: "Netto", value: -netCost },
    { label: "Besparing vs utan system", value: totalSavings },
  ];
  return (
    <article className="edash-panel edash-panel-cashflow" data-testid="economy-cashflow">
      <h3>KASSAFLÖDE</h3>
      <ul>
        {rows.map((row) => (
          <li key={row.label}>
            <span>{row.label}</span>
            <strong className={row.value >= 0 ? "is-pos" : "is-neg"}>
              {row.value >= 0 ? "+" : "−"}
              {formatEconomyKr(Math.abs(row.value))}
            </strong>
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="edash-outline-btn"
        onClick={() => navigateEconomySection(siteSlug, "cashflow")}
      >
        Visa kassaflödesrapport
      </button>
    </article>
  );
}

export function EconomyBudgetPanel({
  usedPct,
  spentSek,
  budgetSek,
  forecastSek,
  forecastDelta,
  forecastDeltaPct,
}: {
  usedPct: number;
  spentSek: number;
  budgetSek: number;
  forecastSek: number;
  forecastDelta: number;
  forecastDeltaPct: number;
}) {
  const angle = 180 * (usedPct / 100);
  const cx = 100;
  const cy = 100;
  const r = 70;
  const start = Math.PI;
  const end = Math.PI + (angle / 180) * Math.PI;
  const x1 = cx + r * Math.cos(start);
  const y1 = cy + r * Math.sin(start);
  const x2 = cx + r * Math.cos(end);
  const y2 = cy + r * Math.sin(end);
  const large = angle > 180 ? 1 : 0;
  const arc = `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;

  return (
    <article className="edash-panel edash-panel-budget" data-testid="economy-budget-panel">
      <h3>BUDGET &amp; PROGNOS</h3>
      <div className="edash-budget-body">
        <div className="edash-semi-gauge">
          <svg viewBox="0 0 200 110" aria-hidden="true">
            <path d="M 30 100 A 70 70 0 0 1 170 100" fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth="14" strokeLinecap="round" />
            <path d={arc} fill="none" stroke="#4ade80" strokeWidth="14" strokeLinecap="round" />
          </svg>
          <div className="edash-semi-gauge-center">
            <strong>{Math.round(usedPct)}%</strong>
            <span>Av budget</span>
            <em>{formatEconomyKr(spentSek)} / {formatEconomyKr(budgetSek)}</em>
          </div>
        </div>
        <div className="edash-budget-meta">
          <p><span>Prognos denna månad</span><strong>{formatEconomyKr(forecastSek)}</strong></p>
          <p>
            <span>Prognos avvikelse</span>
            <strong className={forecastDelta <= 0 ? "is-pos" : "is-neg"}>
              {forecastDelta <= 0 ? "" : "+"}
              {formatEconomyKr(forecastDelta)} ({forecastDeltaPct >= 0 ? "+" : ""}
              {Math.round(forecastDeltaPct)}%)
            </strong>
          </p>
        </div>
      </div>
    </article>
  );
}

export function EconomyInvestmentPanel({
  payback,
  ytdReturnPct,
  ytdBenefitSek,
  lifetimeBenefitSek,
}: {
  payback: PaybackMetrics;
  ytdReturnPct: number | null;
  ytdBenefitSek: number;
  lifetimeBenefitSek: number;
}) {
  const rows = [
    {
      label: "Investerat",
      value: payback.investmentSek != null ? formatEconomyKr(payback.investmentSek) : "Investering ej angiven",
    },
    {
      label: "Återbetalat",
      value: payback.investmentSek != null ? formatEconomyKr(payback.repaidSek) : formatEconomyKr(lifetimeBenefitSek),
    },
    {
      label: "Kvar",
      value:
        payback.remainingSek != null ? formatEconomyKr(payback.remainingSek) : "—",
    },
    {
      label: "Återbetalt",
      value: payback.repaidPct != null ? `${Math.round(payback.repaidPct)} %` : "—",
    },
    {
      label: "Beräknad återbetalningstid",
      value:
        payback.paybackYears != null
          ? `${payback.paybackYears.toFixed(1)} år${payback.isForecast ? " (Prognos)" : ""}`
          : "Beräknas när mer historik finns",
    },
    {
      label: "Avkastning YTD",
      value: ytdReturnPct != null ? `${ytdReturnPct.toFixed(1)} %` : "Investering ej angiven",
    },
    {
      label: "Besparing YTD",
      value: formatEconomyKr(ytdBenefitSek),
    },
    {
      label: "Besparing sedan installation",
      value: formatEconomyKr(lifetimeBenefitSek),
    },
  ];
  return (
    <article className="edash-panel edash-panel-investment" data-testid="economy-investment">
      <h3>INVESTERING &amp; AVKASTNING</h3>
      <dl>
        {rows.map((row) => (
          <div key={row.label}>
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

export function EconomyGoalsPanel({ goals }: { goals: EconomyGoal[] }) {
  return (
    <article className="edash-panel edash-panel-goals" data-testid="economy-goals">
      <h3>EKONOMIMÅL</h3>
      <ul>
        {goals.map((goal) => (
          <li key={goal.id} className={`edash-goal edash-goal-${goal.tone}`}>
            <div className="edash-goal-head">
              <span>{goal.label}</span>
              <em>{goal.targetLabel}</em>
            </div>
            <div className="edash-goal-bar">
              <div className="edash-goal-fill" style={{ width: `${Math.min(100, goal.valuePct)}%` }} />
            </div>
            <strong>{goal.displayValue}</strong>
          </li>
        ))}
      </ul>
    </article>
  );
}

export function EconomyInsightsPanel({
  siteSlug,
  insights,
}: {
  siteSlug: string;
  insights: EconomyInsight[];
}) {
  return (
    <article className="edash-panel edash-panel-insights" data-testid="economy-insights">
      <h3>SNABBINSIKTER</h3>
      <ul>
        {insights.map((item) => (
          <li key={item.id}>
            <span className="edash-insight-dot" aria-hidden="true" />
            {item.text}
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="edash-link-btn edash-link-btn-right"
        onClick={() => navigateEconomySection(siteSlug, "insights")}
      >
        Fler insikter
      </button>
    </article>
  );
}

export function EconomyDistributionLegend({ slices }: { slices: CostBreakdownSlice[] }) {
  return (
    <ul className="edash-donut-legend">
      {slices.map((slice) => (
        <li key={slice.id}>
          <i style={{ background: slice.color }} />
          <span>{slice.label}</span>
          <em>{Math.round(slice.pct)}%</em>
        </li>
      ))}
    </ul>
  );
}
