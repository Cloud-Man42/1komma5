"use client";

import { useEffect, useState } from "react";
import { HistoryResponse, SolarForecast, fetchSiteHistory, fetchSolarForecast } from "@/lib/api";
import { EnergyChart } from "@/components/EnergyChart";
import { DashboardSection, Skeleton } from "@/components/dashboard";

export function EnergyTodayChart({ siteSlug }: { siteSlug: string }) {
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [forecast, setForecast] = useState<SolarForecast | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([fetchSiteHistory(siteSlug, 5, 24), fetchSolarForecast(siteSlug).catch(() => null)])
      .then(([hist, solar]) => {
        if (!active) return;
        setHistory(hist);
        setForecast(solar);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [siteSlug]);

  return (
    <DashboardSection title="Energi idag" subtitle="Produktion och förbrukning">
      <div className="dashboard-surface">
        {loading ? (
          <Skeleton lines={5} />
        ) : (
          <EnergyChart readings={history?.readings ?? []} forecastPoints={forecast?.points ?? []} />
        )}
      </div>
    </DashboardSection>
  );
}
