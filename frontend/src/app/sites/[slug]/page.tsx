"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertBannerList,
  DashboardSection,
  ErrorState,
  Skeleton,
} from "@/components/dashboard";
import { BatteryCard, EvCard, SolarSummaryCard } from "@/components/dashboard/DetailCards";
import { EnergyTodayChart } from "@/components/dashboard/EnergyTodayChart";
import { LiveEnergyFlow } from "@/components/dashboard/LiveEnergyFlow";
import { OptimizationCard } from "@/components/dashboard/OptimizationCard";
import { SiteHeader } from "@/components/dashboard/SiteHeader";
import { TodaySection } from "@/components/dashboard/TodaySection";
import { useSiteDashboard } from "@/lib/useSiteDashboard";

export default function SiteOverviewPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const { dashboard, error, loading } = useSiteDashboard(slug, 15);

  if (loading && !dashboard) {
    return (
      <div className="dashboard-surface">
        <Skeleton lines={6} />
      </div>
    );
  }

  if (error && !dashboard) {
    return <ErrorState title="Dashboard otillgänglig" text={error} />;
  }

  if (!dashboard) {
    return <ErrorState title="Dashboard otillgänglig" />;
  }

  const reading =
    dashboard.live && dashboard.freshness.updated_at
      ? {
          recorded_at: dashboard.freshness.updated_at,
          solar_production_w: dashboard.live.solar_production_w ?? 0,
          consumption_w: dashboard.live.consumption_w ?? 0,
          grid_import_w: dashboard.live.grid_import_w ?? 0,
          grid_export_w: dashboard.live.grid_export_w ?? 0,
          battery_soc_pct: dashboard.live.battery_soc_pct ?? 0,
          battery_power_w: dashboard.live.battery_power_w ?? 0,
        }
      : null;

  return (
    <>
      <SiteHeader dashboard={dashboard} />
      <AlertBannerList alerts={dashboard.alerts.map((alert) => alert.message_sv)} />

      <DashboardSection title="Live" subtitle="Energiflöde just nu">
        <LiveEnergyFlow
          siteSlug={slug}
          live={dashboard.live}
          reading={reading}
          evPowerW={dashboard.live?.ev_power_w ?? undefined}
          solar={dashboard.solar}
          today={dashboard.today}
        />
      </DashboardSection>

      <div className="dashboard-grid-2">
        <TodaySection today={dashboard.today} />
        <OptimizationCard optimization={dashboard.optimization} />
      </div>

      <EnergyTodayChart siteSlug={slug} />

      <DashboardSection title="Detaljer">
        <div className="dashboard-grid-3">
          <BatteryCard live={dashboard.live} />
          <EvCard ev={dashboard.ev} />
          <SolarSummaryCard solar={dashboard.solar} />
        </div>
      </DashboardSection>

      <p className="muted">
        <Link href={`/sites/${slug}/energy`}>Visa energihistorik</Link>
        {" · "}
        <Link href={`/sites/${slug}/ev`}>Laddboxinställningar</Link>
        {" · "}
        <Link href={`/sites/${slug}/diagnostics`}>Diagnostik</Link>
      </p>
    </>
  );
}
