"use client";

import { useParams } from "next/navigation";
import { EvOverview } from "@/components/ev-dashboard/EvOverview";

export default function SiteEvPage() {
  const params = useParams<{ slug: string }>();
  return <EvOverview siteSlug={params.slug} />;
}
