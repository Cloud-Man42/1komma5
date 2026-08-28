import { CircularGauge } from "@/components/intelligence-dashboard/CircularGauge";
import type { SpaControlConfig, SpaPlan, SpaStatus } from "@/lib/api";
import {
  filterMinutesRemaining,
  filterProgressPct,
  filterSchedulePanelCopy,
  isFilterRunning,
  nextCycleLabel,
} from "./spaDashboardHelpers";

export function SpaFilterSchedulePanel({
  status,
  plan,
  control,
  onShowSchedule,
}: {
  status: SpaStatus;
  plan: SpaPlan | null;
  control: SpaControlConfig | null;
  onShowSchedule?: () => void;
}) {
  const running = isFilterRunning(status, plan);
  const dailyProgress = plan?.daily_progress_pct ?? 0;
  const ringValue = running ? filterProgressPct(status, plan, control) : dailyProgress;
  const remaining = filterMinutesRemaining(status, plan, control);

  const nextCycle = nextCycleLabel(plan);
  const panelCopy = filterSchedulePanelCopy(control);

  return (
    <section className="sdash-panel sdash-filter-panel">
      <h2 className="sdash-panel-title">SMART FILTERSCHEMA</h2>
      <p className="sdash-filter-sub">{panelCopy.subtitle}</p>
      <div className="sdash-filter-body">
        <div className="sdash-filter-ring">
          <CircularGauge value={ringValue} label={`${Math.round(ringValue)}%`} color="#38bdf8" size={110} />
          <p className="sdash-filter-next">
            Nästa cykel
            <strong>{nextCycle}</strong>
            <span>Idag</span>
          </p>
        </div>
        <ul className="sdash-filter-checklist">
          {panelCopy.checklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      {panelCopy.warning ? (
        <p className="sdash-filter-warn" data-testid="fixed-schedule-warning">
          {panelCopy.warning}
        </p>
      ) : null}
      <button type="button" className="sdash-link-btn" onClick={onShowSchedule}>
        Visa schema
      </button>
      {running ? (
        <p className="sdash-filter-running">
          Filtercykel pågår{remaining != null ? ` · ${remaining} min kvar` : ""}
        </p>
      ) : null}
    </section>
  );
}
