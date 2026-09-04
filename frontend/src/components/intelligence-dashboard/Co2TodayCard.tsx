"use client";

import type { DashboardTodaySection } from "@/lib/api";
import { estimateCo2AvoidedKg, formatCo2AvoidedKg } from "@/lib/co2SavingsHelpers";

export function Co2TodayCard({ today }: { today: DashboardTodaySection | null }) {
  const kg = estimateCo2AvoidedKg(today?.produced_kwh ?? null);

  return (
    <section className="idash-panel" data-testid="co2-today-card">
      <h2 className="idash-panel-title">CO₂ undvikt idag</h2>
      <p className="idash-co2-value">{formatCo2AvoidedKg(kg)}</p>
      <p className="muted idash-co2-caption">
        Uppskattning från egen solproduktion (nätmix ~45 g/kWh).
      </p>
    </section>
  );
}
