"use client";

import type { MultiSiteAggregate, MultiSiteSiteEntry } from "@/lib/multiSiteApi";
import { formatFlowPowerCompact, formatFlowPowerFromKw } from "@/lib/multiSiteFlowFormat";
import { buildSiteColorMap } from "@/lib/multiSiteSiteColors";

const GLYPHS = {
  sun:
    "M12 8.1a3.9 3.9 0 1 0 0 7.8 3.9 3.9 0 0 0 0-7.8ZM12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.4 5.4l1.5 1.5M17.1 17.1l1.5 1.5M18.6 5.4l-1.5 1.5M6.9 17.1l-1.5 1.5",
  house: "M3.2 10.6 12 3.8l8.8 6.8M5.6 9.6v10.8h12.8V9.6M9.8 20.4v-5.6h4.4v5.6",
  battery: "M7 4.4h10v15.2H7zM10 4.4V2.8h4v1.6M9.4 9.2h5.2v7.4H9.4z",
  pylon: "M5.4 20.6 8.8 3.6h6.4l3.4 17M7.6 13h8.8M6.6 16.8h10.8M9.1 8.8h5.8",
  plug: "M9 3v4.6M15 3v4.6M6.8 7.6h10.4v3.1a5.2 5.2 0 0 1-10.4 0zM12 15.9v5.2",
};

const COLORS = {
  solar: "#fcc206",
  ev: "#f97316",
  battery: "#e879f9",
  grid: "#64748b",
  house: "#38bdf8",
};

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function distributeAngles(count: number, start: number, end: number): number[] {
  if (count <= 0) return [];
  if (count === 1) return [(start + end) / 2];
  const step = (end - start) / (count - 1);
  return Array.from({ length: count }, (_, i) => start + step * i);
}

function FlowPath({
  from,
  to,
  hub,
  color,
  active,
  dimmed,
}: {
  from: { x: number; y: number };
  to: { x: number; y: number };
  hub: { x: number; y: number };
  color: string;
  active: boolean;
  dimmed?: boolean;
}) {
  const d = `M ${from.x} ${from.y} Q ${hub.x} ${hub.y} ${to.x} ${to.y}`;
  const opacity = dimmed ? 0.12 : active ? 0.85 : 0.22;
  return (
    <g>
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={active && !dimmed ? 2.4 : 1.4}
        strokeOpacity={opacity}
        strokeLinecap="round"
      />
      {active && !dimmed ? (
        <circle r="3" fill={color}>
          <animateMotion dur="2.4s" repeatCount="indefinite" path={d} />
        </circle>
      ) : null}
    </g>
  );
}

function OuterNode({
  x,
  y,
  glyph,
  color,
  label,
  value,
  sub,
  dimmed,
  emphasized,
}: {
  x: number;
  y: number;
  glyph: string;
  color: string;
  label: string;
  value: string;
  sub?: string;
  dimmed?: boolean;
  emphasized?: boolean;
}) {
  const size = emphasized ? 38 : 34;
  const gx = x - size / 2;
  const gy = y - size / 2;
  const opacity = dimmed ? 0.35 : 1;
  return (
    <g opacity={opacity}>
      <circle
        cx={x}
        cy={y}
        r={size / 2 + (emphasized ? 8 : 6)}
        fill="rgba(15,23,42,0.55)"
        stroke={color}
        strokeOpacity={emphasized ? 0.9 : 0.35}
        strokeWidth={emphasized ? 2 : 1}
      />
      <rect x={gx} y={gy} width={size} height={size} rx={8} fill={color} fillOpacity={0.18} stroke={color} strokeOpacity={0.5} />
      <g transform={`translate(${gx + 7} ${gy + 7}) scale(0.85)`}>
        <path d={glyph} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      <text x={x} y={y + size / 2 + 14} textAnchor="middle" className="ms-flow-node-label" fill={color}>
        {label}
      </text>
      <text x={x} y={y + size / 2 + 28} textAnchor="middle" className="ms-flow-node-value">
        {value || sub || "—"}
      </text>
      {sub && value ? (
        <text x={x} y={y + size / 2 + 40} textAnchor="middle" className="ms-flow-node-sub" fill={color}>
          {sub}
        </text>
      ) : null}
    </g>
  );
}

function hubSegmentsFromSites(
  sites: MultiSiteSiteEntry[],
  siteColors: Record<string, string>,
): { color: string; pct: number }[] {
  const loads = sites.map((site) => ({
    color: siteColors[site.slug] ?? COLORS.house,
    w: Math.max(0, (site.live.consumptionPowerKw ?? 0) * 1000),
  }));
  const total = loads.reduce((sum, item) => sum + item.w, 0) || 1;
  return loads.filter((item) => item.w >= 25).map((item) => ({ color: item.color, pct: (item.w / total) * 100 }));
}

