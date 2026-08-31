import { createSectionNavigation } from "@/lib/hashSectionNavigation";

export type SolarSectionId =
  | "overview"
  | "forecast"
  | "tomorrow"
  | "weather"
  | "performance"
  | "accuracy";

const solarNav = createSectionNavigation<SolarSectionId>({
  defaultSection: "overview",
  pathname: (slug) => `/sites/${slug}/solar`,
  sectionHash: {
    overview: "",
    forecast: "prognos",
    tomorrow: "imorgon",
    weather: "vader",
    performance: "prestanda",
    accuracy: "modellkvalitet",
  },
  sectionLabels: {
    overview: "Översikt",
    forecast: "Prognos",
    tomorrow: "Imorgon",
    weather: "Väder",
    performance: "Prestanda",
    accuracy: "Modellkvalitet",
  },
  sidebarOrder: ["overview", "forecast", "tomorrow", "weather", "performance", "accuracy"],
});

export const SOLAR_SECTION_HASH = solarNav.sectionHash;
export const SOLAR_SECTION_LABELS = solarNav.sectionLabels;
export const parseSolarSection = solarNav.parseSection;
export const solarSectionHref = solarNav.sectionHref;
export const isSolarSectionActive = solarNav.isSectionActive;
export const readSolarSectionFromLocation = solarNav.readSectionFromLocation;
export const navigateSolarSection = solarNav.navigateSection;
export const SOLAR_SIDEBAR_SUBNAV = solarNav.sidebarSubnav;
export const isSolarSidebarNavActive = solarNav.isSidebarNavActive;
export type SolarSidebarNavItem = (typeof solarNav.sidebarSubnav)[number];
