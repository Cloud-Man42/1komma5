"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchMultiSiteHistory, type MultiSiteHistoryPoint } from "@/lib/multiSiteHistory";

export function useMultiSiteHistory(siteSlugs: string[]) {
  const [points, setPoints] = useState<MultiSiteHistoryPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (siteSlugs.length < 2) {
      setPoints([]);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchMultiSiteHistory(siteSlugs, 15, 24);
      setPoints(data);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Kunde inte ladda historik.");
      setPoints([]);
    } finally {
      setLoading(false);
    }
  }, [siteSlugs]);

  useEffect(() => {
    void reload();
    const timer = setInterval(() => void reload(), 60_000);
    return () => clearInterval(timer);
  }, [reload]);

  return { points, loading, error, reload };
}
