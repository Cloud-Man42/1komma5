"use client";

import { exportFinancialCsv, formatEconomyKr } from "./economyDashboardHelpers";
import type { FinancialStat } from "@/lib/api";

export function EconomyReportsSection({
  stats,
  siteSlug,
}: {
  stats: FinancialStat[];
  siteSlug: string;
}) {
  return (
    <section className="edash-section" data-testid="economy-reports-section">
      <header className="edash-section-head">
        <h2>Rapporter</h2>
        <p>Detaljerad ekonomisk statistik för {siteSlug}.</p>
      </header>
      <div className="edash-reports-toolbar">
        <button
          type="button"
          className="edash-outline-btn"
          onClick={() => exportFinancialCsv(stats)}
          disabled={stats.length === 0}
        >
          Exportera CSV
        </button>
      </div>
      {stats.length === 0 ? (
        <p className="edash-muted">Ingen rapportdata tillgänglig.</p>
      ) : (
        <div className="edash-table-wrap">
          <table className="edash-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Solbesparing</th>
                <th>Batteri</th>
                <th>Export</th>
                <th>Elkostnad</th>
                <th>Netto</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((row) => {
                const net =
                  row.solar_savings_sek +
                  row.battery_savings_sek +
                  row.export_revenue_sek -
                  row.grid_import_cost_sek;
                return (
                  <tr key={row.period_start}>
                    <td>{row.period_start}</td>
                    <td>{formatEconomyKr(row.solar_savings_sek)}</td>
                    <td>{formatEconomyKr(row.battery_savings_sek)}</td>
                    <td>{formatEconomyKr(row.export_revenue_sek)}</td>
                    <td>{formatEconomyKr(row.grid_import_cost_sek)}</td>
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
