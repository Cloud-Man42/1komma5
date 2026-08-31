import { createSectionNavigation } from "@/lib/hashSectionNavigation";

export type EnergySectionId =
  | "flow"
  | "flows"
  | "history"
  | "live"
  | "quality"
  | "peaks"
  | "reports";

const energyNav = createSectionNavigation<EnergySectionId>({
  defaultSection: "flow",
  pathname: (slug) => `/sites/${slug}/energy`,
  sectionHash: {
    flow: "",
    flows: "floden",
    history: "historik",
    live: "realtidsdata",
    quality: "kvalitet",
    peaks: "toppar",
    reports: "rapporter",
  },
  sectionLabels: {
    flow: "Energi",
    flows: "Flöden",
    history: "Historik",
    live: "Realtidsdata",
    quality: "Kvalitet",
    peaks: "Toppar & dalar",
    reports: "Rapporter",
  },
  sidebarOrder: ["flow", "flows", "history", "live", "quality", "peaks", "reports"],
});

export const ENERGY_SECTION_HASH = energyNav.sectionHash;
export const ENERGY_SECTION_LABELS = energyNav.sectionLabels;
export const parseEnergySection = energyNav.parseSection;
export const energySectionHref = energyNav.sectionHref;
export const isEnergySectionActive = energyNav.isSectionActive;
export const readEnergySectionFromLocation = energyNav.readSectionFromLocation;
export const navigateEnergySection = energyNav.navigateSection;
export const ENERGY_SIDEBAR_SUBNAV = energyNav.sidebarSubnav;
export const isEnergySidebarNavActive = energyNav.isSidebarNavActive;
export type EnergySidebarNavItem = (typeof energyNav.sidebarSubnav)[number];
