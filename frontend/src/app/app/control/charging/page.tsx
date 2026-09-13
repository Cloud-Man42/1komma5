"use client";

import { MobileChargingView } from "@/components/mobile/MobileControlViews";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { useAuth } from "@/lib/authContext";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";

export default function MobileChargingPage() {
  const { can } = useAuth();
  const { selectedSlugs, accessibleSites } = useSiteSelection();
  const slugs = selectedSlugs.length ? selectedSlugs : accessibleSites.map((s) => s.slug);
  const siteNames = Object.fromEntries(accessibleSites.map((s) => [s.slug, s.name]));

  if (!can("charging.read")) {
    return <p className="mobile-error">You do not have permission to view charging.</p>;
  }

  return (
    <MobileSectionPage title="Charging" subtitle="EV and smart charging" backHref="/app/control">
      <MobileChargingView slugs={slugs} siteNames={siteNames} />
    </MobileSectionPage>
  );
}
