"use client";

import { ReactNode } from "react";
import type { SiteDashboard, SolarWeather } from "@/lib/api";
import { DashboardSidebar } from "./DashboardSidebar";
import { DashboardTopBar } from "./DashboardTopBar";

export function DashboardShell({
  slug,
  dashboard,
  latitude,
  longitude,
  weather,
  children,
}: {
  slug: string;
  dashboard: SiteDashboard | null;
  latitude?: number | null;
  longitude?: number | null;
  weather?: SolarWeather | null;
  children: ReactNode;
}) {
  return (
    <div className="idash-shell">
      <DashboardSidebar
        slug={slug}
        dashboard={dashboard}
        latitude={latitude}
        longitude={longitude}
        weather={weather}
      />
      <div className="idash-main">
        <DashboardTopBar
          slug={slug}
          spaEnabled={dashboard?.spa_integration_enabled}
          vehicleEnabled={dashboard?.vehicle_integration_enabled}
        />
        <div className="idash-content">{children}</div>
      </div>
    </div>
  );
}
