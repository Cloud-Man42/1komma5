/** SMHI data attribution — single source for UI copy (spec §5). */

export const SMHI_ATTRIBUTION = {
  title: "Väder- och strålningsdata",
  body: "Solprognos och strålningsmodell använder data från SMHI (STRÅNG och SNOW) via öppna API:er. STRÅNG tillhandahåller normaliserad global strålning; SNOW tillhandahåller väderprognos.",
  linkLabel: "SMHI Open Data",
  linkUrl: "https://opendata.smhi.se/",
  license: "Data © SMHI (STRÅNG/SNOW). Användning enligt SMHI:s villkor för öppna data.",
} as const;

export function smhiAttributionLine(): string {
  return `Data: ${SMHI_ATTRIBUTION.license}`;
}
