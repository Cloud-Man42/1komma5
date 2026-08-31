/** Pi kiosk section keys — single source of truth for routes and navigation. */
export const PI_SECTIONS = [
  "solar",
  "energy",
  "battery",
  "grid",
  "vehicle",
  "charger",
  "spa",
  "economy",
  "insights",
] as const;

export type PiSection = (typeof PI_SECTIONS)[number];

export function isPiSection(value: string): value is PiSection {
  return (PI_SECTIONS as readonly string[]).includes(value);
}

export function piHref(slug: string, section?: PiSection): string {
  return section ? `/display/${slug}/${section}` : `/display/${slug}`;
}

export type PiSectionMeta = {
  title: string;
  /** Short Swedish label for aria-labels on touch cards. */
  touchLabel: string;
};

export const PI_SECTION_META: Record<PiSection, PiSectionMeta> = {
  solar: { title: "SOL", touchLabel: "Öppna Sol-vyn" },
  energy: { title: "ENERGI", touchLabel: "Öppna Energi-vyn" },
  battery: { title: "BATTERI", touchLabel: "Öppna Batteri-vyn" },
  grid: { title: "NÄT & ENERGIFLÖDE", touchLabel: "Öppna Nät-vyn" },
  vehicle: { title: "FORDON", touchLabel: "Öppna Fordon-vyn" },
  charger: { title: "LADDBOX", touchLabel: "Öppna Laddbox-vyn" },
  spa: { title: "SPA", touchLabel: "Öppna Spa-vyn" },
  economy: { title: "EKONOMI", touchLabel: "Öppna Ekonomi-vyn" },
  insights: { title: "HÖJDPUNKTER", touchLabel: "Öppna Höjdpunkter-vyn" },
};

/** Maps home-screen card keys to their destination section. */
export const PI_CARD_SECTIONS = {
  solarProduction: "solar",
  houseConsumption: "energy",
  battery: "battery",
  gridNet: "grid",
  solarSurplus: "solar",
  energyFlow: "grid",
  vehicle: "vehicle",
  charger: "charger",
  spa: "spa",
  economy: "economy",
  highlights: "insights",
  kpiProduction: "solar",
  kpiConsumption: "energy",
  kpiBatterySoh: "battery",
  kpiSelfSufficiency: "energy",
  kpiSelfUse: "energy",
  kpiPrice: "economy",
} as const satisfies Record<string, PiSection>;
