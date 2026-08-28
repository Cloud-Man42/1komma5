"use client";

import { useParams } from "next/navigation";
import { VehicleOverview } from "@/components/vehicle-dashboard/VehicleOverview";

export default function SiteVehiclePage() {
  const params = useParams<{ slug: string }>();
  return <VehicleOverview siteSlug={params.slug} />;
}
