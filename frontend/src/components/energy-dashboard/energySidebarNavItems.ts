import {
  energySectionHref,
  ENERGY_SECTION_LABELS,
  isEnergySectionActive,
  type EnergySectionId,
} from "./energySection";

export interface EnergySidebarNavItem {
  id: EnergySectionId | "overview";
  label: string;
  href: (slug: string) => string;
}

export const ENERGY_SIDEBAR_NAV: EnergySidebarNavItem[] = [
  { id: "overview", label: "Översikt", href: (slug) => `/sites/${slug}` },
  ...(["flow", "flows", "history", "live", "quality", "peaks", "reports"] as EnergySectionId[]).map(
    (id) => ({
      id,
      label: ENERGY_SECTION_LABELS[id],
      href: (slug: string) => energySectionHref(slug, id),
    }),
  ),
];

export function isEnergySidebarNavActive(
  pathname: string,
  slug: string,
  item: EnergySidebarNavItem,
  hash = "",
): boolean {
  if (item.id === "overview") {
    return pathname === `/sites/${slug}`;
  }
  return isEnergySectionActive(pathname, slug, item.id, hash);
}
