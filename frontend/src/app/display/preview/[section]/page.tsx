"use client";

import { notFound } from "next/navigation";
import { useParams } from "next/navigation";
import { MOCKUP_NOW, MOCKUP_OVERVIEW } from "@/components/pi-dashboard/__fixtures__/mockupOverview";
import { PiDetailView } from "@/components/pi-dashboard/PiDetailView";
import { isPiSection } from "@/components/pi-dashboard/piSections";

/**
 * Visual-comparison harness for Pi detail views. Dev-only.
 */
export default function DisplayPreviewSectionPage() {
  if (process.env.NODE_ENV === "production") return null;

  const params = useParams<{ section: string }>();
  const section = params.section;

  if (!isPiSection(section)) {
    notFound();
  }

  return (
    <PiDetailView
      slug="preview"
      section={section}
      data={MOCKUP_OVERVIEW}
      connection="CONNECTED"
      error={null}
      nowOverride={MOCKUP_NOW}
    />
  );
}
