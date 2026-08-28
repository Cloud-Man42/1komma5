"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";

const SolarOverview = dynamic(
  () => import("@/components/solar-dashboard/SolarOverview").then((m) => m.SolarOverview),
  { ssr: false, loading: () => <p>Laddar solvy…</p> },
);

export default function SiteSolarPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;

  return <SolarOverview siteSlug={slug} />;
}
