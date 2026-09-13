import type { MultiSiteOverviewResponse } from "@/lib/multiSiteApi";

export function OverviewCostBreakdown({ data }: { data: MultiSiteOverviewResponse }) {
  if (!data.currencies.length) return null;

  return (
    <section className="ms-cost-breakdown">
      <h2>Energikostnad idag</h2>
      <ul>
        {data.currencies.map((row) => (
          <li key={row.currency}>
            <strong>{row.currency}</strong> — Kostnad: {row.costToday ?? "—"} · Besparing: {row.savingsToday ?? "—"}
          </li>
        ))}
      </ul>
      {data.currencies.length > 1 ? (
        <p className="muted">Valutor summeras inte — visar uppdelning per valuta.</p>
      ) : null}
    </section>
  );
}
