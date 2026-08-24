"use client";

import { ReactNode } from "react";
import { useParams } from "next/navigation";
import { SiteTabs } from "@/components/dashboard/SiteNavigation";
import { useSiteDashboard } from "@/lib/useSiteDashboard";

export default function SiteLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const { dashboard } = useSiteDashboard(slug, 60);

  return (
    <section>
      <SiteTabs slug={slug} spaEnabled={dashboard?.spa_integration_enabled} vehicleEnabled={dashboard?.vehicle_integration_enabled} />
      {children}
    </section>
  );
}
