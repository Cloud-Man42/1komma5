"use client";

import { useEffect, useState } from "react";
import { SiteOverviewCard } from "@/components/dashboard/SiteOverviewCard";
import { ErrorState, Skeleton } from "@/components/dashboard";
import { Site, fetchSites } from "@/lib/api";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

export default function DashboardPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshSeconds = useDashboardRefreshSeconds();

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await fetchSites();
        if (active) {
          setSites(data);
          setError(null);
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Kunde inte ladda anläggningar");
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, refreshSeconds * 1000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [refreshSeconds]);

  if (loading) {
    return (
      <div className="dashboard-surface">
        <Skeleton lines={4} />
      </div>
    );
  }

  if (error) {
    return <ErrorState title="Kunde inte ladda dashboard" text={error} />;
  }

  return (
    <section>
      <p className="muted page-intro">Live översikt — uppdateras var {refreshSeconds} s</p>
      <div className="grid">
        {sites.map((site) => (
          <SiteOverviewCard key={site.slug} site={site} />
        ))}
      </div>
    </section>
  );
}
