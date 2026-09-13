"use client";

import { MobileSpaView } from "@/components/mobile/MobileControlViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { useAuth } from "@/lib/authContext";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";

export default function MobileSpaPage() {
  const { can } = useAuth();
  const { selectedSlugs, accessibleSites } = useSiteSelection();
  const slugs = selectedSlugs.length ? selectedSlugs : accessibleSites.map((s) => s.slug);
  const siteNames = Object.fromEntries(accessibleSites.map((s) => [s.slug, s.name]));

  if (!can("spa.read")) {
    return <p className="mobile-error">You do not have permission to view SPA.</p>;
  }

  return (
    <MobileSectionPage title="SPA" subtitle="Pool heating and control" backHref="/app/control">
      <MobileSpaView slugs={slugs} siteNames={siteNames} />
    </MobileSectionPage>
  );
}
