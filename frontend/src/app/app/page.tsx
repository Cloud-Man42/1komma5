"use client";

import { TableSkeleton } from "@/components/admin-ui";
import {
  MobileBatterySummary,
  MobileDailySummary,
  MobileEnergyFlow,
  MobileHeroStatus,
  MobileQuickActions,
  MobileSiteCards,
  MobileStatusHeader,
  MobileWarnings,
} from "@/components/mobile/MobileHomeSections";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";
import { useMobileSummary } from "@/lib/useMobileSummary";

export default function MobileHomePage() {
  const { loading: selLoading, selectedSlugs, accessibleSites } = useSiteSelection();
  const slugs = selectedSlugs.length ? selectedSlugs : accessibleSites.map((s) => s.slug);
  const { data, loading, error, online } = useMobileSummary(slugs);

  if (selLoading || (loading && !data)) {
    return <TableSkeleton rows={8} />;
  }

  if (error && !data) {
    return <p className="mobile-error">{error}</p>;
  }

  if (!data) {
    return (
      <div className="mobile-empty">
        {!online ? <p>Offline — connect to load live summary.</p> : <p>Select at least one site.</p>}
      </div>
    );
  }

  return (
    <div className="mobile-home">
      <MobileStatusHeader data={data} />
      <MobileHeroStatus data={data} />
      <MobileEnergyFlow data={data} />
      <MobileDailySummary data={data} />
      <MobileBatterySummary data={data} />
      <MobileWarnings data={data} />
      <MobileQuickActions data={data} />
      <MobileSiteCards data={data} />
      {data.dataQuality.partial ? (
        <p className="mobile-partial" role="status">
          {data.dataQuality.message ?? "Partial data from some sites"}
        </p>
      ) : null}
    </div>
  );
}
