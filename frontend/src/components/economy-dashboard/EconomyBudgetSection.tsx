"use client";

import { EconomyBudgetPanel, EconomyGoalsPanel } from "./EconomyAnalysisPanels";

export function EconomyBudgetSection({
  usedPct,
  spentSek,
  budgetSek,
  forecastSek,
  forecastDelta,
  forecastDeltaPct,
  goals,
}: {
  usedPct: number;
  spentSek: number;
  budgetSek: number;
  forecastSek: number;
  forecastDelta: number;
  forecastDeltaPct: number;
  goals: Parameters<typeof EconomyGoalsPanel>[0]["goals"];
}) {
  return (
    <section className="edash-section" data-testid="economy-budget-section">
      <header className="edash-section-head">
        <h2>Budget &amp; mål</h2>
        <p>Följ upp månadskostnad och dina energimål.</p>
      </header>
      <div className="edash-budget-grid">
        <EconomyBudgetPanel
          usedPct={usedPct}
          spentSek={spentSek}
          budgetSek={budgetSek}
          forecastSek={forecastSek}
          forecastDelta={forecastDelta}
          forecastDeltaPct={forecastDeltaPct}
        />
        <EconomyGoalsPanel goals={goals} />
      </div>
    </section>
  );
}
