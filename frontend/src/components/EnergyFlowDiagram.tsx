"use client";

import type { DashboardSolarSection, DashboardTodaySection, Reading } from "@/lib/api";
import { EnergyGaugePanel } from "@/components/EnergyGaugePanel";

interface EnergyFlowDiagramProps {
  reading: Reading;
  size?: "compact" | "full";
  siteSlug?: string;
  evPowerW?: number;
  solar?: DashboardSolarSection | null;
  today?: DashboardTodaySection | null;
  mainFuseA?: number | null;
}

/** Live site energy — analog boost-style power gauges. */
export function EnergyFlowDiagram({
  reading,
  size = "full",
  evPowerW = 0,
  solar = null,
  today = null,
  mainFuseA = null,
}: EnergyFlowDiagramProps) {
  const compact = size === "compact";

  return (
    <div
      className={`energy-flow energy-flow-gauges ${compact ? "energy-flow-compact" : "energy-flow-full"}`}
      aria-label="Energiflöde visualisering"
    >
      <EnergyGaugePanel
        reading={reading}
        compact={compact}
        evPowerW={evPowerW}
        solar={solar}
        today={today}
        mainFuseA={mainFuseA}
      />
    </div>
  );
}
