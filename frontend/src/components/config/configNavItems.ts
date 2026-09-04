export type ConfigNavItem = {
  id: string;
  label: string;
  href: string;
  description: string;
  matchPrefix?: boolean;
};

export const CONFIG_NAV_ITEMS: ConfigNavItem[] = [
  {
    id: "overview",
    label: "Översikt",
    href: "/config",
    description: "Status och snabblänkar",
  },
  {
    id: "system",
    label: "System",
    href: "/config/system",
    description: "Heartbeat, dashboard och laddning",
  },
  {
    id: "sites",
    label: "Anläggningar",
    href: "/config/sites",
    description: "Sites, laddboxar och integrationer",
    matchPrefix: true,
  },
  {
    id: "displays",
    label: "Display & enheter",
    href: "/config/displays",
    description: "Pi-kiosk och widget-enheter",
  },
  {
    id: "admin",
    label: "Admin & säkerhet",
    href: "/config/admin",
    description: "Token och audit-logg",
  },
  {
    id: "integrations",
    label: "Integrationer",
    href: "/config/integrations",
    description: "Mercedes, ChargeFinder m.m.",
  },
];

export function isConfigNavActive(pathname: string, item: ConfigNavItem): boolean {
  if (item.href === "/config") {
    return pathname === "/config";
  }
  if (item.matchPrefix) {
    return pathname === item.href || pathname.startsWith(`${item.href}/`);
  }
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}
