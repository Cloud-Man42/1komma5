import type { EquipmentVariants } from "@/lib/energySceneEquipment";
import {
  BATTERY_VARIANTS,
  equipmentPlacement,
  INVERTER_VARIANTS,
  SOLAR_VARIANTS,
  variantMeta,
} from "@/lib/energySceneEquipment";
import type { ScenePoint } from "@/lib/energyFlowSceneLayout";

interface EnergyEquipmentOverlayProps {
  equipment: EquipmentVariants;
  anchors: {
    solar: ScenePoint;
    inverter: ScenePoint;
    battery: ScenePoint;
  };
  editing?: boolean;
}

function SolarPanels({
  variant,
  anchor,
}: {
  variant: EquipmentVariants["solar"];
  anchor: ScenePoint;
}) {
  const meta = variantMeta("solar", variant);
  const box = equipmentPlacement(anchor, meta);
  const panelCount = variant === "panel-full" ? 6 : 4;
  const panelWidth = box.width / panelCount - 0.15;
  const fill =
    variant === "panel-blue" ? "#1e3a8a" : variant === "panel-full" ? "#111827" : "#0f172a";

  return (
    <g className="scene-equipment scene-equipment-solar">
      {Array.from({ length: panelCount }).map((_, index) => (
        <rect
          key={index}
          x={box.x + index * (panelWidth + 0.15)}
          y={box.y}
          width={panelWidth}
          height={box.height}
          rx={0.15}
          fill={fill}
          stroke="#64748b"
          strokeWidth={0.08}
        />
      ))}
    </g>
  );
}

function InverterUnit({
  variant,
  anchor,
}: {
  variant: EquipmentVariants["inverter"];
  anchor: ScenePoint;
}) {
  const meta = variantMeta("inverter", variant);
  const box = equipmentPlacement(anchor, meta);

  return (
    <g className="scene-equipment scene-equipment-inverter">
      <rect
        x={box.x}
        y={box.y}
        width={box.width}
        height={box.height}
        rx={0.25}
        fill="#f4f4f5"
        stroke="#a1a1aa"
        strokeWidth={0.1}
      />
      <rect
        x={box.x + box.width * 0.15}
        y={box.y + box.height * 0.2}
        width={box.width * 0.7}
        height={box.height * 0.12}
        rx={0.08}
        fill="#d4d4d8"
      />
      <rect
        x={box.x + box.width * 0.15}
        y={box.y + box.height * 0.4}
        width={box.width * 0.7}
        height={box.height * 0.12}
        rx={0.08}
        fill="#d4d4d8"
      />
      {variant === "inverter-large" ? (
        <circle cx={box.x + box.width * 0.8} cy={box.y + box.height * 0.75} r={0.25} fill="#22c55e" />
      ) : null}
    </g>
  );
}

function BatteryUnit({
  variant,
  anchor,
}: {
  variant: EquipmentVariants["battery"];
  anchor: ScenePoint;
}) {
  const meta = variantMeta("battery", variant);
  const box = equipmentPlacement(anchor, meta);
  const fill =
    variant === "battery-tower-dark" ? "#27272a" : variant === "battery-cabinet" ? "#e4e4e7" : "#fafafa";
  const accent = variant === "battery-tower-dark" ? "#a855f7" : "#9333ea";

  return (
    <g className="scene-equipment scene-equipment-battery">
      <rect
        x={box.x}
        y={box.y}
        width={box.width}
        height={box.height}
        rx={variant === "battery-cabinet" ? 0.2 : 0.35}
        fill={fill}
        stroke="#a1a1aa"
        strokeWidth={0.1}
      />
      <rect
        x={box.x + box.width * 0.42}
        y={box.y + box.height * 0.12}
        width={box.width * 0.16}
        height={box.height * 0.72}
        rx={0.08}
        fill={accent}
        opacity={0.85}
      />
    </g>
  );
}

export function EnergyEquipmentOverlay({ equipment, anchors, editing = false }: EnergyEquipmentOverlayProps) {
  return (
    <g className={editing ? "scene-equipment-editing" : "scene-equipment-view"} pointerEvents="none">
      <SolarPanels variant={equipment.solar} anchor={anchors.solar} />
      <BatteryUnit variant={equipment.battery} anchor={anchors.battery} />
      <InverterUnit variant={equipment.inverter} anchor={anchors.inverter} />
    </g>
  );
}

export const EQUIPMENT_PICKER_OPTIONS = {
  solar: SOLAR_VARIANTS,
  inverter: INVERTER_VARIANTS,
  battery: BATTERY_VARIANTS,
};
