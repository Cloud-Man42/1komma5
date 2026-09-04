"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import EnergyReasoningPanel from "@/components/EnergyReasoningPanel";
import { SolarAccuracyView } from "@/components/SolarAccuracyView";
import { SolarDiagnosticsPanel } from "@/components/SolarDiagnosticsPanel";
import VirtualEvseDiagnosticsPanel from "@/components/VirtualEvseDiagnosticsPanel";
import { HeartbeatAuditPanel } from "@/components/HeartbeatAuditPanel";
import { EnergyControlPanel } from "@/components/EnergyControlPanel";
import { EnergyStrategyCard } from "@/components/intelligence-dashboard/EnergyStrategyCard";
import { BatteryOpportunityPanel } from "@/components/intelligence-dashboard/BatteryOpportunityPanel";
import { HorizonOptimizerPanel } from "@/components/intelligence-dashboard/HorizonOptimizerPanel";
import { IntegrationHealthPanel } from "@/components/IntegrationHealthPanel";
import { EvCharger, fetchEvChargers, fetchSites } from "@/lib/api";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

export default function SiteDiagnosticsPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const refreshSeconds = useDashboardRefreshSeconds();
  const [chargers, setChargers] = useState<EvCharger[]>([]);
  const [timezone, setTimezone] = useState("Europe/Stockholm");

  useEffect(() => {
    fetchSites()
      .then((sites) => {
        const site = sites.find((entry) => entry.slug === slug);
        if (site?.timezone) setTimezone(site.timezone);
      })
      .catch(() => undefined);
  }, [slug]);

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
      <HeartbeatAuditPanel siteSlug={slug} />
      <IntegrationHealthPanel siteSlug={slug} />
      <EnergyStrategyCard slug={slug} timezone={timezone} />
      <BatteryOpportunityPanel slug={slug} />
      <HorizonOptimizerPanel slug={slug} />
      <EnergyControlPanel siteSlug={slug} />
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
