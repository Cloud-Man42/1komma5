/** Multi-site overview and site selection API. */

import { authFetch } from "@/lib/auth";

export interface MultiSiteOverviewResponse {
  generatedAt: string;
  sites: MultiSiteSiteEntry[];
  aggregate: MultiSiteAggregate;
  health: { healthy: number; degraded: number; offline: number };
  dataQuality: {
    partial: boolean;
    sitesRequested: number;
    sitesAvailable: number;
    sitesStale: number;
    message: string | null;
  };
  freshness: {
    freshestAt: string | null;
    oldestAt: string | null;
    maxDataAgeSeconds: number | null;
  };
  currencies: { currency: string; costToday: number | null; savingsToday: number | null }[];
}

export interface MultiSiteSiteEntry {
  slug: string;
  name: string;
  currency?: string;
  health: string;
  healthDetail: string | null;
  available: boolean;
  live: {
    solarPowerKw: number | null;
    consumptionPowerKw: number | null;
    gridImportPowerKw: number | null;
    gridExportPowerKw: number | null;
    batterySocPercent: number | null;
    batteryPowerKw: number | null;
    batteryCapacityKwh?: number | null;
    batteryStoredKwh?: number | null;
    batteryState?: string | null;
    evPowerKw?: number | null;
  };
  today: {
    solarKwh: number | null;
    consumptionKwh: number | null;
    gridImportKwh: number | null;
    gridExportKwh: number | null;
    costToday: number | null;
    savingsToday: number | null;
  };
  error: string | null;
}

export interface MultiSiteAggregate {
  solarPowerKw: number | null;
  consumptionPowerKw: number | null;
  gridImportPowerKw: number | null;
  gridExportPowerKw: number | null;
  gridNetPowerKw: number | null;
  batteryChargePowerKw: number | null;
  batteryDischargePowerKw: number | null;
  batteryCapacityKwh: number | null;
  batteryStoredKwh: number | null;
  batterySocPercent: number | null;
  solarTodayKwh: number | null;
  consumptionTodayKwh: number | null;
  gridImportTodayKwh: number | null;
  gridExportTodayKwh: number | null;
  evPowerKw: number | null;
  bestSolarSiteSlug: string | null;
  bestSolarSiteKwh: number | null;
}

export interface SiteSelectionResponse {
  selectedSiteSlugs: string[];
  accessibleSiteSlugs: string[];
  mode: "none" | "single" | "multi";
}

export async function fetchMultiSiteOverview(siteSlugs: string[]): Promise<MultiSiteOverviewResponse> {
  const res = await authFetch("/api/multi-site/overview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ site_slugs: siteSlugs }),
  });
  if (!res.ok) throw new Error(`Overview failed (${res.status})`);
  return res.json() as Promise<MultiSiteOverviewResponse>;
}

export async function fetchSiteSelection(): Promise<SiteSelectionResponse> {
  const res = await authFetch("/api/user/site-selection");
  if (!res.ok) throw new Error(`Site selection failed (${res.status})`);
  return res.json() as Promise<SiteSelectionResponse>;
}

export async function patchSiteSelection(selectedSiteSlugs: string[]): Promise<SiteSelectionResponse> {
  const res = await authFetch("/api/user/site-selection", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_site_slugs: selectedSiteSlugs }),
  });
  if (!res.ok) throw new Error(`Site selection update failed (${res.status})`);
  return res.json() as Promise<SiteSelectionResponse>;
}
