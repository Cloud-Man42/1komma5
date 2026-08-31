import { createSectionNavigation } from "@/lib/hashSectionNavigation";

export type EconomySectionId =
  | "analysis"
  | "reports"
  | "budget"
  | "settings"
  | "cashflow"
  | "insights"
  | "prices";

const ANALYSIS_DETAIL_SECTIONS: EconomySectionId[] = ["cashflow", "insights", "prices"];

const economyNav = createSectionNavigation<EconomySectionId>({
  defaultSection: "analysis",
  pathname: (slug) => `/sites/${slug}/costs`,
  sectionHash: {
    analysis: "",
    reports: "rapporter",
    budget: "budget",
    settings: "installningar",
    cashflow: "kassaflode",
    insights: "insikter",
    prices: "priser",
  },
  sectionLabels: {
    analysis: "Kostnad & analys",
    reports: "Rapporter",
    budget: "Budget & mål",
    settings: "Inställningar",
    cashflow: "Kassaflödesrapport",
    insights: "Insikter",
    prices: "Prisdetaljer",
  },
  sidebarOrder: ["analysis", "reports", "budget", "settings"],
  isSectionActive(pathname, slug, section, hash, parseSection) {
    if (pathname !== `/sites/${slug}/costs`) {
      return section === "settings" && pathname.startsWith("/config");
    }
    const current = parseSection(hash);
    if (section === "analysis") {
      return current === "analysis" || ANALYSIS_DETAIL_SECTIONS.includes(current);
    }
    return current === section;
  },
});

export const ECONOMY_SECTION_HASH = economyNav.sectionHash;
export const ECONOMY_SECTION_LABELS = economyNav.sectionLabels;
export const parseEconomySection = economyNav.parseSection;
export const economySectionHref = economyNav.sectionHref;
export const isEconomySectionActive = economyNav.isSectionActive;
export const readEconomySectionFromLocation = economyNav.readSectionFromLocation;
export const navigateEconomySection = economyNav.navigateSection;
export const ECONOMY_SIDEBAR_SUBNAV = economyNav.sidebarSubnav;
export const isEconomySidebarSubnavActive = economyNav.isSidebarNavActive;
export type EconomySidebarNavItem = (typeof economyNav.sidebarSubnav)[number];
