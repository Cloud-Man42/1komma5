"use client";

import { PiDashboard } from "@/components/pi-dashboard/PiDashboard";
import { MOCKUP_NOW, MOCKUP_OVERVIEW } from "@/components/pi-dashboard/__fixtures__/mockupOverview";

/**
 * Visual-comparison harness: renders the kiosk layout with the design
 * reference's exact readings and a frozen clock, so a headless screenshot can
 * be diffed against the mockup. Dev-only — never exposed by a production build.
 */
export default function DisplayPreviewPage() {
  if (process.env.NODE_ENV === "production") return null;

  return (
    <PiDashboard
      slug="preview"
      data={MOCKUP_OVERVIEW}
      connection="CONNECTED"
      error={null}
      nowOverride={MOCKUP_NOW}
    />
  );
}
