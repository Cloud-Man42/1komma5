export type VehicleSectionId =
  | "overview"
  | "charging"
  | "history"
  | "status"
  | "costs"
  | "schedule"
  | "settings";

export const VEHICLE_SECTION_HASH: Record<VehicleSectionId, string> = {
  overview: "",
  charging: "laddning",
  history: "resor",
  status: "status",
  costs: "kostnad",
  schedule: "schema",
  settings: "installningar",
};

export const VEHICLE_SECTION_LABELS: Record<VehicleSectionId, string> = {
  overview: "Översikt",
  charging: "Laddning",
  history: "Laddhistorik",
  status: "Fordonsstatus",
  costs: "Kostnad & analys",
  schedule: "Schema",
  settings: "Inställningar",
};

export function parseVehicleSection(hash: string): VehicleSectionId {
  const normalized = hash.replace(/^#/, "").toLowerCase();
  const entry = Object.entries(VEHICLE_SECTION_HASH).find(([, h]) => h === normalized);
  if (entry) return entry[0] as VehicleSectionId;
  return "overview";
}

export function vehicleSectionHref(slug: string, section: VehicleSectionId): string {
  const base = `/sites/${slug}/vehicle`;
  const hash = VEHICLE_SECTION_HASH[section];
  return hash ? `${base}#${hash}` : base;
}

export function isVehicleSectionActive(
  pathname: string,
  slug: string,
  section: VehicleSectionId,
  hash: string,
): boolean {
  if (pathname !== `/sites/${slug}/vehicle`) {
    return section === "settings" && pathname.startsWith("/config");
  }
  return parseVehicleSection(hash) === section;
}

export function readVehicleSectionFromLocation(): VehicleSectionId {
  if (typeof window === "undefined") return "overview";
  const idx = window.location.href.indexOf("#");
  const hash = idx >= 0 ? window.location.href.slice(idx) : "";
  return parseVehicleSection(hash);
}

/** Next.js Link does not fire hashchange on same-page hash navigation — call this instead. */
export function navigateVehicleSection(slug: string, section: VehicleSectionId): void {
  if (typeof window === "undefined") return;
  const href = vehicleSectionHref(slug, section);
  window.history.pushState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}
