import { useCallback, useEffect, useState } from "react";
import { SiteDashboard, fetchSiteDashboard } from "@/lib/api";
import { useOptionalSiteData } from "@/lib/SiteDataProvider";

const DEFAULT_REFRESH_SECONDS = 15;

export function useSiteDashboard(slug: string, refreshSeconds = DEFAULT_REFRESH_SECONDS) {
  const shared = useOptionalSiteData();
  const [dashboard, setDashboard] = useState<SiteDashboard | null>(shared?.dashboard ?? null);
  const [error, setError] = useState<string | null>(shared?.error ?? null);
  const [loading, setLoading] = useState(shared ? shared.loading : true);

  const load = useCallback(async () => {
    try {
      const data = await fetchSiteDashboard(slug);
      setDashboard(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte ladda dashboard");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    if (shared) {
      setDashboard(shared.dashboard);
      setError(shared.error);
      setLoading(shared.loading);
      return;
    }
    setLoading(true);
    load();
    const interval = setInterval(load, refreshSeconds * 1000);
    return () => clearInterval(interval);
  }, [shared, load, refreshSeconds]);

  if (shared) {
    return shared;
  }

  return { dashboard, error, loading, reload: load };
}
