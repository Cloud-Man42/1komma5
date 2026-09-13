"use client";

import { TableSkeleton } from "@/components/admin-ui";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";
import type { MobileSummaryResponse } from "@/lib/mobileApi";
import { useMobileSummary } from "@/lib/useMobileSummary";

export function MobileSummaryLoader({
  children,
}: {
  children: (props: { data: MobileSummaryResponse; slugs: string[] }) => React.ReactNode;
}) {
  const { loading: selLoading, selectedSlugs, accessibleSites } = useSiteSelection();
  const slugs = selectedSlugs.length ? selectedSlugs : accessibleSites.map((s) => s.slug);
  const { data, loading, error, online } = useMobileSummary(slugs);

  if (selLoading || (loading && !data)) {
    return <TableSkeleton rows={6} />;
  }

  if (error && !data) {
    return <p className="mobile-error">{error}</p>;
  }

  if (!data) {
    return (
      <div className="mobile-empty">
        {!online ? <p>Offline — connect to load data.</p> : <p>Select at least one site.</p>}
      </div>
    );
  }

  return <>{children({ data, slugs })}</>;
}
