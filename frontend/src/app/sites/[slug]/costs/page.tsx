"use client";

import { useParams } from "next/navigation";
import { EconomyOverview } from "@/components/economy-dashboard/EconomyOverview";

export default function SiteCostsPage() {
  const params = useParams<{ slug: string }>();
  return <EconomyOverview siteSlug={params.slug} />;
}
