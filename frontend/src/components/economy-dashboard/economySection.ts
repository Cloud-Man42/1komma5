export type EconomySectionId =
  | "analysis"
  | "reports"
  | "budget"
  | "settings"
  | "cashflow"
  | "insights"
  | "prices";

export const ECONOMY_SECTION_HASH: Record<EconomySectionId, string> = {
  analysis: "",
  reports: "rapporter",
  budget: "budget",
  settings: "installningar",
  cashflow: "kassaflode",
  insights: "insikter",
  prices: "priser",
};

export const ECONOMY_SECTION_LABELS: Record<EconomySectionId, string> = {
  analysis: "Kostnad & analys",
  reports: "Rapporter",
  budget: "Budget & mål",
  settings: "Inställningar",
  cashflow: "Kassaflödesrapport",
  insights: "Insikter",
  prices: "Prisdetaljer",
};

const ANALYSIS_DETAIL_SECTIONS: EconomySectionId[] = ["cashflow", "insights", "prices"];

export function parseEconomySection(hash: string): EconomySectionId {
  const normalized = hash.replace(/^#/, "").toLowerCase();
  const entry = Object.entries(ECONOMY_SECTION_HASH).find(([, h]) => h === normalized);
  if (entry) return entry[0] as EconomySectionId;
  return "analysis";
}

export function economySectionHref(slug: string, section: EconomySectionId): string {
  const base = `/sites/${slug}/costs`;
  const hash = ECONOMY_SECTION_HASH[section];
  return hash ? `${base}#${hash}` : base;
}

export function isEconomySectionActive(
  pathname: string,
  slug: string,
  section: EconomySectionId,
  hash: string,
): boolean {
  if (pathname !== `/sites/${slug}/costs`) {
    return section === "settings" && pathname.startsWith("/config");
  }
  const current = parseEconomySection(hash);
  if (section === "analysis") {
    return current === "analysis" || ANALYSIS_DETAIL_SECTIONS.includes(current);
  }
  return current === section;
}

export function readEconomySectionFromLocation(): EconomySectionId {
  if (typeof window === "undefined") return "analysis";
  const idx = window.location.href.indexOf("#");
  const hash = idx >= 0 ? window.location.href.slice(idx) : "";
  return parseEconomySection(hash);
}

export function navigateEconomySection(slug: string, section: EconomySectionId): void {
  if (typeof window === "undefined") return;
  const href = economySectionHref(slug, section);
  window.history.pushState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}
