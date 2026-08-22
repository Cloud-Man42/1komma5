"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { EnergyChart } from "@/components/EnergyChart";
import { SolarForecastCard } from "@/components/SolarForecastCard";
import { HistoryResponse, SolarForecast, fetchSiteHistory, fetchSolarForecast } from "@/lib/api";

export default function SiteSolarPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [forecast, setForecast] = useState<SolarForecast | null>(null);

  useEffect(() => {
    Promise.all([
      fetchSiteHistory(slug, 5, 24),
      fetchSolarForecast(slug).catch(() => null),
    ]).then(([hist, solar]) => {
      setHistory(hist);
      setForecast(solar);
    });
  }, [slug]);

  return (
    <>
      <h2 className="page-title">Sol</h2>
      <SolarForecastCard siteSlug={slug} />
      <EnergyChart readings={history?.readings ?? []} forecastPoints={forecast?.points ?? []} />
    </>
  );
}
