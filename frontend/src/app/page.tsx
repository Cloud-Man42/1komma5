"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SiteOverviewCard } from "@/components/dashboard/SiteOverviewCard";
import { ErrorState, Skeleton } from "@/components/dashboard";
import { SiteSelector } from "@/components/site-selector/SiteSelector";
import { Site, fetchSites } from "@/lib/api";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";
import { useMobileShell } from "@/lib/useMobileShell";

export default function DashboardPage() {
  const router = useRouter();
  const mobileShell = useMobileShell();
  const { loading: selLoading, selectedSlugs } = useSiteSelection();
  const [sites, setSites] = useState<Site[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshSeconds = useDashboardRefreshSeconds();

  useEffect(() => {
    if (selLoading) return;
    if (mobileShell) {
      router.replace("/app");
      return;
    }
    if (selectedSlugs.length > 1) {
      router.replace("/overview");
    } else if (selectedSlugs.length === 1) {
      router.replace(`/sites/${selectedSlugs[0]}`);
    }
  }, [selLoading, selectedSlugs, router, mobileShell]);

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
        if (!active) return;
        const message = e instanceof Error ? e.message : "Kunde inte ladda anläggningar";
        if (message.includes("401")) {
          setError("Admin-token saknas. Ange token i dialogrutan ovan, eller gå till Konfiguration → Admin-token.");
          return;
        }
        setError(message);
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

  if (loading || selLoading) {
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
      <div className="ms-overview-header-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p className="muted page-intro">Live översikt — uppdateras var {refreshSeconds} s</p>
        <SiteSelector />
      </div>
      <div className="grid">
        {sites.map((site) => (
          <SiteOverviewCard key={site.slug} site={site} />
        ))}
      </div>
    </section>
  );
}
