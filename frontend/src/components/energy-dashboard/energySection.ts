export type EnergySectionId =
  | "flow"
  | "flows"
  | "history"
  | "live"
  | "quality"
  | "peaks"
  | "reports";

export const ENERGY_SECTION_HASH: Record<EnergySectionId, string> = {
  flow: "",
  flows: "floden",
  history: "historik",
  live: "realtidsdata",
  quality: "kvalitet",
  peaks: "toppar",
  reports: "rapporter",
};

export const ENERGY_SECTION_LABELS: Record<EnergySectionId, string> = {
  flow: "Energi",
  flows: "Flöden",
  history: "Historik",
  live: "Realtidsdata",
  quality: "Kvalitet",
  peaks: "Toppar & dalar",
  reports: "Rapporter",
};

export function parseEnergySection(hash: string): EnergySectionId {
  const normalized = hash.replace(/^#/, "").toLowerCase();
  const entry = Object.entries(ENERGY_SECTION_HASH).find(([, h]) => h === normalized);
  if (entry) return entry[0] as EnergySectionId;
  return "flow";
}

export function energySectionHref(slug: string, section: EnergySectionId): string {
  const base = `/sites/${slug}/energy`;
  const hash = ENERGY_SECTION_HASH[section];
  return hash ? `${base}#${hash}` : base;
}

export function isEnergySectionActive(
  pathname: string,
  slug: string,
  section: EnergySectionId,
  hash: string,
): boolean {
  if (pathname !== `/sites/${slug}/energy`) return false;
  return parseEnergySection(hash) === section;
}

export function readEnergySectionFromLocation(): EnergySectionId {
  if (typeof window === "undefined") return "flow";
  const idx = window.location.href.indexOf("#");
  const hash = idx >= 0 ? window.location.href.slice(idx) : "";
  return parseEnergySection(hash);
}

export function navigateEnergySection(slug: string, section: EnergySectionId): void {
  if (typeof window === "undefined") return;
  const href = energySectionHref(slug, section);
  window.history.pushState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}
