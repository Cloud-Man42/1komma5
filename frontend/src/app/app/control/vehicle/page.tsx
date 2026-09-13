"use client";

import { MobileVehicleView } from "@/components/mobile/MobileControlViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { useAuth } from "@/lib/authContext";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";

export default function MobileVehiclePage() {
  const { can } = useAuth();
  const { selectedSlugs, accessibleSites } = useSiteSelection();
  const slugs = selectedSlugs.length ? selectedSlugs : accessibleSites.map((s) => s.slug);
  const siteNames = Object.fromEntries(accessibleSites.map((s) => [s.slug, s.name]));

  if (!can("dashboard.read")) {
    return <p className="mobile-error">You do not have permission to view vehicle.</p>;
  }

  return (
    <MobileSectionPage title="Vehicle" subtitle="Mercedes integration" backHref="/app/control">
      <MobileVehicleView slugs={slugs} siteNames={siteNames} />
    </MobileSectionPage>
  );
}
