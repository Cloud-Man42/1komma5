"use client";

import type { DisplayOverview } from "@/lib/displayOverview";
import { MISSING, flowNode, kwReading } from "./piDashboardFormatters";
import { PiTouchCard } from "./PiTouchCard";
import { PI_CARD_SECTIONS, PI_SECTION_META, piHref } from "./piSections";

/**
 * Six-node energy flow diagram (sol, batteri, nät -> hus -> laddbox, spa).
 *
 * Coordinates are authored directly in the panel's content box (273x144 CSS px)
 * so the diagram lands exactly where the reference mockup puts it. Arrow
 * direction is driven by live data: `reversed` flips the arrowhead to the start
 * of the path via `auto-start-reverse`.
 *
 * `fit` decides how the viewBox maps onto the card:
 *
 *   - `stretch` maps it non-uniformly onto the box. The home card is the box the
 *     coordinates were drawn for (344x161 — the mockup spreads them ~19% wider
 *     than the viewBox), so this is what puts every node where it was authored.
 *   - `contain` scales uniformly and centres. Any card of another shape needs
 *     this: the detail view's box is nearly three times wider than the home
 *     card's, and stretching into it smeared every glyph sideways while
 *     squeezing each node's label, value and status into one another.
 */

const GLYPHS: Record<string, string> = {
  sun: "M12 8.1a3.9 3.9 0 1 0 0 7.8 3.9 3.9 0 0 0 0-7.8ZM12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.4 5.4l1.5 1.5M17.1 17.1l1.5 1.5M18.6 5.4l-1.5 1.5M6.9 17.1l-1.5 1.5",
  battery: "M7 4.4h10v15.2H7zM10 4.4V2.8h4v1.6M9.4 9.2h5.2v7.4H9.4z",
  pylon: "M5.4 20.6 8.8 3.6h6.4l3.4 17M7.6 13h8.8M6.6 16.8h10.8M9.1 8.8h5.8",
  house: "M3.2 10.6 12 3.8l8.8 6.8M5.6 9.6v10.8h12.8V9.6M9.8 20.4v-5.6h4.4v5.6",
  plug: "M9 3v4.6M15 3v4.6M6.8 7.6h10.4v3.1a5.2 5.2 0 0 1-10.4 0zM12 15.9v5.2",
  spa: "M3.4 13.6h17.2v2.9a3.9 3.9 0 0 1-3.9 3.9H7.3a3.9 3.9 0 0 1-3.9-3.9zM7.8 10.7c0-1.6 1.3-1.8 1.3-3.1 0-1-.7-1.5-1.3-1.9M12 10.7c0-1.6 1.3-1.8 1.3-3.1 0-1-.7-1.5-1.3-1.9M16.2 10.7c0-1.6 1.3-1.8 1.3-3.1 0-1-.7-1.5-1.3-1.9",
};

const ICON_SIZE = 17.5;
const GLYPH_SCALE = 13 / 24;

function FlowNode({
  x,
  y,
  glyph,
  colour,
  label,
  value,
  unit,
  status,
}: {
  x: number;
  y: number;
  glyph: string;
  colour: string;
  label: string;
  value: string;
  unit: string;
  status?: string | null;
}) {
  const glyphOffset = (ICON_SIZE - 24 * GLYPH_SCALE) / 2;
  const textX = x + ICON_SIZE + 10;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={ICON_SIZE}
        height={ICON_SIZE}
        rx="5"
        fill={colour}
        fillOpacity="0.14"
        stroke={colour}
        strokeOpacity="0.34"
        strokeWidth="0.8"
      />
      <g transform={`translate(${x + glyphOffset} ${y + glyphOffset}) scale(${GLYPH_SCALE})`}>
        <path
          d={GLYPHS[glyph]}
          fill="none"
          stroke={colour}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
      <text x={textX} y={y} className="pi-flow-label" fill={colour} dominantBaseline="hanging">
        {label}
      </text>
      {/* Baseline-anchored so the smaller unit sits on the value's baseline. */}
      <text x={textX} y={y + 18} className="pi-flow-value">
        {value}
        {unit ? <tspan fontSize="7" fontWeight="500" dx="2">{unit}</tspan> : null}
      </text>
      {status ? (
        <text x={textX} y={y + 22.5} className="pi-flow-status" fill={colour} dominantBaseline="hanging">
          {status}
        </text>
      ) : null}
    </g>
  );
}

function FlowLink({
  d,
  colour,
  markerId,
  reversed,
  active,
}: {
  d: string;
  colour: string;
  markerId: string;
  reversed: boolean;
  active: boolean;
}) {
  return (
    <path
      d={d}
      fill="none"
      stroke={colour}
      strokeOpacity={active ? 0.95 : 0.26}
      strokeWidth="1.5"
      strokeLinecap="round"
      markerEnd={reversed ? undefined : `url(#${markerId})`}
      markerStart={reversed ? `url(#${markerId})` : undefined}
    />
  );
}

const COLOURS = {
  solar: "#fcc206",
  battery: "#c94ad4",
  grid: "#21cc3e",
  house: "#06baf8",
  charger: "#23ec50",
  spa: "#07baf7",
};

export type PiFlowFit = "stretch" | "contain";

