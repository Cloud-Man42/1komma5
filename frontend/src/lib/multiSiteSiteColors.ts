/** Stable per-site colors for multi-site overview. */

export const SITE_PALETTE = [
  "#a855f7",
  "#06b6d4",
  "#6366f1",
  "#14b8a6",
  "#f97316",
  "#84cc16",
  "#ec4899",
  "#eab308",
] as const;

export function siteColorForIndex(index: number): string {
  return SITE_PALETTE[index % SITE_PALETTE.length];
}

export function buildSiteColorMap(slugs: string[]): Record<string, string> {
  const map: Record<string, string> = {};
  slugs.forEach((slug, index) => {
    map[slug] = siteColorForIndex(index);
  });
  return map;
}
