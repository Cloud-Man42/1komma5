"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { FinancialStatsView } from "@/components/FinancialStatsView";
import { PriceChart } from "@/components/PriceChart";
import { YearForecastView } from "@/components/YearForecastView";
import { MarketPricesResponse, fetchMarketPrices } from "@/lib/api";

export default function SiteCostsPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [marketPrices, setMarketPrices] = useState<MarketPricesResponse | null>(null);
  const [priceError, setPriceError] = useState<string | null>(null);

  useEffect(() => {
    fetchMarketPrices(slug, 24)
      .then((prices) => {
        setMarketPrices(prices);
        setPriceError(null);
      })
      .catch((error) => {
        setMarketPrices(null);
        setPriceError(error instanceof Error ? error.message : "Kunde inte ladda elpriser");
      });
  }, [slug]);

  return (
    <>
      <h2 className="page-title">Ekonomi</h2>
      {priceError ? <p className="muted">Elpris: {priceError}</p> : <PriceChart prices={marketPrices} />}
      <FinancialStatsView siteSlug={slug} />
      <YearForecastView siteSlug={slug} />
    </>
  );
}
