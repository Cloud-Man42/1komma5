"use client";

import { useState } from "react";
import { SpaEnergyAnalysis } from "@/components/SpaEnergyAnalysis";
import { SpaEnergyBreakdown } from "@/components/SpaEnergyBreakdown";
import { SpaEconomicsPanel } from "@/components/spa/SpaEconomicsPanel";

const PERIOD_TABS = [
  { id: "today", label: "Idag" },
  { id: "week", label: "Vecka" },
  { id: "month", label: "Månad" },
  { id: "year", label: "År" },
  { id: "total", label: "Totalt" },
] as const;

export function SpaDetailedAnalysisPanel({ siteSlug }: { siteSlug: string }) {
  const [period, setPeriod] = useState<string>("month");

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
      <SpaEnergyAnalysis siteSlug={siteSlug} period={period} />
      <SpaEnergyBreakdown siteSlug={siteSlug} period={period} />
      <SpaEconomicsPanel siteSlug={siteSlug} />
    </div>
  );
}
