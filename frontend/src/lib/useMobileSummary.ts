"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchMobileSummary, type MobileSummaryResponse } from "@/lib/mobileApi";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";
import { useOnlineStatus } from "@/lib/useOnlineStatus";

export function useMobileSummary(siteSlugs: string[]) {
  const refreshSeconds = useDashboardRefreshSeconds();
  const online = useOnlineStatus();
  const [data, setData] = useState<MobileSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const slugKey = siteSlugs.slice().sort().join("\0");

  const load = useCallback(async () => {
    if (siteSlugs.length === 0) {
      setData(null);
      setLoading(false);
      return;
    }
    if (!online) {
      setLoading(false);
      return;
    }
    try {
      const summary = await fetchMobileSummary(siteSlugs);
      setData(summary);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda sammanfattning");
    } finally {
      setLoading(false);
    }
  }, [siteSlugs, online]);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load, slugKey]);

  useEffect(() => {
    if (!online) return;
    const tick = () => {
      if (document.visibilityState === "visible") void load();
    };
    const id = window.setInterval(tick, refreshSeconds * 1000);
    return () => window.clearInterval(id);
  }, [load, refreshSeconds, online]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible" && online) void load();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [load, online]);

  return { data, loading, error, refresh: load, online };
}
