"use client";

import { ReactNode } from "react";
import { SiteDashboard } from "@/lib/api";
import { DataFreshness, StatusBadge } from "@/components/dashboard";
import { SiteSwitcher } from "@/components/dashboard/SiteNavigation";

export function SiteHeader({
  dashboard,
  children,
}: {
  dashboard: SiteDashboard;
  children?: ReactNode;
}) {
  const alertTone =
    dashboard.alerts.some((alert) => alert.severity === "danger")
      ? "danger"
      : dashboard.alerts.length > 0
        ? "warning"
        : dashboard.freshness.stale
          ? "warning"
          : "success";

  const statusLabel =
    dashboard.alerts.length > 0
      ? `${dashboard.alerts.length} ${dashboard.alerts.length === 1 ? "problem" : "problem"} behöver uppmärksamhet`
      : dashboard.freshness.stale
        ? "Data inaktuell"
        : "Allt normalt";

  return (
    <header className="site-header">
      <div>
        <SiteSwitcher currentSlug={dashboard.site.slug} />
        <h1 className="site-header-title">{dashboard.site.name}</h1>
        <p className="site-header-meta">{dashboard.site.timezone}</p>
        <div style={{ marginTop: "var(--space-3)", display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
          <StatusBadge label={statusLabel} tone={alertTone} />
          <DataFreshness updatedAt={dashboard.freshness.updated_at} stale={dashboard.freshness.stale} />
        </div>
      </div>
      {children}
    </header>
  );
}
