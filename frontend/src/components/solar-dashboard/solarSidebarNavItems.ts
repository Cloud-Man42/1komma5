import {
  isSolarSectionActive,
  solarSectionHref,
  SOLAR_SECTION_LABELS,
  type SolarSectionId,
} from "./solarSection";

export interface SolarSidebarNavItem {
  id: SolarSectionId;
  label: string;
  href: (slug: string) => string;
}

export const SOLAR_SIDEBAR_NAV: SolarSidebarNavItem[] = (
  ["overview", "forecast", "tomorrow", "weather", "performance", "accuracy"] as SolarSectionId[]
).map((id) => ({
  id,
  label: SOLAR_SECTION_LABELS[id],
  href: (slug: string) => solarSectionHref(slug, id),
}));

export function isSolarSidebarNavActive(
  pathname: string,
  slug: string,
  item: SolarSidebarNavItem,
  hash = "",
): boolean {
  return isSolarSectionActive(pathname, slug, item.id, hash);
}
