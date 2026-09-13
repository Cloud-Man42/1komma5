/** Mobile PWA summary API. */

import { authFetch } from "@/lib/auth";
import type { MultiSiteOverviewResponse } from "@/lib/multiSiteApi";

export interface MobileWarning {
  slug: string;
  name: string;
  severity: "critical" | "warning" | "info";
  message: string;
  category?: string;
}

export interface MobileQuickAction {
  id: string;
  label: string;
  route: string;
}

export interface MobileSummaryResponse extends MultiSiteOverviewResponse {
  freshnessLabel: string;
  warnings: MobileWarning[];
  quickActions: MobileQuickAction[];
}

export async function fetchMobileSummary(siteSlugs: string[]): Promise<MobileSummaryResponse> {
  const res = await authFetch("/api/mobile/summary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ site_slugs: siteSlugs }),
  });
  if (!res.ok) throw new Error(`Mobile summary failed (${res.status})`);
  return res.json() as Promise<MobileSummaryResponse>;
}
