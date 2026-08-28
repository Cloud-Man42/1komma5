"use client";

import { useParams } from "next/navigation";
import { IntelligenceOverviewLoader } from "@/components/intelligence-dashboard/IntelligenceOverview";
import { useSiteDashboard } from "@/lib/useSiteDashboard";

export default function SiteOverviewPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const { dashboard, error, loading } = useSiteDashboard(slug, 15);

  return (
    <IntelligenceOverviewLoader
      slug={slug}
      dashboard={dashboard}
      loading={loading}
      error={error}
    />
  );
}
