"use client";

import dynamic from "next/dynamic";
import { TableSkeleton } from "@/components/admin-ui";
import { MobileOfflineGuard } from "@/components/mobile/MobileOfflineGuard";
import { SiteDataProvider } from "@/lib/SiteDataProvider";

const EvOverview = dynamic(
  () => import("@/components/ev-dashboard/EvOverview").then((m) => m.EvOverview),
  { ssr: false, loading: () => <TableSkeleton rows={6} /> },
);

const SpaOverview = dynamic(
  () => import("@/components/spa-dashboard/SpaOverview").then((m) => m.SpaOverview),
  { ssr: false, loading: () => <TableSkeleton rows={6} /> },
);

const VehicleOverview = dynamic(
  () => import("@/components/vehicle-dashboard/VehicleOverview").then((m) => m.VehicleOverview),
  { ssr: false, loading: () => <TableSkeleton rows={6} /> },
);

function SiteControlEmbed({
  slug,
  kind,
}: {
  slug: string;
  kind: "charging" | "spa" | "vehicle";
}) {
  return (
    <SiteDataProvider slug={slug} refreshSeconds={30}>
      <MobileOfflineGuard>
        <div className="mobile-embed-view">
          {kind === "charging" ? <EvOverview siteSlug={slug} /> : null}
          {kind === "spa" ? <SpaOverview siteSlug={slug} /> : null}
          {kind === "vehicle" ? <VehicleOverview siteSlug={slug} /> : null}
        </div>
      </MobileOfflineGuard>
    </SiteDataProvider>
  );
}

export function MobileChargingView({ slugs, siteNames }: { slugs: string[]; siteNames: Record<string, string> }) {
  if (slugs.length === 1) {
    return <SiteControlEmbed slug={slugs[0]!} kind="charging" />;
  }
  return (
    <>
      {slugs.map((slug) => (
        <section key={slug} className="mobile-hub-group">
          <h2>{siteNames[slug] ?? slug}</h2>
          <SiteControlEmbed slug={slug} kind="charging" />
        </section>
      ))}
    </>
  );
}

export function MobileSpaView({ slugs, siteNames }: { slugs: string[]; siteNames: Record<string, string> }) {
  if (slugs.length === 1) {
    return <SiteControlEmbed slug={slugs[0]!} kind="spa" />;
  }
  return (
    <>
      {slugs.map((slug) => (
        <section key={slug} className="mobile-hub-group">
          <h2>{siteNames[slug] ?? slug}</h2>
          <SiteControlEmbed slug={slug} kind="spa" />
        </section>
      ))}
    </>
  );
}

export function MobileVehicleView({ slugs, siteNames }: { slugs: string[]; siteNames: Record<string, string> }) {
  if (slugs.length === 1) {
    return <SiteControlEmbed slug={slugs[0]!} kind="vehicle" />;
  }
  return (
    <>
      {slugs.map((slug) => (
        <section key={slug} className="mobile-hub-group">
          <h2>{siteNames[slug] ?? slug}</h2>
          <SiteControlEmbed slug={slug} kind="vehicle" />
        </section>
      ))}
    </>
  );
}
