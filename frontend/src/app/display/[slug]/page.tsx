"use client";

import { useParams } from "next/navigation";
import { PiDashboard } from "@/components/pi-dashboard/PiDashboard";
import { usePiDashboardData } from "@/lib/usePiDashboardData";

export default function DisplayHomePage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const { data, connection, error } = usePiDashboardData(slug);

  return <PiDashboard slug={slug} data={data} connection={connection} error={error} />;
}
