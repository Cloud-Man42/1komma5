"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchMultiSiteOverview, type MultiSiteOverviewResponse } from "@/lib/multiSiteApi";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

export function useMultiSiteOverview(siteSlugs: string[]) {
  const refreshSeconds = useDashboardRefreshSeconds();
  const [data, setData] = useState<MultiSiteOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (siteSlugs.length < 2) {
      setData(null);
      setLoading(false);
      return;
    }
    try {
      const overview = await fetchMultiSiteOverview(siteSlugs);
      setData(overview);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda översikt");
    } finally {
      setLoading(false);
    }
  }, [siteSlugs]);

  useEffect(() => {
    setLoading(true);
    void load();
    const id = window.setInterval(() => void load(), refreshSeconds * 1000);
    return () => window.clearInterval(id);
  }, [load, refreshSeconds]);

  return { data, loading, error, refresh: load };
}
