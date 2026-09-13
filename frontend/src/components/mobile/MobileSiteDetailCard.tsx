"use client";

import Link from "next/link";
import type { MobileSummaryResponse } from "@/lib/mobileApi";
import { formatFlowPowerFromKw } from "@/lib/multiSiteFlowFormat";

function fmtKw(kw: number | null | undefined): string {
  if (kw == null) return "—";
  return formatFlowPowerFromKw(kw);
}

export function MobileSiteDetailCard({
  site,
}: {
  site: MobileSummaryResponse["sites"][number];
}) {
  const gridLabel =
    site.live.gridImportPowerKw && site.live.gridImportPowerKw > 0
      ? `Import ${fmtKw(site.live.gridImportPowerKw)}`
      : site.live.gridExportPowerKw && site.live.gridExportPowerKw > 0
        ? `Export ${fmtKw(site.live.gridExportPowerKw)}`
        : "Balanced";

  return (
    <article className="mobile-site-card">
      <div className="mobile-site-card-head">
        <h2>{site.name}</h2>
        <span className={`mobile-health mobile-health-${site.health}`}>{site.health}</span>
      </div>
      <div className="mobile-site-card-grid">
        <div><span>Solar</span><strong>{fmtKw(site.live.solarPowerKw)}</strong></div>
        <div><span>Load</span><strong>{fmtKw(site.live.consumptionPowerKw)}</strong></div>
        <div><span>Battery</span><strong>{site.live.batterySocPercent != null ? `${Math.round(site.live.batterySocPercent)}%` : "—"}</strong></div>
        <div><span>Grid</span><strong>{gridLabel}</strong></div>
      </div>
      <div className="mobile-site-card-actions">
        <Link href={`/app/sites/${site.slug}`} className="mobile-site-card-btn">
          Summary
        </Link>
        <Link href={`/sites/${site.slug}`} className="mobile-site-card-btn mobile-site-card-btn-secondary">
          Full dashboard
        </Link>
      </div>
    </article>
  );
}
