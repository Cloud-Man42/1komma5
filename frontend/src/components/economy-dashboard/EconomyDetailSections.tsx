"use client";

import { PriceChart } from "@/components/PriceChart";
import type { FinancialStat, MarketPricesResponse } from "@/lib/api";
import { formatPriceOre } from "./economyDashboardHelpers";
import { marketPointImportOre, marketPointSpotOre } from "@/lib/prices";
import type { EconomyInsight, PriceAnalysis } from "./economyDashboardHelpers";
import { exportFinancialCsv, formatEconomyKr } from "./economyDashboardHelpers";
import { navigateEconomySection } from "./economySection";

function BackToAnalysis({ siteSlug }: { siteSlug: string }) {
  return (
    <button type="button" className="edash-link-btn edash-back-link" onClick={() => navigateEconomySection(siteSlug, "analysis")}>
      ← Tillbaka till översikt
    </button>
  );
}

export function EconomyCashFlowSection({
  stats,
  siteSlug,
  importCost,
  exportRevenue,
  netCost,
  totalSavings,
}: {
  stats: FinancialStat[];
  siteSlug: string;
  importCost: number;
  exportRevenue: number;
  netCost: number;
  totalSavings: number;
}) {
  const summary = [
    { label: "Totala kostnader", value: -importCost },
    { label: "Såld el-intäkter", value: exportRevenue },
    { label: "Netto", value: -netCost },
    { label: "Besparing vs utan system", value: totalSavings },
  ];

  return (
    <section className="edash-section" data-testid="economy-cashflow-section">
      <BackToAnalysis siteSlug={siteSlug} />
      <header className="edash-section-head">
        <h2>Kassaflödesrapport</h2>
        <p>Daglig kassaflödesuppdelning för {siteSlug}.</p>
      </header>
      <div className="edash-panel edash-panel-cashflow edash-cashflow-summary">
        <ul>
          {summary.map((row) => (
            <li key={row.label}>
              <span>{row.label}</span>
              <strong className={row.value >= 0 ? "is-pos" : "is-neg"}>
                {row.value >= 0 ? "+" : "−"}
                {formatEconomyKr(Math.abs(row.value))}
              </strong>
            </li>
          ))}
        </ul>
      </div>
      <div className="edash-reports-toolbar">
        <button
          type="button"
          className="edash-outline-btn"
          onClick={() => exportFinancialCsv(stats, "kassaflode-rapport.csv")}
          disabled={stats.length === 0}
        >
          Exportera kassaflöde
        </button>
      </div>
      {stats.length === 0 ? (
        <p className="edash-muted">Ingen kassaflödesdata tillgänglig.</p>
      ) : (
        <div className="edash-table-wrap">
          <table className="edash-table">
            <thead>
              <tr>
                <th>Dag</th>
                <th>Kostnad</th>
                <th>Intäkt</th>
                <th>Besparing</th>
                <th>Netto</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((row) => {
                const savings = row.solar_savings_sek + row.battery_savings_sek;
                const net = row.export_revenue_sek - row.grid_import_cost_sek + savings;
                return (
                  <tr key={row.period_start}>
                    <td>{row.period_start}</td>
                    <td>{formatEconomyKr(row.grid_import_cost_sek)}</td>
                    <td>{formatEconomyKr(row.export_revenue_sek)}</td>
                    <td>{formatEconomyKr(savings)}</td>
                    <td className={net >= 0 ? "is-pos" : "is-neg"}>{formatEconomyKr(net)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function EconomyInsightsDetailSection({
  insights,
  siteSlug,
}: {
  insights: EconomyInsight[];
  siteSlug: string;
}) {
  return (
    <section className="edash-section" data-testid="economy-insights-section">
      <BackToAnalysis siteSlug={siteSlug} />
      <header className="edash-section-head">
        <h2>Insikter</h2>
        <p>Alla ekonomiska insikter för denna period.</p>
      </header>
      <article className="edash-panel edash-panel-insights edash-insights-detail">
        <ul>
          {insights.length === 0 ? (
            <li className="edash-muted">Inga insikter tillgängliga ännu.</li>
          ) : (
            insights.map((item) => (
              <li key={item.id}>
                <span className="edash-insight-dot" aria-hidden="true" />
                {item.text}
              </li>
            ))
          )}
        </ul>
      </article>
    </section>
  );
}

export function EconomyPriceDetailsSection({
  siteSlug,
  marketPrices,
  priceAnalysis,
  timezone,
}: {
  siteSlug: string;
  marketPrices: MarketPricesResponse | null;
  priceAnalysis: PriceAnalysis;
  timezone: string;
}) {
  const points = marketPrices?.points ?? [];

  return (
    <section className="edash-section" data-testid="economy-price-details-section">
      <BackToAnalysis siteSlug={siteSlug} />
      <header className="edash-section-head">
        <h2>Prisdetaljer</h2>
        <p>Timvis elpris och snitt för {siteSlug}.</p>
      </header>
      <div className="edash-price-details-grid">
        <article className="edash-panel edash-panel-prices">
          <h3>SNITT &amp; EXTREMVÄRDEN</h3>
          <dl className="edash-price-list">
            <div><dt>Spotpris (snitt)</dt><dd>{formatPriceOre(priceAnalysis.spotOre)}</dd></div>
            <div><dt>Köpt pris</dt><dd>{formatPriceOre(priceAnalysis.purchaseOre)}</dd></div>
            <div><dt>Sålt pris</dt><dd>{formatPriceOre(priceAnalysis.exportOre)}</dd></div>
          </dl>
          <div className="edash-price-extremes">
            <p><span>Billigaste timme</span><strong>{formatPriceOre(priceAnalysis.cheapestOre)}</strong><em>{priceAnalysis.cheapestAt ?? "—"}</em></p>
            <p><span>Dyraste timme</span><strong>{formatPriceOre(priceAnalysis.expensiveOre)}</strong><em>{priceAnalysis.expensiveAt ?? "—"}</em></p>
          </div>
        </article>
        <article className="edash-panel edash-panel-chart-wide">
          <h3>ELPRIS — KOMMANDE TIMMAR</h3>
          <PriceChart prices={marketPrices} />
        </article>
      </div>
      {points.length > 0 ? (
        <div className="edash-table-wrap">
          <table className="edash-table">
            <thead>
              <tr>
                <th>Tid</th>
                <th>Spot (öre/kWh)</th>
                <th>All-in (öre/kWh)</th>
              </tr>
            </thead>
            <tbody>
              {points.slice(0, 48).map((point) => (
                <tr key={point.timestamp}>
                  <td>
                    {new Date(point.timestamp).toLocaleString("sv-SE", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                      timeZone: timezone,
                    })}
                  </td>
                  <td>{marketPointSpotOre(point) ?? "—"}</td>
                  <td>{marketPointImportOre(point) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="edash-muted">Ingen timprisdata tillgänglig.</p>
      )}
    </section>
  );
}
