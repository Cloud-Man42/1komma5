"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Skeleton } from "@/components/dashboard";
import { formatRelativeTime } from "@/lib/format";
import {
  EvEnergyMixPanel,
  EvHardwarePanel,
  EvHeaderChips,
  EvManualControlPanel,
  EvMiniStatsRow,
  EvPlaceholderSection,
  EvPlanPanel,
  EvQuickOverviewPanel,
  EvSavingsPanel,
  EvSessionsTable,
  EvWaitingPanel,
} from "./EvPanels";
import type { EvStatsPeriod } from "./evDashboardHelpers";
import { EV_SECTION_LABELS } from "./evSection";
import { useEvDashboardData } from "./useEvDashboardData";
import { useEvSection } from "./useEvSection";

const EvPowerPanel = dynamic(
  () => import("./EvPanels").then((mod) => ({ default: mod.EvPowerPanel })),
  { ssr: false, loading: () => <Skeleton lines={6} /> },
);

const EvStatisticsPanel = dynamic(
  () => import("./EvPanels").then((mod) => ({ default: mod.EvStatisticsPanel })),
  { ssr: false, loading: () => <Skeleton lines={6} /> },
);

export function EvOverview({ siteSlug }: { siteSlug: string }) {
  const [statsPeriod, setStatsPeriod] = useState<EvStatsPeriod>("day");
  const data = useEvDashboardData(siteSlug, statsPeriod);
  const { section } = useEvSection();

  const updatedLabel = data.charger?.last_bridge_run_at
    ? formatRelativeTime(data.charger.last_bridge_run_at)
    : data.dashboard?.freshness.updated_at
      ? formatRelativeTime(data.dashboard.freshness.updated_at)
      : "—";

  useEffect(() => {
    if (section === "history") {
      document.getElementById("ev-sessions")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [section]);

  if (data.loading && !data.charger) {
    return <Skeleton lines={16} />;
  }

  if (!data.charger) {
    return (
      <section className="evdash-overview" data-testid="ev-overview">
        {data.error ? <p className="evdash-error" role="alert">{data.error}</p> : null}
        <p className="evdash-muted">Inga laddboxar konfigurerade. Lägg till under Inställningar.</p>
        <Link href="/config" className="evdash-link">
          Öppna konfiguration
        </Link>
      </section>
    );
  }

  const charger = data.charger;
  const online = data.bridge ? !data.bridge.stale : true;
  const titleName = `${charger.manufacturer} ${charger.model}`.trim() || charger.name;

  const renderOverview = () => (
    <>
      <div className="evdash-top-row">
        <EvPowerPanel charger={charger} powerChart={data.powerChart} maxPowerKw={data.maxPowerKw} />
        <EvHardwarePanel charger={charger} bridge={data.bridge} />
        <EvWaitingPanel reasoning={data.reasoning} plan={data.plan} />
      </div>
      <EvMiniStatsRow dayStats={data.dayStats} monthStats={data.monthStats} co2SavedKg={data.co2SavedKg} />
      <div className="evdash-mid-row">
        <EvPlanPanel planWindows={data.planWindows} plan={data.plan} />
        <EvStatisticsPanel
          hourlySources={data.hourlySources}
          period={statsPeriod}
          onPeriodChange={setStatsPeriod}
        />
        <EvEnergyMixPanel slices={data.energyMix} totalKwh={data.dayStats?.total_energy_kwh ?? 0} />
        <EvQuickOverviewPanel
          maxPowerKw={data.maxPowerKw}
          avgPowerKw={data.avgPowerKw}
          sessions={data.sessions}
          charger={charger}
          bridge={data.bridge}
        />
      </div>
      <div className="evdash-bottom-row">
        <EvSessionsTable sessions={data.sessions} />
        <EvSavingsPanel savings={data.savings} chart={data.savingsChart} />
        <EvManualControlPanel siteSlug={siteSlug} charger={charger} onUpdated={() => void data.reload()} />
      </div>
    </>
  );

  const renderSection = () => {
    switch (section) {
      case "overview":
        return renderOverview();
      case "charging":
        return (
          <>
            <EvPowerPanel charger={charger} powerChart={data.powerChart} maxPowerKw={data.maxPowerKw} />
            <EvWaitingPanel reasoning={data.reasoning} plan={data.plan} />
            <EvManualControlPanel siteSlug={siteSlug} charger={charger} onUpdated={() => void data.reload()} />
          </>
        );
      case "schedules":
        return <EvPlanPanel planWindows={data.planWindows} plan={data.plan} />;
      case "history":
        return renderOverview();
      case "statistics":
        return (
          <>
            <EvStatisticsPanel
              hourlySources={data.hourlySources}
              period={statsPeriod}
              onPeriodChange={setStatsPeriod}
            />
            <EvSavingsPanel savings={data.savings} chart={data.savingsChart} />
          </>
        );
      case "settings":
        return (
          <EvPlaceholderSection
            title="INSTÄLLNINGAR"
            text="Avancerade laddinställningar finns under Konfiguration → Laddboxar."
          />
        );
      case "access":
        return (
          <EvPlaceholderSection
            title="ÅTKOMST & QR"
            text="QR-koder och gäståtkomst hanteras i Charge Amps-appen."
          />
        );
      case "diagnostics":
        return (
          <EvPlaceholderSection
            title="DIAGNOSTIK"
            text="Detaljerad bridge- och energibalansdiagnostik finns i konfigurationsvyn."
          />
        );
      default:
        return renderOverview();
    }
  };

  return (
    <div className="evdash-overview" data-testid="ev-overview">
      <header className="evdash-header">
        <div>
          <h1 className="evdash-title">
            LADDBOX – {titleName.toUpperCase()}
            <span className={`evdash-live-badge ${online ? "evdash-live-badge-ok" : "evdash-live-badge-warn"}`}>
              {online ? "ONLINE" : "OFFLINE"}
            </span>
          </h1>
          <p className="evdash-subtitle">
            {charger.name} · {data.vehicleLabel} · Senast uppdaterad {updatedLabel}
          </p>
        </div>
        <EvHeaderChips charger={charger} bridge={data.bridge} reasoning={data.reasoning} />
      </header>

      {data.error ? <p className="evdash-error" role="alert">{data.error}</p> : null}

      {section !== "overview" && section !== "history" ? (
        <p className="evdash-section-label">{EV_SECTION_LABELS[section]}</p>
      ) : null}

      {renderSection()}
    </div>
  );
}
