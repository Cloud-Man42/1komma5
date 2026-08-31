"use client";

import { useRef, useState } from "react";
import { Skeleton } from "@/components/dashboard";
import { startVehicleCharging, stopVehicleCharging, syncVehicles } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import { VehicleActionsPanel } from "./VehicleActionsPanel";
import { VehicleBatteryHero } from "./VehicleBatteryHero";
import { VehicleChargingPlanPanel } from "./VehicleChargingPlanPanel";
import { VehicleChargingSessionPanel } from "./VehicleChargingSessionPanel";
import { VehicleCostsSection } from "./VehicleCostsSection";
import { VehicleHeaderChips } from "./VehicleHeaderChips";
import { VehicleHistorySection } from "./VehicleHistorySection";
import { VehicleSettingsSection } from "./VehicleSettingsSection";
import { VehicleStatusPanel } from "./VehicleStatusPanel";
import { VehicleSummaryStrip } from "./VehicleSummaryStrip";
import { VehicleSyncFooter } from "./VehicleSyncFooter";
import { buildVehicleDisplay, connectionLabel } from "./vehicleDashboardHelpers";
import { VEHICLE_SECTION_LABELS } from "./vehicleSection";
import { useVehicleDashboardData } from "./useVehicleDashboardData";
import { useVehicleSection } from "./useVehicleSection";

