"use client";

import { useEffect, useState } from "react";
import {
  fetchSpaEconomics,
  fetchSpaEnergyBreakdown,
  fetchSpaEnergyPeriod,
  type SpaEconomics,
  type SpaEnergyBreakdown,
  type SpaEnergyPeriod,
} from "@/lib/api";

function economicsPeriodForAnalysis(period: string): string {
  if (period === "today") return "today";
  if (period === "month" || period === "week") return "month";
  return "year";
}

export function useSpaDetailedAnalysisData(siteSlug: string, period: string) {
  const [energy, setEnergy] = useState<SpaEnergyPeriod | null>(null);
  const [breakdown, setBreakdown] = useState<SpaEnergyBreakdown | null>(null);
  const [economics, setEconomics] = useState<SpaEconomics | null>(null);
  const [breakdownError, setBreakdownError] = useState<string | null>(null);
  const [economicsError, setEconomicsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setBreakdownError(null);
    setEconomicsError(null);

    const economicsPeriod = economicsPeriodForAnalysis(period);

    Promise.all([
      fetchSpaEnergyPeriod(siteSlug, period).catch(() => null),
      fetchSpaEnergyBreakdown(siteSlug, period).catch((err: unknown) => {
        if (active) {
          setBreakdownError(err instanceof Error ? err.message : "Kunde inte ladda energifördelning");
        }
        return null;
      }),
      fetchSpaEconomics(siteSlug, economicsPeriod).catch((err: unknown) => {
        if (active) {
          setEconomicsError(err instanceof Error ? err.message : "Kunde inte ladda ekonomi");
        }
        return null;
      }),
    ]).then(([energyData, breakdownData, economicsData]) => {
      if (!active) return;
      setEnergy(energyData);
      setBreakdown(breakdownData);
      setEconomics(economicsData);
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [siteSlug, period]);

  return { energy, breakdown, economics, breakdownError, economicsError, loading };
}
