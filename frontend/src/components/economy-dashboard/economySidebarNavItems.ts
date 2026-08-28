import {
  economySectionHref,
  ECONOMY_SECTION_LABELS,
  isEconomySectionActive,
  type EconomySectionId,
} from "./economySection";

export interface EconomySidebarNavItem {
  id: EconomySectionId;
  label: string;
  href: (slug: string) => string;
}

export const ECONOMY_SIDEBAR_SUBNAV: EconomySidebarNavItem[] = (
  ["analysis", "reports", "budget", "settings"] as EconomySectionId[]
).map((id) => ({
  id,
  label: ECONOMY_SECTION_LABELS[id],
  href: (slug: string) => economySectionHref(slug, id),
}));

export function isEconomySidebarSubnavActive(
  pathname: string,
  slug: string,
  item: EconomySidebarNavItem,
  hash = "",
): boolean {
  return isEconomySectionActive(pathname, slug, item.id, hash);
}
