export const SITE_CONFIG_TABS = [
  { id: "general", label: "Grund" },
  { id: "charging", label: "Laddning" },
  { id: "solar", label: "Sol" },
  { id: "spa", label: "Spa" },
  { id: "vehicles", label: "Fordon" },
] as const;

export type SiteConfigTabId = (typeof SITE_CONFIG_TABS)[number]["id"];

export function parseSiteConfigTab(value: string | null | undefined): SiteConfigTabId {
  const match = SITE_CONFIG_TABS.find((tab) => tab.id === value);
  return match?.id ?? "general";
}

export function siteConfigHref(slug: string, tab: SiteConfigTabId = "general"): string {
  return tab === "general" ? `/config/sites/${slug}` : `/config/sites/${slug}?tab=${tab}`;
}
