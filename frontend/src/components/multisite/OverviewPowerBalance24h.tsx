"use client";

import type { CSSProperties } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MultiSiteAggregate } from "@/lib/multiSiteApi";
import { formatFlowPowerCompact } from "@/lib/multiSiteFlowFormat";
import { historySiteSolarKey, type MultiSiteHistoryPoint } from "@/lib/multiSiteHistory";

export interface SiteHistorySeries {
  slug: string;
  name: string;
  color: string;
}

const LEGEND = [
  { id: "solar", label: "Solar", color: "#fcc206" },
  { id: "gridImport", label: "Grid import", color: "#ef4444" },
  { id: "gridExport", label: "Grid export", color: "#38bdf8" },
  { id: "batteryCharge", label: "Battery charge", color: "#c084fc" },
  { id: "batteryDischarge", label: "Battery discharge", color: "#4ade80" },
] as const;

function KpiItem({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="ms-balance-kpi">
      <span className="ms-balance-kpi-label">{label}</span>
      <strong className="ms-balance-kpi-value" style={{ color }}>
        {value}
      </strong>
    </div>
  );
}

export function OverviewPowerBalance24h({
  aggregate,
  points,
  loading,
  siteSeries = [],
}: {
  aggregate: MultiSiteAggregate;
  points: MultiSiteHistoryPoint[];
  loading: boolean;
  siteSeries?: SiteHistorySeries[];
}) {
  const latest = points.length > 0 ? points[points.length - 1] : null;

  const kpis = {
    solarW: latest?.solarW ?? (aggregate.solarPowerKw ?? 0) * 1000,
    gridImportW: latest?.gridImportW ?? (aggregate.gridImportPowerKw ?? 0) * 1000,
    gridExportW: latest?.gridExportW ?? (aggregate.gridExportPowerKw ?? 0) * 1000,
    batteryChargeW: latest?.batteryChargeW ?? (aggregate.batteryChargePowerKw ?? 0) * 1000,
    batteryDischargeW: latest?.batteryDischargeW ?? (aggregate.batteryDischargePowerKw ?? 0) * 1000,
  };

  const chartData = points.map((p) => {
    const row: Record<string, number | string> = {
      label: p.label,
      solarW: p.solarW,
      gridImportW: p.gridImportW,
      gridExportW: p.gridExportW,
      batteryChargeW: p.batteryChargeW,
      batteryDischargeW: p.batteryDischargeW,
    };
    for (const site of siteSeries) {
      row[historySiteSolarKey(site.slug)] = p.siteSolarW?.[site.slug] ?? 0;
    }
    return row;
  });

  return (
    <section className="ms-panel ms-balance-panel">
      <header className="ms-panel-header">
        <h2>Generation, grid and battery – 24 hours</h2>
      </header>

      <div className="ms-balance-kpi-row">
        <KpiItem label="Solar" value={formatFlowPowerCompact(kpis.solarW)} color={LEGEND[0].color} />
        <KpiItem label="Grid import" value={formatFlowPowerCompact(kpis.gridImportW)} color={LEGEND[1].color} />
        <KpiItem label="Grid export" value={formatFlowPowerCompact(kpis.gridExportW)} color={LEGEND[2].color} />
        <KpiItem
          label="Battery charge"
          value={formatFlowPowerCompact(kpis.batteryChargeW)}
          color={LEGEND[3].color}
        />
        <KpiItem
          label="Battery discharge"
          value={formatFlowPowerCompact(kpis.batteryDischargeW)}
          color={LEGEND[4].color}
        />
      </div>

      {loading && chartData.length === 0 ? (
        <p className="muted ms-balance-empty">Laddar historik…</p>
      ) : chartData.length === 0 ? (
        <p className="muted ms-balance-empty">Ingen historik tillgänglig.</p>
      ) : (
        <div className="ms-balance-chart-wrap">
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                width={48}
                label={{ value: "Power (W)", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid rgba(148,163,184,0.2)" }}
                formatter={(value: number) => formatFlowPowerCompact(value)}
              />
              <Area
                type="monotone"
                dataKey="solarW"
                stackId="gen"
                stroke={LEGEND[0].color}
                fill={LEGEND[0].color}
                fillOpacity={siteSeries.length > 1 ? 0.15 : 0.35}
                strokeWidth={1.5}
              />
              {siteSeries.map((site) => (
                <Line
                  key={site.slug}
                  type="monotone"
                  dataKey={historySiteSolarKey(site.slug)}
                  name={site.name}
                  stroke={site.color}
                  strokeWidth={2}
                  strokeDasharray="4 3"
                  dot={false}
                />
              ))}
              <Area
                type="monotone"
                dataKey="batteryChargeW"
                stackId="gen"
                stroke={LEGEND[3].color}
                fill={LEGEND[3].color}
                fillOpacity={0.3}
                strokeWidth={1.5}
              />
              <Line
                type="monotone"
                dataKey="gridImportW"
                stroke={LEGEND[1].color}
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="gridExportW"
                stroke={LEGEND[2].color}
                strokeWidth={1.5}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="batteryDischargeW"
                stroke={LEGEND[4].color}
                strokeWidth={1.5}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      <ul className="ms-balance-legend" aria-label="Förklaring">
        {LEGEND.map((item) => (
          <li key={item.id}>
            <span
              className="ms-balance-legend-swatch"
              style={{ "--ms-swatch": item.color } as CSSProperties}
              aria-hidden="true"
            />
            {item.label}
          </li>
        ))}
        {siteSeries.map((site) => (
          <li key={site.slug}>
            <span
              className="ms-balance-legend-swatch ms-balance-legend-swatch-dashed"
              style={{ "--ms-swatch": site.color } as CSSProperties}
              aria-hidden="true"
            />
            {site.name} (sol)
          </li>
        ))}
      </ul>
    </section>
  );
}