export function PiEnergyFlowDiagram({
  slug,
  data,
  fit = "stretch",
}: {
  slug?: string;
  data: DisplayOverview | null;
  fit?: PiFlowFit;
}) {
  const available = data?.flow?.available !== false && data != null;

  const solar = flowNode(data, "solar");
  const battery = flowNode(data, "battery");
  const grid = flowNode(data, "grid");
  const house = flowNode(data, "house");
  const charger = flowNode(data, "charger");
  const spa = flowNode(data, "spa");

  const batteryCharging = (data?.live?.battery_state_sv ?? "").toLowerCase().startsWith("laddar");
  const gridExporting = data?.live?.grid_direction === "export";

  const houseReading = kwReading(house?.power_kw ?? data?.live?.house_power_kw);

  const link = (value: number | null | undefined) => (value ?? 0) > 0.02;

  const body = (
    <>
      <h2 className="pi-card-title">ENERGIFLÖDE – JUST NU</h2>
      {available ? (
        <svg
          className="pi-flow-svg"
          viewBox="0 0 289.4 161"
          preserveAspectRatio={fit === "contain" ? "xMidYMid meet" : "none"}
          aria-label="Energiflöde just nu"
        >
          <defs>
            {Object.entries(COLOURS).map(([key, colour]) => (
              <marker
                key={key}
                id={`pi-arrow-${key}`}
                viewBox="0 0 8 8"
                refX="6.4"
                refY="4"
                markerWidth="4.4"
                markerHeight="4.4"
                orient="auto-start-reverse"
              >
                <path d="M1 1.2 6.6 4 1 6.8z" fill={colour} />
              </marker>
            ))}
          </defs>

          {/*
            Sources converge on the house's left edge (x 134.5) and loads leave
            from its right edge (x 168.5) at y 80, each on its own elbow so the
            vertical runs stay separated, as in the reference.
          */}
          {/* sol -> hus */}
          <FlowLink
            d="M78 41 H119 Q127 41 127 49 V72 Q127 80 135 80"
            colour={COLOURS.solar}
            markerId="pi-arrow-solar"
            reversed={false}
            active={link(solar?.power_kw)}
          />
          {/* batteri <-> hus */}
          <FlowLink
            d="M78 80 H124"
            colour={COLOURS.battery}
            markerId="pi-arrow-battery"
            reversed={batteryCharging}
            active={link(battery?.power_kw)}
          />
          {/* nät <-> hus */}
          <FlowLink
            d="M78 125 H103 Q111 125 111 117 V88 Q111 80 119 80"
            colour={COLOURS.grid}
            markerId="pi-arrow-grid"
            reversed={gridExporting}
            active={link(grid?.power_kw)}
          />
          {/* hus -> laddbox */}
          <FlowLink
            d="M170 80 H175 Q183 80 183 72 V56 Q183 48 191 48 H199"
            colour={COLOURS.charger}
            markerId="pi-arrow-charger"
            reversed={false}
            active={link(charger?.power_kw)}
          />
          {/* hus -> spa */}
          <FlowLink
            d="M170 80 H175 Q183 80 183 88 V100 Q183 108 191 108 H199"
            colour={COLOURS.spa}
            markerId="pi-arrow-spa"
            reversed={false}
            active={link(spa?.power_kw)}
          />

          <FlowNode
            x={13.5}
            y={33.5}
            glyph="sun"
            colour={COLOURS.solar}
            label="SOL"
            {...kwReading(solar?.power_kw)}
          />
          <FlowNode
            x={13.5}
            y={67.5}
            glyph="battery"
            colour={COLOURS.battery}
            label="BATTERI"
            status={battery?.status_sv ?? null}
            {...kwReading(battery?.power_kw)}
          />
          <FlowNode
            x={13.5}
            y={106.5}
            glyph="pylon"
            colour={COLOURS.grid}
            label="NÄT"
            status={grid?.status_sv ?? null}
            {...kwReading(grid?.power_kw)}
          />

          {/* hus — the visual anchor, sized to the reference's ~30px glyph */}
          <g transform="translate(130.5 56.3) scale(1.72)">
            <path
              d={GLYPHS.house}
              fill="none"
              stroke={COLOURS.house}
              strokeWidth="1.25"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </g>
          <text x={151} y={104} className="pi-flow-house-value" textAnchor="middle">
            {houseReading.value}
            {houseReading.unit ? (
              <tspan fontSize="8" fontWeight="500" dx="2">
                {houseReading.unit}
              </tspan>
            ) : null}
          </text>
          <text
            x={151}
            y={107.5}
            className="pi-flow-label"
            fill={COLOURS.house}
            textAnchor="middle"
            dominantBaseline="hanging"
          >
            HUS
          </text>

          <FlowNode
            x={203.5}
            y={39}
            glyph="plug"
            colour={COLOURS.charger}
            label="LADDBOX"
            status={charger?.status_sv ?? null}
            {...kwReading(charger?.power_kw)}
          />
          <FlowNode
            x={203.5}
            y={99}
            glyph="spa"
            colour={COLOURS.spa}
            label="SPA"
            status={spa?.status_sv ?? null}
            {...kwReading(spa?.power_kw)}
          />
        </svg>
      ) : (
        <div className="pi-empty pi-flow-empty">{data == null ? MISSING : "Data saknas"}</div>
      )}
    </>
  );

  if (slug) {
    return (
      <PiTouchCard
        href={piHref(slug, PI_CARD_SECTIONS.energyFlow)}
        className="pi-card pi-flow"
        ariaLabel={PI_SECTION_META.grid.touchLabel}
      >
        {body}
      </PiTouchCard>
    );
  }

  return <section className="pi-card pi-flow">{body}</section>;
}
