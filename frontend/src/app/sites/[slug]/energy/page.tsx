"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";

const EnergyOverview = dynamic(
  () => import("@/components/energy-dashboard/EnergyOverview").then((m) => m.EnergyOverview),
  { ssr: false, loading: () => <p>Laddar energivy…</p> },
);

export default function SiteEnergyPage() {
  const params = useParams<{ slug: string }>();
  return <EnergyOverview siteSlug={params.slug} />;
}
