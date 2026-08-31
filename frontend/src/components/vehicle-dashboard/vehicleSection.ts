import { createSectionNavigation } from "@/lib/hashSectionNavigation";

export type VehicleSectionId =
  | "overview"
  | "charging"
  | "history"
  | "status"
  | "costs"
  | "schedule"
  | "settings";

const vehicleNav = createSectionNavigation<VehicleSectionId>({
  defaultSection: "overview",
  pathname: (slug) => `/sites/${slug}/vehicle`,
  sectionHash: {
    overview: "",
    charging: "laddning",
    history: "resor",
    status: "status",
    costs: "kostnad",
    schedule: "schema",
    settings: "installningar",
  },
  sectionLabels: {
    overview: "Översikt",
    charging: "Laddning",
    history: "Laddhistorik",
    status: "Fordonsstatus",
    costs: "Kostnad & analys",
    schedule: "Schema",
    settings: "Inställningar",
  },
  sidebarOrder: ["overview", "charging", "history", "status", "costs", "schedule", "settings"],
  isSectionActive(pathname, slug, section, hash, parseSection) {
    if (pathname !== `/sites/${slug}/vehicle`) {
      return section === "settings" && pathname.startsWith("/config");
    }
    return parseSection(hash) === section;
  },
});

export const VEHICLE_SECTION_HASH = vehicleNav.sectionHash;
export const VEHICLE_SECTION_LABELS = vehicleNav.sectionLabels;
export const parseVehicleSection = vehicleNav.parseSection;
export const vehicleSectionHref = vehicleNav.sectionHref;
export const isVehicleSectionActive = vehicleNav.isSectionActive;
export const readVehicleSectionFromLocation = vehicleNav.readSectionFromLocation;
export const navigateVehicleSection = vehicleNav.navigateSection;
export const VEHICLE_SIDEBAR_SUBNAV = vehicleNav.sidebarSubnav;
export const isVehicleSidebarNavActive = vehicleNav.isSidebarNavActive;
export type VehicleSidebarNavItem = (typeof vehicleNav.sidebarSubnav)[number];
export type VehicleSidebarNavId = VehicleSectionId;
