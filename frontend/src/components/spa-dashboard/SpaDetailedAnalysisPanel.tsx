"use client";

import { useState } from "react";
import { SpaEnergyAnalysis } from "@/components/SpaEnergyAnalysis";
import { SpaEnergyBreakdown } from "@/components/SpaEnergyBreakdown";
import { SpaEconomicsPanel } from "@/components/spa/SpaEconomicsPanel";
import { useSpaDetailedAnalysisData } from "./useSpaDetailedAnalysisData";

const PERIOD_TABS = [
  { id: "today", label: "Idag" },
  { id: "week", label: "Vecka" },
  { id: "month", label: "Månad" },
  { id: "year", label: "År" },
  { id: "total", label: "Totalt" },
] as const;

function economicsPeriodForAnalysis(period: string): string {
  if (period === "today") return "today";
  if (period === "month" || period === "week") return "month";
  return "year";
}

export function SpaDetailedAnalysisPanel({ siteSlug }: { siteSlug: string }) {
  const [period, setPeriod] = useState<string>("month");
  const { energy, breakdown, economics, breakdownError, economicsError, loading } =
    useSpaDetailedAnalysisData(siteSlug, period);

  return (
    <div className="sdash-analysis-panel" data-testid="spa-detailed-analysis">
      <div className="sdash-analysis-tabs" role="tablist" aria-label="Analysperiod">
        {PERIOD_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={period === tab.id}
            className={period === tab.id ? "is-active" : ""}
            onClick={() => setPeriod(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {loading ? <p className="muted">Laddar analys…</p> : null}
      <SpaEnergyAnalysis siteSlug={siteSlug} period={period} data={energy} />
      <SpaEnergyBreakdown
        siteSlug={siteSlug}
        period={period}
        data={breakdown}
        error={breakdownError}
      />
      <SpaEconomicsPanel
        siteSlug={siteSlug}
        period={economicsPeriodForAnalysis(period)}
        data={economics}
        error={economicsError}
      />
    </div>
  );
}
