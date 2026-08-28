import {
  isVehicleSectionActive,
  vehicleSectionHref,
  VEHICLE_SECTION_LABELS,
  type VehicleSectionId,
} from "./vehicleSection";

export type VehicleSidebarNavId = VehicleSectionId;

export interface VehicleSidebarNavItem {
  id: VehicleSidebarNavId;
  label: string;
  href: (slug: string) => string;
}

export const VEHICLE_SIDEBAR_NAV: VehicleSidebarNavItem[] = (
  [
    "overview",
    "charging",
    "history",
    "status",
    "costs",
    "schedule",
    "settings",
  ] as VehicleSectionId[]
).map((id) => ({
  id,
  label: VEHICLE_SECTION_LABELS[id],
  href: (slug: string) => vehicleSectionHref(slug, id),
}));

export function isVehicleSidebarNavActive(
  pathname: string,
  slug: string,
  item: VehicleSidebarNavItem,
  hash = "",
): boolean {
  return isVehicleSectionActive(pathname, slug, item.id, hash);
}
