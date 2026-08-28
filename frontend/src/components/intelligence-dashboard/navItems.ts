export type DashboardNavIcon =
  | "overview"
  | "energy"
  | "solar"
  | "ev"
  | "costs"
  | "diagnostics"
  | "spa"
  | "vehicle"
  | "settings";

export interface DashboardNavItem {
  id: DashboardNavIcon;
  label: string;
  href: (slug: string) => string;
  exact?: boolean;
  optional?: "spa" | "vehicle";
}

export const DASHBOARD_NAV_ITEMS: DashboardNavItem[] = [
  { id: "overview", label: "Översikt", href: (slug) => `/sites/${slug}`, exact: true },
  { id: "energy", label: "Energi", href: (slug) => `/sites/${slug}/energy` },
  { id: "solar", label: "Sol", href: (slug) => `/sites/${slug}/solar` },
  { id: "ev", label: "Laddbox", href: (slug) => `/sites/${slug}/ev` },
  { id: "costs", label: "Ekonomi", href: (slug) => `/sites/${slug}/costs` },
  { id: "diagnostics", label: "Diagnostik", href: (slug) => `/sites/${slug}/diagnostics` },
  { id: "spa", label: "SPA", href: (slug) => `/sites/${slug}/spa`, optional: "spa" },
  { id: "vehicle", label: "Fordon", href: (slug) => `/sites/${slug}/vehicle`, optional: "vehicle" },
  { id: "settings", label: "Inställningar", href: () => "/config" },
];

export function visibleNavItems(
  spaEnabled?: boolean,
  vehicleEnabled?: boolean,
): DashboardNavItem[] {
  return DASHBOARD_NAV_ITEMS.filter((item) => {
    if (item.optional === "spa") return spaEnabled;
    if (item.optional === "vehicle") return vehicleEnabled;
    return true;
  });
}

export function isNavActive(pathname: string, slug: string, item: DashboardNavItem): boolean {
  const href = item.href(slug);
  if (item.exact) return pathname === href;
  if (item.id === "settings") return pathname.startsWith("/config");
  return pathname === href || pathname.startsWith(`${href}/`);
}
