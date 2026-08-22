import type { ScenePoint } from "./energyFlowSceneLayout";

export type SolarVariantId = "panel-black" | "panel-blue" | "panel-full";
export type InverterVariantId = "inverter-compact" | "inverter-standard" | "inverter-large";
export type BatteryVariantId = "battery-tower-white" | "battery-tower-dark" | "battery-cabinet";

export type EquipmentVariants = {
  solar: SolarVariantId;
  inverter: InverterVariantId;
  battery: BatteryVariantId;
};

export interface EquipmentVariantMeta {
  id: string;
  label: string;
  width: number;
  height: number;
  anchorX: number;
  anchorY: number;
}

export const DEFAULT_EQUIPMENT_VARIANTS: EquipmentVariants = {
  solar: "panel-black",
  inverter: "inverter-standard",
  battery: "battery-tower-white",
};

export const SOLAR_VARIANTS: EquipmentVariantMeta[] = [
  { id: "panel-black", label: "Svarta paneler", width: 14, height: 5, anchorX: 0.5, anchorY: 1 },
  { id: "panel-blue", label: "Blå paneler", width: 14, height: 5, anchorX: 0.5, anchorY: 1 },
  { id: "panel-full", label: "Fullt tak", width: 22, height: 6, anchorX: 0.5, anchorY: 1 },
];

export const INVERTER_VARIANTS: EquipmentVariantMeta[] = [
  { id: "inverter-compact", label: "Kompakt vägg", width: 3.2, height: 4.5, anchorX: 0.5, anchorY: 0.5 },
  { id: "inverter-standard", label: "Standard vägg", width: 4.2, height: 6, anchorX: 0.5, anchorY: 0.5 },
  { id: "inverter-large", label: "Stor vägg", width: 5.5, height: 7.5, anchorX: 0.5, anchorY: 0.5 },
];

export const BATTERY_VARIANTS: EquipmentVariantMeta[] = [
  { id: "battery-tower-white", label: "Vit torn", width: 5, height: 11, anchorX: 0.5, anchorY: 0.5 },
  { id: "battery-tower-dark", label: "Mörk torn", width: 5, height: 11, anchorX: 0.5, anchorY: 0.5 },
  { id: "battery-cabinet", label: "Golvskåp", width: 7, height: 5, anchorX: 0.5, anchorY: 1 },
];

export function variantMeta(
  type: keyof EquipmentVariants,
  id: string,
): EquipmentVariantMeta {
  const list =
    type === "solar"
      ? SOLAR_VARIANTS
      : type === "inverter"
        ? INVERTER_VARIANTS
        : BATTERY_VARIANTS;
  return list.find((entry) => entry.id === id) ?? list[0];
}

export function equipmentPlacement(
  point: ScenePoint,
  meta: EquipmentVariantMeta,
): { x: number; y: number; width: number; height: number } {
  return {
    x: point.x - meta.width * meta.anchorX,
    y: point.y - meta.height * meta.anchorY,
    width: meta.width,
    height: meta.height,
  };
}

export function isSolarVariantId(value: string): value is SolarVariantId {
  return SOLAR_VARIANTS.some((entry) => entry.id === value);
}

export function isInverterVariantId(value: string): value is InverterVariantId {
  return INVERTER_VARIANTS.some((entry) => entry.id === value);
}

export function isBatteryVariantId(value: string): value is BatteryVariantId {
  return BATTERY_VARIANTS.some((entry) => entry.id === value);
}
