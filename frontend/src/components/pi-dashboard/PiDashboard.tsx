"use client";

import { useEffect, useState } from "react";
import type { DisplayOverview, PiConnectionState } from "@/lib/displayOverview";
import { PiChargerPanel, PiSpaPanel, PiVehiclePanel } from "./PiAssetPanels";
import { PiEconomyPanel, PiHighlightsPanel, PiKpiBar } from "./PiBottomPanels";
import { PiConnectionBanner } from "./PiConnectionBanner";
import { PiEnergyFlowDiagram } from "./PiEnergyFlowDiagram";
import { PiHeader } from "./PiHeader";
import { PiMetricCards } from "./PiMetricCards";

/** Design size of the kiosk layout; the Pi panel is natively exactly this. */
export const PI_WIDTH = 1024;
export const PI_HEIGHT = 600;

/**
 * Scales the fixed 1024x600 layout to whatever viewport it is shown in, so the
 * Pi (scale 1.0) and a desktop preview render pixel-identically and neither
 * ever produces a scrollbar.
 */
function useFitScale() {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const update = () =>
      setScale(Math.min(window.innerWidth / PI_WIDTH, window.innerHeight / PI_HEIGHT));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return scale;
}

export function PiDashboard({
  slug,
  data,
  connection,
  nowOverride,
}: {
  slug: string;
  data: DisplayOverview | null;
  connection: PiConnectionState;
  /** Kept for the page contract; the banner reports state, not the raw message. */
  error?: string | null;
  /** Fixed clock used by the visual-comparison preview and tests. */
  nowOverride?: Date;
}) {
  const scale = useFitScale();

  return (
    <div className="pi-viewport">
      <div className="pi-frame" style={{ ["--pi-fit" as string]: scale }}>
        <PiConnectionBanner connection={connection} freshness={data?.freshness} />
        <div className="pi-main">
          <PiHeader slug={slug} data={data} connection={connection} nowOverride={nowOverride} isHome />
          <PiMetricCards slug={slug} data={data} />
          <section className="pi-row-mid">
            <PiEnergyFlowDiagram slug={slug} data={data} />
            <PiVehiclePanel slug={slug} data={data} />
            <PiChargerPanel slug={slug} data={data} />
          </section>
          <section className="pi-row-bottom">
            <PiSpaPanel slug={slug} data={data} />
            <PiEconomyPanel slug={slug} data={data} />
            <PiHighlightsPanel slug={slug} data={data} />
          </section>
          <PiKpiBar slug={slug} data={data} />
        </div>
      </div>
    </div>
  );
}
