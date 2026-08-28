"use client";

import { useState } from "react";
import { Skeleton } from "@/components/dashboard";
import { formatRelativeTime } from "@/lib/format";
import { SpaComponentsPanel } from "./SpaComponentsPanel";
import { SpaConsumption24hChart } from "./SpaConsumption24hChart";
import { SpaDetailedAnalysisPanel } from "./SpaDetailedAnalysisPanel";
import { SpaDrawer } from "./SpaDrawer";
import { SpaFilterScheduleEditor } from "./SpaFilterScheduleEditor";
import { SpaFilterSchedulePanel } from "./SpaFilterSchedulePanel";
import { SpaGaugeRow } from "./SpaGaugeRow";
import { SpaInsightsPanel } from "./SpaInsightsPanel";
import { SpaModeSelect } from "./SpaModeSelect";
import { SpaShadowModeToggle } from "./SpaShadowModeToggle";
import { SpaQuickControls } from "./SpaQuickControls";
import { SpaSensorsPanel } from "./SpaSensorsPanel";
import { SpaStatusFooter } from "./SpaStatusFooter";
import { SpaTodayHistoryChart } from "./SpaTodayHistoryChart";
import {
  filterMinutesRemaining,
  filterProgressPct,
  integrationLabelSv,
  isFilterRunning,
} from "./spaDashboardHelpers";
import { useSpaDashboardData } from "./useSpaDashboardData";
import { CircularGauge } from "@/components/intelligence-dashboard/CircularGauge";

export function SpaOverview({ siteSlug }: { siteSlug: string }) {
  const data = useSpaDashboardData(siteSlug);
  const [showSensors, setShowSensors] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);

  if (data.error && !data.status) {
    return <p className="form-error">{data.error}</p>;
  }

  if (data.loading && !data.status) {
    return <Skeleton lines={12} />;
  }

  if (!data.status) {
    return <p className="sdash-muted">Laddar spa…</p>;
  }

  if (!data.status.integration_enabled) {
    return (
      <section className="sdash-overview" data-testid="spa-overview">
        <p className="sdash-muted">Integrationen är inte aktiverad. Konfigurera under Inställningar.</p>
      </section>
    );
  }

  const status = data.status;
  const filterRunning = isFilterRunning(status, data.plan);
  const filterProgress = filterProgressPct(status, data.plan, data.control);
  const filterRemaining = filterMinutesRemaining(status, data.plan, data.control);
  const updatedLabel = status.last_updated
    ? formatRelativeTime(status.last_updated)
    : data.lastLoadedAt
      ? formatRelativeTime(new Date(data.lastLoadedAt).toISOString())
      : "—";

  return (
    <div className="sdash-overview" data-testid="spa-overview">
      <header className="sdash-header">
        <div>
          <h1 className="sdash-title">
            SPA – ARCTIC SPA
            <span className="idash-live-badge">● LIVE</span>
          </h1>
          <p className="sdash-subtitle">
            Glacier XL · {integrationLabelSv(status.data_source)} · Uppdaterad {updatedLabel}
          </p>
        </div>
        <div className="sdash-header-controls">
          <SpaModeSelect siteSlug={siteSlug} control={data.control} onChanged={() => void data.reload()} />
          <SpaShadowModeToggle
            siteSlug={siteSlug}
            control={data.control}
            compact
            onChanged={() => void data.reload()}
          />
          <div className="sdash-filter-chip">
            <div>
              <span className="sdash-filter-chip-label">FILTERCYKEL</span>
              <strong>{filterRunning ? "Pågår" : "Vilar"}</strong>
              {filterRunning && filterRemaining != null ? (
                <p>{filterRemaining} min kvar</p>
              ) : null}
            </div>
            <CircularGauge
              value={filterProgress}
              label={`${Math.round(filterProgress)}%`}
              color="#38bdf8"
              size={72}
            />
          </div>
        </div>
      </header>

      <SpaGaugeRow status={status} today={data.today} month={data.month} total={data.total} />

      <div className="sdash-middle-grid">
        <SpaComponentsPanel status={status} />
        <SpaConsumption24hChart history={data.history24h} status={status} />
      </div>

      <div className="sdash-bottom-grid">
        <SpaFilterSchedulePanel
          status={status}
          plan={data.plan}
          control={data.control}
          onShowSchedule={() => setShowSchedule(true)}
        />
        <SpaTodayHistoryChart history={data.historyToday} />
        <SpaInsightsPanel
          status={status}
          today={data.today}
          month={data.month}
          plan={data.plan}
          onShowAnalysis={() => setShowAnalysis(true)}
        />
        <SpaQuickControls
          siteSlug={siteSlug}
          status={status}
          control={data.control}
          onChanged={() => void data.reload()}
        />
      </div>

      <SpaStatusFooter status={status} health={data.health} onShowSensors={() => setShowSensors(true)} />

      <SpaDrawer title="Alla sensorer" open={showSensors} onClose={() => setShowSensors(false)}>
        <SpaSensorsPanel status={status} health={data.health} />
      </SpaDrawer>

      <SpaDrawer title="Filtersschema" open={showSchedule} onClose={() => setShowSchedule(false)}>
        <SpaFilterScheduleEditor
          siteSlug={siteSlug}
          plan={data.plan}
          control={data.control}
          onSaved={() => void data.reload()}
          onControlChanged={() => void data.reload()}
        />
      </SpaDrawer>

      <SpaDrawer title="Detaljerad analys" open={showAnalysis} onClose={() => setShowAnalysis(false)}>
        <SpaDetailedAnalysisPanel siteSlug={siteSlug} />
      </SpaDrawer>
    </div>
  );
}
