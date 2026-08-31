import { createSectionNavigation } from "@/lib/hashSectionNavigation";

export type EvSectionId =
  | "overview"
  | "charging"
  | "schedules"
  | "history"
  | "statistics"
  | "settings"
  | "access"
  | "diagnostics";

const evNav = createSectionNavigation<EvSectionId>({
  defaultSection: "overview",
  pathname: (slug) => `/sites/${slug}/ev`,
  sectionHash: {
    overview: "",
    charging: "laddning",
    schedules: "scheman",
    history: "historik",
    statistics: "statistik",
    settings: "installningar",
    access: "atkomst",
    diagnostics: "diagnostik",
  },
  sectionLabels: {
    overview: "Översikt",
    charging: "Laddning",
    schedules: "Scheman",
    history: "Historik",
    statistics: "Statistik",
    settings: "Inställningar",
    access: "Åtkomst & QR",
    diagnostics: "Diagnostik",
  },
  sidebarOrder: [
    "overview",
    "charging",
    "schedules",
    "history",
    "statistics",
    "settings",
    "access",
    "diagnostics",
  ],
  isSectionActive(pathname, slug, section, hash, parseSection) {
    if (pathname !== `/sites/${slug}/ev`) {
      return section === "settings" && pathname.startsWith("/config");
    }
    return parseSection(hash) === section;
  },
});

export const EV_SECTION_HASH = evNav.sectionHash;
export const EV_SECTION_LABELS = evNav.sectionLabels;
export const parseEvSection = evNav.parseSection;
export const evSectionHref = evNav.sectionHref;
export const isEvSectionActive = evNav.isSectionActive;
export const readEvSectionFromLocation = evNav.readSectionFromLocation;
export const navigateEvSection = evNav.navigateSection;
export const EV_SIDEBAR_SUBNAV = evNav.sidebarSubnav;
export const isEvSidebarNavActive = evNav.isSidebarNavActive;
export type EvSidebarNavItem = (typeof evNav.sidebarSubnav)[number];
