"use client";

import { useId, useMemo, useRef, type CSSProperties } from "react";
import Link from "next/link";
import { EnergySceneCanvas } from "@/components/EnergySceneCanvas";
import type { Reading } from "@/lib/api";
import { formatWatts } from "@/lib/api";
import {
  batteryFlowState,
  computeEnergyFlows,
  computeWireFlows,
  EMPTY_STICKY_WIRE_STATE,
  isFlowActive,
  normalizeFlowValues,
  readingToFlowValues,
  stabilizeWireAnimations,
  type StickyWireState,
  type WireAnimationSlot,
} from "@/lib/energyFlow";
import { wirePathForSlot, sceneEquipmentAnchors } from "@/lib/energySceneConfig";
import { useEnergySceneConfig } from "@/lib/useEnergySceneConfig";
import { WireFlowPulse } from "@/components/WireFlowPulse";
import { GridLawnFlowPulse } from "@/components/GridLawnFlowPulse";
import type { EnergyFlowKind } from "@/lib/energyFlowColors";
import { paletteForFlowKind } from "@/lib/energyFlowColors";

interface EnergyFlowDiagramProps {
  reading: Reading;
  size?: "compact" | "full";
  siteSlug?: string;
  evPowerW?: number;
}

interface WireFlow {
  id: string;
  path: string;
  watts: number;
  kind: EnergyFlowKind;
  slot: WireAnimationSlot;
}

const SLOT_KIND: Record<WireAnimationSlot, EnergyFlowKind> = {
  solar: "solar",
  house: "house-consumption",
  batteryCharge: "battery-charge",
  batteryDischarge: "battery-discharge",
  gridImport: "grid-import",
  gridExport: "grid-export",
};

function formatKwLabel(watts: number, suffix: string): string {
  return `${formatWatts(watts).replace(".", ",")} ${suffix}`;
}

function Callout({
  style,
  primary,
  secondary,
}: {
  style: CSSProperties;
  primary: string;
  secondary?: string;
}) {
  return (
    <div className="energy-photo-callout" style={style}>
      <span className="energy-photo-callout-primary">{primary}</span>
      {secondary ? <span className="energy-photo-callout-secondary">{secondary}</span> : null}
    </div>
  );
}

function NodeBadge({
  title,
  value,
  sub,
  accent,
  compact,
}: {
  title: string;
  value: string;
  sub?: string;
  accent: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`energy-node-badge ${compact ? "energy-node-badge-compact" : ""}`}
      style={{ "--node-accent": accent } as CSSProperties}
    >
      <span className="energy-node-badge-title">{title}</span>
      <span className="energy-node-badge-value">{value}</span>
      {sub ? <span className="energy-node-badge-sub">{sub}</span> : null}
    </div>
  );
}