export function OverviewLivePowerFlow({
  aggregate,
  sites,
  allSites,
  highlightedSlug,
}: {
  aggregate: MultiSiteAggregate;
  sites: MultiSiteSiteEntry[];
  allSites: MultiSiteSiteEntry[];
  highlightedSlug?: string | null;
}) {
  const cx = 200;
  const cy = 200;
  const hub = { x: cx, y: cy };
  const orbitR = 122;
  const consumptionKw = aggregate.consumptionPowerKw ?? 0;
  const siteColors = buildSiteColorMap(allSites.map((s) => s.slug));
  const segments =
    sites.length >= 2
      ? hubSegmentsFromSites(sites, siteColors)
      : [
          { color: COLORS.solar, pct: 100 },
        ].filter(() => (aggregate.solarPowerKw ?? 0) >= 0.025);

  type FlowNodeSpec = {
    id: string;
    kind: "fixed" | "site";
    angle: number;
    glyph: string;
    color: string;
    label: string;
    value: string;
    sub?: string;
    active: boolean;
  };

  const fixedNodes: FlowNodeSpec[] = [
    {
      id: "solar",
      kind: "fixed",
      angle: 300,
      glyph: GLYPHS.sun,
      color: COLORS.solar,
      label: "Solar",
      value: formatFlowPowerFromKw(aggregate.solarPowerKw),
      active: (aggregate.solarPowerKw ?? 0) >= 0.025,
    },
    {
      id: "ev",
      kind: "fixed",
      angle: 40,
      glyph: GLYPHS.plug,
      color: COLORS.ev,
      label: "EV charger",
      value: formatFlowPowerFromKw(aggregate.evPowerKw),
      active: (aggregate.evPowerKw ?? 0) >= 0.025,
    },
    {
      id: "grid",
      kind: "fixed",
      angle: 200,
      glyph: GLYPHS.pylon,
      color: COLORS.grid,
      label: "Grid",
      value: "",
      sub: `← ${formatFlowPowerCompact((aggregate.gridExportPowerKw ?? 0) * 1000)} → ${formatFlowPowerCompact((aggregate.gridImportPowerKw ?? 0) * 1000)}`,
      active:
        (aggregate.gridImportPowerKw ?? 0) >= 0.025 || (aggregate.gridExportPowerKw ?? 0) >= 0.025,
    },
    {
      id: "battery",
      kind: "fixed",
      angle: 250,
      glyph: GLYPHS.battery,
      color: COLORS.battery,
      label: "Batteri",
      value: aggregate.batterySocPercent != null ? `${aggregate.batterySocPercent.toFixed(1)}%` : "—",
      sub:
        (aggregate.batteryChargePowerKw ?? 0) >= 0.025
          ? `↑ ${formatFlowPowerFromKw(aggregate.batteryChargePowerKw)}`
          : (aggregate.batteryDischargePowerKw ?? 0) >= 0.025
            ? `↓ ${formatFlowPowerFromKw(aggregate.batteryDischargePowerKw)}`
            : undefined,
      active:
        (aggregate.batteryChargePowerKw ?? 0) >= 0.025 ||
        (aggregate.batteryDischargePowerKw ?? 0) >= 0.025,
    },
  ];

  const siteAngles = distributeAngles(sites.length, 58, 168);
  const siteNodes: FlowNodeSpec[] = sites.map((site, index) => {
    const kw = site.live.consumptionPowerKw ?? 0;
    const solarKw = site.live.solarPowerKw ?? 0;
    return {
      id: site.slug,
      kind: "site",
      angle: siteAngles[index],
      glyph: GLYPHS.house,
      color: siteColors[site.slug],
      label: site.name,
      value: formatFlowPowerFromKw(kw),
      sub: solarKw >= 0.025 ? `Sol ${formatFlowPowerFromKw(solarKw)}` : undefined,
      active: kw >= 0.025 || solarKw >= 0.025,
    };
  });

  const outerNodes: FlowNodeSpec[] = [...fixedNodes.slice(0, 2), ...siteNodes, ...fixedNodes.slice(2)];

  let ringOffset = 0;
  const ringR = 36;
  const circumference = 2 * Math.PI * ringR;

  return (
    <section className="ms-panel ms-live-flow-panel">
      <header className="ms-panel-header">
        <h2>Live power flow</h2>
      </header>
      <div className="ms-live-flow-wrap">
        <svg viewBox="0 0 400 400" className="ms-live-flow-svg" aria-label="Live energiflöde">
          {outerNodes.map((node) => {
            const pos = polar(cx, cy, orbitR, node.angle);
            const dimmed =
              node.kind === "site" && highlightedSlug != null && node.id !== highlightedSlug;
            return (
              <FlowPath
                key={`path-${node.id}`}
                from={pos}
                to={hub}
                hub={polar(cx, cy, orbitR * 0.55, node.angle)}
                color={node.color}
                active={node.active}
                dimmed={dimmed}
              />
            );
          })}

          <circle cx={cx} cy={cy} r={ringR + 10} fill="rgba(15,23,42,0.65)" stroke="rgba(148,163,184,0.2)" />
          <circle cx={cx} cy={cy} r={ringR} fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth={8} />
          {segments.map((seg, index) => {
            const dash = (seg.pct / 100) * circumference;
            const offset = ringOffset;
            ringOffset += dash;
            return (
              <circle
                key={`${seg.color}-${index}`}
                cx={cx}
                cy={cy}
                r={ringR}
                fill="none"
                stroke={seg.color}
                strokeWidth={8}
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={-offset}
                transform={`rotate(-90 ${cx} ${cy})`}
              />
            );
          })}

          <g transform={`translate(${cx - 12} ${cy - 12}) scale(1)`}>
            <path
              d={GLYPHS.house}
              fill="none"
              stroke={COLORS.house}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </g>
          <text x={cx} y={cy + 28} textAnchor="middle" className="ms-flow-hub-value">
            {formatFlowPowerFromKw(consumptionKw)}
          </text>

          {outerNodes.map((node) => {
            const pos = polar(cx, cy, orbitR, node.angle);
            const dimmed =
              node.kind === "site" && highlightedSlug != null && node.id !== highlightedSlug;
            const emphasized = node.kind === "site" && highlightedSlug === node.id;
            return (
              <OuterNode
                key={`node-${node.id}`}
                x={pos.x}
                y={pos.y}
                glyph={node.glyph}
                color={node.color}
                label={node.label}
                value={node.value}
                sub={node.sub}
                dimmed={dimmed}
                emphasized={emphasized}
              />
            );
          })}
        </svg>
      </div>
    </section>
  );
}
