"use client";

import { useRef, type ReactNode } from "react";
import { EnergyEquipmentOverlay } from "@/components/EnergyEquipmentOverlay";
import { clientToViewBox, SCENE_VIEWBOX } from "@/lib/energySceneCoords";
import type { EquipmentVariants } from "@/lib/energySceneEquipment";
import { sceneEquipmentAnchors } from "@/lib/energySceneConfig";
import type { CalibratorPaths } from "@/lib/energySceneCalibrator";
import { SCENE_WIRE_IDS, WIRE_COLORS } from "@/lib/energySceneCalibrator";
import type { ScenePoint, SceneWireId } from "@/lib/energyFlowSceneLayout";
import { pointsToPath } from "@/lib/energyFlowSceneLayout";

interface EnergySceneCanvasProps {
  photoUrl: string;
  paths: CalibratorPaths;
  equipment: EquipmentVariants;
  editMode?: boolean;
  activeWire?: SceneWireId;
  selectedIndex?: number | null;
  showWirePreview?: boolean;
  showWireGuides?: boolean;
  showEquipment?: boolean;
  wireOverlay?: ReactNode;
  onCanvasClick?: (point: ScenePoint) => void;
  onPointMove?: (wire: SceneWireId, index: number, point: ScenePoint) => void;
  onPointSelect?: (wire: SceneWireId, index: number) => void;
  ariaLabel?: string;
}

export function EnergySceneCanvas({
  photoUrl,
  paths,
  equipment,
  editMode = false,
  activeWire = "solar-inverter",
  selectedIndex = null,
  showWirePreview = true,
  showWireGuides = false,
  showEquipment = true,
  wireOverlay,
  onCanvasClick,
  onPointMove,
  onPointSelect,
  ariaLabel = "Energiscen",
}: EnergySceneCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ wire: SceneWireId; index: number } | null>(null);
  const anchors = sceneEquipmentAnchors(paths);

  const handleSvgClick = (event: React.MouseEvent<SVGSVGElement>) => {
    if (!editMode || dragRef.current || !onCanvasClick) return;
    const svg = svgRef.current;
    if (!svg) return;
    onCanvasClick(clientToViewBox(svg, event.clientX, event.clientY));
  };

  const handlePointerDown = (
    event: React.PointerEvent<SVGCircleElement>,
    wire: SceneWireId,
    index: number,
  ) => {
    if (!editMode) return;
    event.stopPropagation();
    dragRef.current = { wire, index };
    onPointSelect?.(wire, index);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    const svg = svgRef.current;
    if (!editMode || !drag || !svg || !onPointMove) return;
    onPointMove(drag.wire, drag.index, clientToViewBox(svg, event.clientX, event.clientY));
  };

  const handlePointerUp = () => {
    dragRef.current = null;
  };

  return (
    <div className={`energy-scene-canvas ${editMode ? "energy-scene-canvas-editing" : ""}`}>
      <div className="energy-flow-scene">
        <img
          src={photoUrl}
          alt=""
          aria-hidden="true"
          className="energy-flow-photo-img"
          draggable={false}
        />
        <div className="energy-flow-photo-vignette" aria-hidden="true" />
        <svg
          ref={svgRef}
          viewBox={SCENE_VIEWBOX}
          preserveAspectRatio="xMidYMid slice"
          className={editMode ? "calibrator-overlay" : "energy-flow-overlay energy-scene-wire-overlay"}
          aria-label={ariaLabel}
          onClick={handleSvgClick}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
        >
          {showEquipment ? (
            <EnergyEquipmentOverlay equipment={equipment} anchors={anchors} editing={editMode} />
          ) : null}

          {SCENE_WIRE_IDS.map((id) => {
            const wirePoints = paths[id];
            if (wirePoints.length < 2) return null;
            const color = WIRE_COLORS[id];
            const isActive = editMode && id === activeWire;
            const showPath = editMode || showWireGuides;
            return (
              <g key={id} opacity={editMode ? (isActive ? 1 : 0.55) : 1}>
                {showPath ? (
                  <path
                    d={pointsToPath(wirePoints)}
                    fill="none"
                    stroke={color}
                    strokeWidth={editMode ? (isActive ? 0.35 : 0.25) : 0.3}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className={
                      editMode && showWirePreview && isActive ? "calibrator-path-preview" : undefined
                    }
                  />
                ) : null}
                {editMode
                  ? wirePoints.map((point, index) => (
                      <circle
                        key={`${id}-${index}`}
                        cx={point.x}
                        cy={point.y}
                        r={isActive ? 0.55 : 0.4}
                        fill={selectedIndex === index && isActive ? "#fafafa" : color}
                        stroke="#0a0a0c"
                        strokeWidth={0.12}
                        className="calibrator-handle"
                        onPointerDown={(event) => handlePointerDown(event, id, index)}
                      />
                    ))
                  : null}
              </g>
            );
          })}

          {wireOverlay}
        </svg>
      </div>
    </div>
  );
}
