export type SolarSectionId =
  | "overview"
  | "forecast"
  | "tomorrow"
  | "weather"
  | "performance"
  | "accuracy";

export const SOLAR_SECTION_HASH: Record<SolarSectionId, string> = {
  overview: "",
  forecast: "prognos",
  tomorrow: "imorgon",
  weather: "vader",
  performance: "prestanda",
  accuracy: "modellkvalitet",
};

export const SOLAR_SECTION_LABELS: Record<SolarSectionId, string> = {
  overview: "Översikt",
  forecast: "Prognos",
  tomorrow: "Imorgon",
  weather: "Väder",
  performance: "Prestanda",
  accuracy: "Modellkvalitet",
};

export function parseSolarSection(hash: string): SolarSectionId {
  const normalized = hash.replace(/^#/, "").toLowerCase();
  const entry = Object.entries(SOLAR_SECTION_HASH).find(([, h]) => h === normalized);
  if (entry) return entry[0] as SolarSectionId;
  return "overview";
}

export function solarSectionHref(slug: string, section: SolarSectionId): string {
  const base = `/sites/${slug}/solar`;
  const hash = SOLAR_SECTION_HASH[section];
  return hash ? `${base}#${hash}` : base;
}

export function isSolarSectionActive(
  pathname: string,
  slug: string,
  section: SolarSectionId,
  hash: string,
): boolean {
  if (pathname !== `/sites/${slug}/solar`) return false;
  return parseSolarSection(hash) === section;
}

export function readSolarSectionFromLocation(): SolarSectionId {
  if (typeof window === "undefined") return "overview";
  const idx = window.location.href.indexOf("#");
  const hash = idx >= 0 ? window.location.href.slice(idx) : "";
  return parseSolarSection(hash);
}

export function navigateSolarSection(slug: string, section: SolarSectionId): void {
  if (typeof window === "undefined") return;
  const href = solarSectionHref(slug, section);
  window.history.pushState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}
