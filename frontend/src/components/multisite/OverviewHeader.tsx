"use client";

import { HomeDashboardButton } from "@/components/HomeDashboardButton";
import { SiteSelector } from "@/components/site-selector/SiteSelector";
import type { MultiSiteOverviewResponse } from "@/lib/multiSiteApi";
import { formatDateTime } from "@/lib/userAdminUtils";

export function OverviewHeader({
  data,
  totalSiteCount,
}: {
  data: MultiSiteOverviewResponse;
  totalSiteCount?: number;
}) {
  const total = totalSiteCount ?? data.sites.length;
  const inView = data.sites.length;
  const siteLabel =
    total > inView ? `${inView} av ${total} anläggningar i vyn` : `${inView} anläggningar i vyn`;

  return (
    <header className="ms-overview-header">
      <div className="ms-overview-header-row">
        <div>
          <h1 className="ms-overview-title">Multi-Site Overview</h1>
          <p className="muted ms-overview-sub">
            {siteLabel} · Systemhälsa: {data.health.healthy} friska
            {data.health.degraded ? ` · ${data.health.degraded} degraded` : ""}
            {data.health.offline ? ` · ${data.health.offline} offline` : ""}
          </p>
          <div className="ms-chip-row">
            {data.sites.map((s) => (
              <span key={s.slug} className="ms-chip">
                {s.name}
              </span>
            ))}
          </div>
          <p className="muted ms-overview-sub">
            Senast uppdaterad: {formatDateTime(data.freshness.freshestAt)}
          </p>
        </div>
        <div className="ms-overview-header-actions">
          <HomeDashboardButton />
          <SiteSelector compact />
        </div>
      </div>
      {data.dataQuality.partial ? (
        <p className="ms-kpi-partial" role="status">
          {data.dataQuality.message ?? "Partiell data"}
        </p>
      ) : null}
    </header>
  );
}