export function VehicleOverview({ siteSlug }: { siteSlug: string }) {
  const data = useVehicleDashboardData(siteSlug);
  const { section } = useVehicleSection();
  const [stopping, setStopping] = useState(false);
  const [starting, setStarting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const actionsRef = useRef<HTMLDivElement | null>(null);

  if (data.loading && !data.integration) {
    return <Skeleton lines={14} />;
  }

  if (data.integration && !data.integration.enabled) {
    return (
      <section className="vdash-overview" data-testid="vehicle-overview">
        <p className="vdash-muted">
          Mercedes me-integrationen är inte aktiverad. Konfigurera under Inställningar → Anläggningar.
        </p>
      </section>
    );
  }

  const display = buildVehicleDisplay({
    vehicle: data.vehicle,
    session: data.session,
    sessions: data.sessions,
    integration: data.integration,
    reasoning: data.reasoning,
    refreshIntervalSec: data.refreshSeconds,
    siteSlug,
  });

  const updatedLabel = data.vehicle?.last_vehicle_update
    ? formatRelativeTime(data.vehicle.last_vehicle_update)
    : "—";

  const siteName = siteSlug.charAt(0).toUpperCase() + siteSlug.slice(1);

  const handleStop = async () => {
    if (!display.vehicleId || !display.canStopCharging) return;
    setStopping(true);
    try {
      await stopVehicleCharging(siteSlug, display.vehicleId);
      await data.reload();
    } finally {
      setStopping(false);
    }
  };

  const handleStart = async () => {
    if (!display.vehicleId || !display.canStartCharging) return;
    setStarting(true);
    try {
      await startVehicleCharging(siteSlug, display.vehicleId);
      await data.reload();
    } finally {
      setStarting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncVehicles(siteSlug);
      await data.reload();
    } finally {
      setSyncing(false);
    }
  };

  const scrollToActions = () => {
    actionsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const sectionTitle = VEHICLE_SECTION_LABELS[section];

  const renderSection = () => {
    if (!data.vehicle) {
      return (
        <p className="vdash-muted">Inget fordon hittades. Kontrollera Mercedes me-inloggning under Konfiguration.</p>
      );
    }

    switch (section) {
      case "overview":
        return (
          <>
            <div className="vdash-hero-row">
              <VehicleBatteryHero
                socPct={display.socPct}
                energyKwh={display.energyKwh}
                capacityKwh={display.capacityKwh}
                chargingPowerKw={display.chargingPowerKw}
                targetSocPct={display.targetSocPct}
                startedAt={display.startedAt}
                isCharging={Boolean(display.isCharging)}
              />
              <VehicleHeaderChips
                rangeKm={display.rangeKm}
                targetSocPct={display.targetSocPct}
                isPluggedIn={display.isPluggedIn}
                isCharging={display.isCharging}
                chargingPowerKw={display.chargingPowerKw}
                freshnessLabel={display.freshnessLabel}
              />
            </div>
            <VehicleSummaryStrip display={display} siteName={siteName} />
          </>
        );

      case "charging":
        return (
          <div className="vdash-section-layout" data-testid="vehicle-section-charging">
            <VehicleChargingSessionPanel
              subtitle={display.chargingSubtitle}
              session={data.session}
              chargingPowerKw={display.chargingPowerKw}
              onStop={() => void handleStop()}
              onStart={() => void handleStart()}
              stopping={stopping}
              starting={starting}
              canStop={display.canStopCharging && data.commandsEnabled}
              canStart={display.canStartCharging && data.commandsEnabled}
            />
            <div className="vdash-section-two-col">
              <VehicleBatteryHero
                socPct={display.socPct}
                energyKwh={display.energyKwh}
                capacityKwh={display.capacityKwh}
                chargingPowerKw={display.chargingPowerKw}
                targetSocPct={display.targetSocPct}
                startedAt={display.startedAt}
                isCharging={Boolean(display.isCharging)}
              />
              <div ref={actionsRef}>
                <VehicleActionsPanel
                  siteSlug={siteSlug}
                  vehicle={data.vehicle}
                  commandsEnabled={data.commandsEnabled}
                  onChanged={() => void data.reload()}
                />
              </div>
            </div>
          </div>
        );

      case "history":
        return <VehicleHistorySection sessions={data.sessions} />;

      case "status":
        return (
          <div className="vdash-section-layout" data-testid="vehicle-section-status">
            <VehicleStatusPanel
              capabilities={display.capabilities}
              integration={display.integration}
              halo={display.halo}
              dataQuality={display.dataQuality}
              freshnessLabel={display.freshnessLabel}
            />
            <VehicleHeaderChips
              rangeKm={display.rangeKm}
              targetSocPct={display.targetSocPct}
              isPluggedIn={display.isPluggedIn}
              isCharging={display.isCharging}
              chargingPowerKw={display.chargingPowerKw}
              freshnessLabel={display.freshnessLabel}
            />
          </div>
        );

      case "costs":
        return (
          <VehicleCostsSection
            sessions={data.sessions}
            bars={display.sessionHistoryBars}
            avgRenewableSharePct={display.avgRenewableSharePct}
            totalEnergyKwh={display.totalEnergyKwh}
            totalSavingsKr={display.totalSavingsKr}
          />
        );

      case "schedule":
        return (
          <div className="vdash-section-layout vdash-section-narrow" data-testid="vehicle-section-schedule">
            <VehicleChargingPlanPanel
              targetSocPct={display.targetSocPct}
              departureTime={display.departureTime}
              requiredEnergyKwh={display.requiredEnergyKwh}
              planReasonSv={display.planReasonSv}
              smartChargingState={display.smartChargingState}
              onEditTargetSoc={scrollToActions}
            />
            <div ref={actionsRef}>
              <VehicleActionsPanel
                siteSlug={siteSlug}
                vehicle={data.vehicle}
                commandsEnabled={data.commandsEnabled}
                onChanged={() => void data.reload()}
              />
            </div>
          </div>
        );

      case "settings":
        return (
          <VehicleSettingsSection
            siteSlug={siteSlug}
            integration={data.integration}
            vehicle={data.vehicle}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="vdash-overview" data-testid="vehicle-overview">
      <header className="vdash-header">
        <div>
          <h1 className="vdash-title">
            FORDON – {display.displayName}
            {display.freshnessLabel === "LIVE" ? (
              <span className="idash-live-badge">● LIVE</span>
            ) : null}
          </h1>
          <p className="vdash-section-breadcrumb">{sectionTitle}</p>
          <div className="vdash-status-row">
            <span className="vdash-status-chip">{connectionLabel(display.connectionState)}</span>
            <span className="vdash-status-chip">
              {display.isPluggedIn == null ? "—" : display.isPluggedIn ? "Ansluten" : "Ej ansluten"}
            </span>
            <span className="vdash-status-chip">{siteName}</span>
            <span className="vdash-status-chip">Senast uppdaterad {updatedLabel}</span>
          </div>
        </div>
      </header>

      {data.error ? <p className="vdash-muted">{data.error}</p> : null}

      {renderSection()}

      <VehicleSyncFooter
        lastUpdateIso={data.vehicle?.last_vehicle_update ?? null}
        signalStrength={display.signalStrength}
        refreshIntervalSec={display.refreshIntervalSec}
        connectionState={display.connectionState}
        onSync={() => void handleSync()}
        syncing={syncing}
      />
    </div>
  );
}
