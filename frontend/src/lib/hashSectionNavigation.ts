/** Custom event — pushState hash updates do not always notify React listeners via hashchange alone. */
export const SECTION_HASH_EVENT = "emic:section-hash";

export function readLocationHash(): string {
  if (typeof window === "undefined") return "";
  const idx = window.location.href.indexOf("#");
  return idx >= 0 ? window.location.href.slice(idx) : "";
}

/** Next.js Link does not fire hashchange on same-page hash navigation — call this instead. */
export function navigateToHashHref(href: string): void {
  if (typeof window === "undefined") return;
  window.history.pushState(null, "", href);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  window.dispatchEvent(new CustomEvent(SECTION_HASH_EVENT));
}

export function subscribeToHashNavigation(onChange: () => void): () => void {
  const handler = () => onChange();
  window.addEventListener("hashchange", handler);
  window.addEventListener("popstate", handler);
  window.addEventListener(SECTION_HASH_EVENT, handler);
  return () => {
    window.removeEventListener("hashchange", handler);
    window.removeEventListener("popstate", handler);
    window.removeEventListener(SECTION_HASH_EVENT, handler);
  };
}

export interface SectionSidebarNavItem<T extends string> {
  id: T;
  label: string;
  href: (slug: string) => string;
}

export interface SectionNavigationConfig<T extends string> {
  defaultSection: T;
  pathname: (slug: string) => string;
  sectionHash: Record<T, string>;
  sectionLabels: Record<T, string>;
  sidebarOrder: T[];
  isSectionActive?: (
    pathname: string,
    slug: string,
    section: T,
    hash: string,
    parseSection: (hash: string) => T,
  ) => boolean;
}

export interface SectionNavigation<T extends string> {
  sectionHash: Record<T, string>;
  sectionLabels: Record<T, string>;
  parseSection: (hash: string) => T;
  sectionHref: (slug: string, section: T) => string;
  isSectionActive: (pathname: string, slug: string, section: T, hash: string) => boolean;
  readSectionFromLocation: () => T;
  navigateSection: (slug: string, section: T) => void;
  sidebarSubnav: SectionSidebarNavItem<T>[];
  isSidebarNavActive: (
    pathname: string,
    slug: string,
    item: SectionSidebarNavItem<T>,
    hash?: string,
  ) => boolean;
}

/** Factory for dashboard hash-section routing (parse, href, navigate, sidebar). */
export function createSectionNavigation<T extends string>(
  config: SectionNavigationConfig<T>,
): SectionNavigation<T> {
  const { defaultSection, pathname, sectionHash, sectionLabels, sidebarOrder, isSectionActive } =
    config;

  function parseSection(hash: string): T {
    const normalized = hash.replace(/^#/, "").toLowerCase();
    const entry = Object.entries(sectionHash).find(([, h]) => h === normalized);
    if (entry) return entry[0] as T;
    return defaultSection;
  }

  function sectionHref(slug: string, section: T): string {
    const base = pathname(slug);
    const hash = sectionHash[section];
    return hash ? `${base}#${hash}` : base;
  }

  function defaultIsSectionActive(pathnameStr: string, slug: string, section: T, hash: string): boolean {
    if (pathnameStr !== pathname(slug)) return false;
    return parseSection(hash) === section;
  }

  function resolveIsSectionActive(pathnameStr: string, slug: string, section: T, hash: string): boolean {
    if (isSectionActive) {
      return isSectionActive(pathnameStr, slug, section, hash, parseSection);
    }
    return defaultIsSectionActive(pathnameStr, slug, section, hash);
  }

  function readSectionFromLocation(): T {
    return parseSection(readLocationHash());
  }

  function navigateSection(slug: string, section: T): void {
    navigateToHashHref(sectionHref(slug, section));
  }

  const sidebarSubnav: SectionSidebarNavItem<T>[] = sidebarOrder.map((id) => ({
    id,
    label: sectionLabels[id],
    href: (slug: string) => sectionHref(slug, id),
  }));

  function isSidebarNavActive(
    pathnameStr: string,
    slug: string,
    item: SectionSidebarNavItem<T>,
    hash = "",
  ): boolean {
    return resolveIsSectionActive(pathnameStr, slug, item.id, hash);
  }

  return {
    sectionHash,
    sectionLabels,
    parseSection,
    sectionHref,
    isSectionActive: resolveIsSectionActive,
    readSectionFromLocation,
    navigateSection,
    sidebarSubnav,
    isSidebarNavActive,
  };
}
