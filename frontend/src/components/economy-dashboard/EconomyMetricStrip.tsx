"use client";

import type { CSSProperties, ReactNode } from "react";
import { Sparkline } from "@/components/intelligence-dashboard/Sparkline";
import { CircularGauge } from "@/components/intelligence-dashboard/CircularGauge";
import type { EconomyDisplayMetrics } from "./economyDashboardHelpers";
import { formatEconomyKr, formatEconomyPct } from "./economyDashboardHelpers";

function MetricCard({
  title,
  value,
  changePct,
  invertChange = false,
  positiveIsGood = true,
  subtext,
  accent,
  sparkValues,
  gauge,
}: {
  title: string;
  value: string;
  changePct: number | null;
  invertChange?: boolean;
  positiveIsGood?: boolean;
  subtext: string;
  accent: string;
  sparkValues: number[];
  gauge?: ReactNode;
}) {
  const pct = formatEconomyPct(changePct, invertChange);
  const isUp = changePct != null && changePct > 0;
  const good = invertChange ? !isUp : positiveIsGood ? isUp : !isUp;
  const badgeClass = changePct == null ? "edash-metric-badge-neutral" : good ? "edash-metric-badge-good" : "edash-metric-badge-warn";

  return (
    <article className="edash-metric-card" style={{ "--edash-accent": accent } as CSSProperties}>
      <div className="edash-metric-spark-bg" aria-hidden="true">
        <Sparkline values={sparkValues} color={accent} className="edash-metric-spark" />
      </div>
      <p className="edash-metric-label">{title}</p>
      <div className="edash-metric-row">
        <strong className="edash-metric-value">{value}</strong>
        {gauge}
        {changePct != null ? <span className={`edash-metric-badge ${badgeClass}`}>{pct}</span> : null}
      </div>
      <p className="edash-metric-sub">{subtext}</p>
    </article>
  );
}

export function EconomyMetricStrip({ metrics, sparkSeries }: { metrics: EconomyDisplayMetrics; sparkSeries: number[][] }) {
  return (
    <div className="edash-metric-strip" data-testid="economy-metric-strip">
      <MetricCard
        title="TOTAL BESPARING"
        value={formatEconomyKr(metrics.totalSavingsSek)}
        changePct={metrics.changes.totalSavings.pct}
        subtext="jämfört med föregående månad"
        accent="#4ade80"
        sparkValues={sparkSeries[0] ?? [1, 2, 3, 4]}
      />
      <MetricCard
        title="ELKOSTNAD"
        value={formatEconomyKr(metrics.gridImportCostSek)}
        changePct={metrics.changes.gridImportCost.pct}
        invertChange
        positiveIsGood={false}
        subtext="jämfört med föregående månad"
        accent="#a78bfa"
        sparkValues={sparkSeries[1] ?? [4, 3, 2, 1]}
      />
      <MetricCard
        title="SÅLD EL-INTÄKT"
        value={formatEconomyKr(metrics.exportRevenueSek)}
        changePct={metrics.changes.exportRevenue.pct}
        subtext="jämfört med föregående månad"
        accent="#4ade80"
        sparkValues={sparkSeries[2] ?? [1, 3, 2, 5]}
      />
      <MetricCard
        title="NETTOKOSTNAD"
        value={formatEconomyKr(metrics.netCostSek)}
        changePct={metrics.changes.netCost.pct}
        invertChange
        positiveIsGood={false}
        subtext="jämfört med föregående månad"
        accent="#38bdf8"
        sparkValues={sparkSeries[3] ?? [3, 2, 4, 2]}
      />
      <MetricCard
        title="AVKASTNING (YTD)"
        value={`${metrics.ytdReturnPct.toFixed(1)}%`}
        changePct={null}
        subtext="på total investering"
        accent="#4ade80"
        sparkValues={sparkSeries[4] ?? [2, 3, 4, 5]}
        gauge={
          <CircularGauge
            value={Math.min(100, metrics.ytdReturnPct * 4)}
            label=""
            color="#4ade80"
            size={52}
          />
        }
      />
    </div>
  );
}
