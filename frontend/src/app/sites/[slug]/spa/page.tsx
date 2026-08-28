"use client";

import { useParams } from "next/navigation";
import { SpaOverview } from "@/components/spa-dashboard/SpaOverview";

export default function SiteSpaPage() {
  const params = useParams<{ slug: string }>();
  return <SpaOverview siteSlug={params.slug} />;
}
