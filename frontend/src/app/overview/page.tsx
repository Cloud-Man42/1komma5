"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { OverviewCostBreakdown } from "@/components/multisite/OverviewCostBreakdown";
import { OverviewHeader } from "@/components/multisite/OverviewHeader";
import { OverviewLivePowerFlow } from "@/components/multisite/OverviewLivePowerFlow";
import { OverviewPowerBalance24h } from "@/components/multisite/OverviewPowerBalance24h";
import { OverviewSiteCard } from "@/components/multisite/OverviewSiteCard";
import { OverviewSiteVisibilityBar } from "@/components/multisite/OverviewSiteVisibilityBar";
import { SiteSelector } from "@/components/site-selector/SiteSelector";
import { EmptyState, TableSkeleton } from "@/components/admin-ui";
import {
  aggregateSiteCurrencies,
  aggregateSiteEntries,
  aggregateSiteHealth,
} from "@/lib/multiSiteClientAggregate";
import { buildSiteColorMap } from "@/lib/multiSiteSiteColors";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";
import { useMultiSiteHistory } from "@/lib/useMultiSiteHistory";
import { useMultiSiteOverview } from "@/lib/useMultiSiteOverview";

export default function MultiSiteOverviewPage() {
  const router = useRouter();
  const { loading: selLoading, selectedSlugs } = useSiteSelection();
  const { data, loading, error } = useMultiSiteOverview(selectedSlugs);
  const [visibleSlugs, setVisibleSlugs] = useState<string[]>([]);
  const [highlightedSlug, setHighlightedSlug] = useState<string | null>(null);

  const siteSlugKey = data?.sites?.map((s) => s.slug).sort().join("\0") ?? "";

  useEffect(() => {
    if (!siteSlugKey) return;
    setVisibleSlugs(siteSlugKey.split("\0"));
    setHighlightedSlug(null);
  }, [siteSlugKey]);

  const visibleSites = useMemo(
    () => (data ? data.sites.filter((s) => visibleSlugs.includes(s.slug)) : []),
    [data, visibleSlugs],
  );
  const visibleAggregate = useMemo(() => aggregateSiteEntries(visibleSites), [visibleSites]);
  const siteColors = useMemo(
    () => (data ? buildSiteColorMap(data.sites.map((s) => s.slug)) : {}),
    [data],
  );

  const { points: historyPoints, loading: historyLoading } = useMultiSiteHistory(visibleSlugs);

  useEffect(() => {
    if (selLoading) return;
    if (selectedSlugs.length === 0) return;
    if (selectedSlugs.length === 1) {
      router.replace(`/sites/${selectedSlugs[0]}`);
    }
  }, [selLoading, selectedSlugs, router]);

  const toggleSite = (slug: string) => {
    setVisibleSlugs((prev) => {
      if (prev.includes(slug)) {
        const next = prev.filter((s) => s !== slug);
        return next.length === 0 ? prev : next;
      }
      return [...prev, slug];
    });
    setHighlightedSlug((current) => (current === slug ? null : current));
  };

  const isolateSite = (slug: string) => {
    setVisibleSlugs([slug]);
    setHighlightedSlug(slug);
  };

  const showAllSites = () => {
    if (data) setVisibleSlugs(data.sites.map((s) => s.slug));
    setHighlightedSlug(null);
  };

  if (selLoading) return <TableSkeleton rows={6} />;

  if (selectedSlugs.length < 2) {
    return (
      <div className="ms-overview">
        <EmptyState
          title="Välj anläggningar"
          text="Markera minst två anläggningar för att skapa en samlad översikt."
          action={<SiteSelector />}
        />
      </div>
    );
  }

  if (loading && !data) return <div className="ms-overview"><TableSkeleton rows={8} /></div>;
  if (error) return <div className="ms-overview"><p className="error-text">{error}</p></div>;
  if (!data) return null;

  const filteredData = {
    ...data,
    aggregate: visibleAggregate,
    sites: visibleSites,
    currencies: aggregateSiteCurrencies(visibleSites),
    health: aggregateSiteHealth(visibleSites),
  };
  const historySiteSeries = visibleSites.map((site) => ({
    slug: site.slug,
    name: site.name,
    color: siteColors[site.slug],
  }));

  return (
    <div className="ms-overview">
      <OverviewHeader data={filteredData} totalSiteCount={data.sites.length} />
      <OverviewSiteVisibilityBar
        sites={data.sites}
        visibleSlugs={visibleSlugs}
        onToggle={toggleSite}
        onShowAll={showAllSites}
        onIsolate={isolateSite}
      />
      {visibleSites.length === 0 ? (
        <EmptyState title="Inga anläggningar valda" text="Aktivera minst en anläggning ovan." />
      ) : (
        <>
          <div className="ms-overview-main-grid">
            <OverviewLivePowerFlow
              aggregate={visibleAggregate}
              sites={visibleSites}
              allSites={data.sites}
              highlightedSlug={highlightedSlug}
            />
            <OverviewPowerBalance24h
              aggregate={visibleAggregate}
              points={historyPoints}
              loading={historyLoading}
              siteSeries={historySiteSeries.length > 1 ? historySiteSeries : []}
            />
          </div>
          <OverviewCostBreakdown data={filteredData} />
          <div className="ms-site-cards">
            {data.sites.map((site) => {
              const visible = visibleSlugs.includes(site.slug);
              return (
                <div
                  key={site.slug}
                  className={visible ? undefined : "ms-site-card-hidden"}
                  onMouseEnter={() => setHighlightedSlug(site.slug)}
                  onMouseLeave={() => setHighlightedSlug(null)}
                >
                  <OverviewSiteCard site={site} color={siteColors[site.slug]} />
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