export function EnergyFlowDiagram({
  reading,
  size = "full",
  siteSlug = "default",
  evPowerW = 0,
}: EnergyFlowDiagramProps) {
  const uid = useId().replace(/:/g, "");
  const { config, ready } = useEnergySceneConfig(siteSlug);
  const values = normalizeFlowValues(readingToFlowValues(reading));
  const flows = computeEnergyFlows(values);
  const wires = computeWireFlows(values);
  const battery = batteryFlowState(values.batteryPowerW);
  const compact = size === "compact";
  const anchors = sceneEquipmentAnchors(config.paths);
  const stickyWireRef = useRef<StickyWireState>(EMPTY_STICKY_WIRE_STATE);
  const wireAnimationSpecs = useMemo(() => {
    const result = stabilizeWireAnimations(values, stickyWireRef.current);
    stickyWireRef.current = result.next;
    return result.specs;
  }, [values]);

  const hubActive =
    wires.solarInverterW >= 25 ||
    wires.houseFeedW >= 25 ||
    wires.batteryChargeW >= 25 ||
    wires.batteryDischargeW >= 25 ||
    wires.gridImportW >= 25 ||
    wires.gridExportW >= 25 ||
    evPowerW >= 25;

  const wireFlows: WireFlow[] = wireAnimationSpecs
    .filter((spec) => isFlowActive(spec.watts))
    .map((spec) => ({
      id: `${uid}-${spec.slot}`,
      path: wirePathForSlot(config.paths, anchors, spec.slot),
      watts: spec.watts,
      kind: SLOT_KIND[spec.slot],
      slot: spec.slot,
    }));

  const lawnGridFlows = wireFlows.filter(
    (wire) => wire.slot === "gridImport" || wire.slot === "gridExport",
  );
  const otherWireFlows = wireFlows.filter(
    (wire) => wire.slot !== "gridImport" && wire.slot !== "gridExport",
  );

  const batteryLabel =
    battery.mode === "charging"
      ? "Batteriladdning"
      : battery.mode === "discharging"
        ? "Batteriurladdning"
        : "Batteri";

  const gridLabel = wires.gridImportW >= 25
    ? "Nätimport"
    : wires.gridExportW >= 25
      ? "Nätinmatning"
      : "Nät";

  const soc = Math.min(100, Math.max(0, values.batterySocPct));

  const legendItems = [
    {
      label: "Sol → Växelriktare",
      watts: wires.solarInverterW,
      kind: "solar" as EnergyFlowKind,
    },
    {
      label: "→ Hushåll",
      watts: wires.houseFeedW,
      kind: "house-consumption" as EnergyFlowKind,
    },
    {
      label: "Sol → Hus",
      watts: flows.solarToHouse,
      kind: "solar" as EnergyFlowKind,
    },
    {
      label: "→ Laddbox",
      watts: evPowerW,
      kind: "house-consumption" as EnergyFlowKind,
    },
    {
      label: "Nät → Hus",
      watts: flows.gridToHouse,
      kind: "grid-import" as EnergyFlowKind,
    },
    {
      label: "Nät → Batteri",
      watts: flows.gridToBattery,
      kind: "grid-import" as EnergyFlowKind,
    },
    {
      label: "→ Nät",
      watts: wires.gridExportW,
      kind: "grid-export" as EnergyFlowKind,
    },
    {
      label: "Sol → Nät",
      watts: flows.solarToGrid,
      kind: "grid-export" as EnergyFlowKind,
    },
    {
      label: "Batteri → Hus",
      watts: flows.batteryToHouse,
      kind: "battery-discharge" as EnergyFlowKind,
    },
    {
      label: "Batteri → Nät",
      watts: flows.batteryToGrid,
      kind: "battery-discharge" as EnergyFlowKind,
    },
    {
      label: "Sol → Batteri",
      watts: flows.solarToBattery,
      kind: "battery-charge" as EnergyFlowKind,
    },
    {
      label: "→ Batteri",
      watts: wires.batteryChargeW,
      kind: "battery-charge" as EnergyFlowKind,
    },
  ];

  const calibrateHref =
    siteSlug === "default" ? "/calibrate" : `/calibrate?site=${encodeURIComponent(siteSlug)}`;

  const houseSecondary =
    evPowerW >= 25 ? `Varav laddbox ${formatWatts(evPowerW)}` : undefined;

  if (!ready) {
    return (
      <div
        className={`energy-flow energy-flow-photo ${compact ? "energy-flow-compact" : "energy-flow-full"}`}
        aria-label="Energiflöde visualisering"
      >
        <div className="energy-flow-canvas energy-flow-loading">Laddar scen…</div>
      </div>
    );
  }

  return (
    <div
      className={`energy-flow energy-flow-photo ${compact ? "energy-flow-compact" : "energy-flow-full"}`}
      aria-label="Energiflöde visualisering"
    >
      {!compact && (
        <div className="energy-flow-toolbar">
          <Link href={calibrateHref} className="energy-flow-customize-link">
            Anpassa scen
          </Link>
        </div>
      )}

      <div className="energy-flow-canvas">
        <div className={`energy-flow-scene-wrap ${hubActive ? "energy-flow-scene-live" : ""}`}>
          <EnergySceneCanvas
            photoUrl={config.photoUrl}
            paths={config.paths}
            equipment={config.equipment}
            editMode={false}
            showEquipment={config.showEquipmentOverlay}
            showWireGuides={false}
            wireOverlay={
              <>
                <defs>
                  <filter id={`pulseGlowGreen-${uid}`} x="-150%" y="-150%" width="400%" height="400%">
                    <feGaussianBlur stdDeviation="0.6" result="blur" />
                    <feMerge>
                      <feMergeNode in="blur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                  <filter id={`pulseGlowPink-${uid}`} x="-150%" y="-150%" width="400%" height="400%">
                    <feGaussianBlur stdDeviation="0.6" result="blur" />
                    <feMerge>
                      <feMergeNode in="blur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>
                {otherWireFlows.map((wire) => (
                  <WireFlowPulse
                    key={`${wire.id}-flow`}
                    path={wire.path}
                    watts={wire.watts}
                    kind={wire.kind}
                  />
                ))}
                {lawnGridFlows.map((wire) => (
                  <GridLawnFlowPulse
                    key={`${uid}-grid-lawn-${wire.slot}`}
                    path={wire.path}
                    watts={wire.watts}
                    mode={wire.slot === "gridExport" ? "export" : "import"}
                    glowFilterId={
                      wire.slot === "gridExport" ? `pulseGlowGreen-${uid}` : `pulseGlowPink-${uid}`
                    }
                  />
                ))}
                {hubActive && (
                  <circle cx={anchors.junction.x} cy={anchors.junction.y} r="0.75" className="energy-hub-glow" />
                )}
              </>
            }
          />

          {!compact && (
            <div className="energy-flow-callouts">
              <Callout
                style={{ left: "4%", top: "4%" }}
                primary={formatKwLabel(wires.houseFeedW, "Hushåll")}
                secondary={houseSecondary}
              />
              <Callout
                style={{ left: "54%", top: "3%" }}
                primary={formatKwLabel(wires.solarInverterW, "Solenergi")}
              />
              <Callout
                style={{ left: "2%", top: "72%" }}
                primary={`${soc.toFixed(0)}% • ${formatWatts(
                  battery.mode === "idle" ? 0 : wires.batteryChargeW || wires.batteryDischargeW,
                ).replace(".", ",")}`}
                secondary={batteryLabel}
              />
              <Callout
                style={{ right: "2%", top: "72%", textAlign: "right" } as CSSProperties}
                primary={formatKwLabel(
                  wires.gridImportW >= 25 ? wires.gridImportW : wires.gridExportW,
                  gridLabel,
                )}
              />
            </div>
          )}
        </div>

        {compact && (
          <div className="energy-flow-hud energy-flow-hud-compact">
            <NodeBadge compact title="Sol" value={formatWatts(wires.solarInverterW)} accent="#ef4444" />
            <NodeBadge compact title="Hus" value={formatWatts(wires.houseFeedW)} accent="#3b82f6" />
            <NodeBadge
              compact
              title="Batteri"
              value={`${soc.toFixed(0)}%`}
              sub={batteryLabel}
              accent="#ef4444"
            />
            <NodeBadge
              compact
              title="Nät"
              value={formatWatts(wires.gridImportW >= 25 ? wires.gridImportW : wires.gridExportW)}
              accent={wires.gridExportW >= 25 && wires.gridImportW < 25 ? "#22c55e" : "#ef4444"}
            />
          </div>
        )}
      </div>

      {!compact && (
        <ul className="energy-flow-legend">
          {legendItems
            .filter((item) => isFlowActive(item.watts))
            .map((item) => (
              <li
                key={item.label}
                style={{ "--flow-accent": paletteForFlowKind(item.kind).glow } as CSSProperties}
              >
                <span className="energy-flow-legend-dot" />
                <span className="energy-flow-legend-text">
                  {item.label}
                  <strong>{formatWatts(item.watts)}</strong>
                </span>
              </li>
            ))}
          {!hubActive && <li className="energy-flow-legend-idle">Systemet i vila — inga aktiva flöden</li>}
        </ul>
      )}
    </div>
  );
}
