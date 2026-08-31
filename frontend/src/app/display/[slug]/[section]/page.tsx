"use client";

import { notFound } from "next/navigation";
import { useParams } from "next/navigation";
import { PiDetailView } from "@/components/pi-dashboard/PiDetailView";
import { isPiSection } from "@/components/pi-dashboard/piSections";
import { usePiDashboardData } from "@/lib/usePiDashboardData";

export default function DisplaySectionPage() {
  const params = useParams<{ slug: string; section: string }>();
  const slug = params.slug;
  const section = params.section;

  if (!isPiSection(section)) {
    notFound();
  }

  const { data, connection, error } = usePiDashboardData(slug);

  return (
    <PiDetailView
      slug={slug}
      section={section}
      data={data}
      connection={connection}
      error={error}
    />
  );
}
