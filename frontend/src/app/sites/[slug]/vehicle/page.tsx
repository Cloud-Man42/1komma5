"use client";

import { useParams } from "next/navigation";
import { VehiclePanel } from "@/components/VehiclePanel";

export default function SiteVehiclePage() {
  const params = useParams<{ slug: string }>();
  return (
    <>
      <h2 className="page-title">Fordon</h2>
      <VehiclePanel siteSlug={params.slug} />
    </>
  );
}
