import {
  evSectionHref,
  EV_SECTION_LABELS,
  isEvSectionActive,
  type EvSectionId,
} from "./evSection";

export interface EvSidebarNavItem {
  id: EvSectionId;
  label: string;
  href: (slug: string) => string;
}

export const EV_SIDEBAR_NAV: EvSidebarNavItem[] = (
  [
    "overview",
    "charging",
    "schedules",
    "history",
    "statistics",
    "settings",
    "access",
    "diagnostics",
  ] as EvSectionId[]
).map((id) => ({
  id,
  label: EV_SECTION_LABELS[id],
  href: (slug: string) => evSectionHref(slug, id),
}));

export function isEvSidebarNavActive(
  pathname: string,
  slug: string,
  item: EvSidebarNavItem,
  hash = "",
): boolean {
  return isEvSectionActive(pathname, slug, item.id, hash);
}
