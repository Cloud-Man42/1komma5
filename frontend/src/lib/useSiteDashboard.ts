import { useCallback, useEffect, useState } from "react";
import { SiteDashboard, fetchSiteDashboard } from "@/lib/api";

const DEFAULT_REFRESH_SECONDS = 15;

export function useSiteDashboard(slug: string, refreshSeconds = DEFAULT_REFRESH_SECONDS) {
  const [dashboard, setDashboard] = useState<SiteDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
    setLoading(true);
    load();
    const interval = setInterval(load, refreshSeconds * 1000);
    return () => clearInterval(interval);
  }, [load, refreshSeconds]);

  return { dashboard, error, loading, reload: load };
}
