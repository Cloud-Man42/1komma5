export type EvSectionId =
  | "overview"
  | "charging"
  | "schedules"
  | "history"
  | "statistics"
  | "settings"
  | "access"
  | "diagnostics";

export const EV_SECTION_HASH: Record<EvSectionId, string> = {
  overview: "",
  charging: "laddning",
  schedules: "scheman",
  history: "historik",
  statistics: "statistik",
  settings: "installningar",
  access: "atkomst",
  diagnostics: "diagnostik",
};

export const EV_SECTION_LABELS: Record<EvSectionId, string> = {
  overview: "Översikt",
  charging: "Laddning",
  schedules: "Scheman",
  history: "Historik",
  statistics: "Statistik",
  settings: "Inställningar",
  access: "Åtkomst & QR",
  diagnostics: "Diagnostik",
};

export function parseEvSection(hash: string): EvSectionId {
  const normalized = hash.replace(/^#/, "").toLowerCase();
  const entry = Object.entries(EV_SECTION_HASH).find(([, h]) => h === normalized);
  if (entry) return entry[0] as EvSectionId;
  return "overview";
}

export function evSectionHref(slug: string, section: EvSectionId): string {
  const base = `/sites/${slug}/ev`;
  const hash = EV_SECTION_HASH[section];
  return hash ? `${base}#${hash}` : base;
}

export function isEvSectionActive(
  pathname: string,
  slug: string,
  section: EvSectionId,
  hash: string,
): boolean {
  if (pathname !== `/sites/${slug}/ev`) {
    return section === "settings" && pathname.startsWith("/config");
  }
  return parseEvSection(hash) === section;
}

export function readEvSectionFromLocation(): EvSectionId {
  if (typeof window === "undefined") return "overview";
  const idx = window.location.href.indexOf("#");
  const hash = idx >= 0 ? window.location.href.slice(idx) : "";
  return parseEvSection(hash);
}

export function navigateEvSection(slug: string, section: EvSectionId): void {
  if (typeof window === "undefined") return;
  const href = evSectionHref(slug, section);
  window.history.pushState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}
