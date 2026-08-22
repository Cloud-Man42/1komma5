"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import EnergyReasoningPanel from "@/components/EnergyReasoningPanel";
import { SolarAccuracyView } from "@/components/SolarAccuracyView";
import { SolarDiagnosticsPanel } from "@/components/SolarDiagnosticsPanel";
import VirtualEvseDiagnosticsPanel from "@/components/VirtualEvseDiagnosticsPanel";
import { EvCharger, fetchEvChargers } from "@/lib/api";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

export default function SiteDiagnosticsPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const refreshSeconds = useDashboardRefreshSeconds();
  const [chargers, setChargers] = useState<EvCharger[]>([]);

  useEffect(() => {
    fetchEvChargers(slug)
      .then(setChargers)
      .catch(() => setChargers([]));
  }, [slug]);

  const bridgeCharger = chargers.find((charger) => charger.bridge_enabled) ?? chargers[0];

  return (
    <>
      <h2 className="page-title">Diagnostik</h2>
      <SolarAccuracyView siteSlug={slug} />
      <SolarDiagnosticsPanel siteSlug={slug} />
      {bridgeCharger && (
        <>
          <EnergyReasoningPanel
            siteSlug={slug}
            chargerId={bridgeCharger.id}
            refreshSeconds={refreshSeconds}
          />
          {(bridgeCharger.bridge_enabled || bridgeCharger.virtual_evse_enabled) && (
            <VirtualEvseDiagnosticsPanel
              siteSlug={slug}
              chargerId={bridgeCharger.id}
              refreshSeconds={refreshSeconds}
              virtualEvseEnabled={bridgeCharger.virtual_evse_enabled}
            />
          )}
        </>
      )}
    </>
  );
}
