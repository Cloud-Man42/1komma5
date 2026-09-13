"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { TableSkeleton } from "@/components/admin-ui";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSiteDetailCard } from "@/components/mobile/MobileSiteDetailCard";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

const IntegrationHealthPanel = dynamic(
  () => import("@/components/IntegrationHealthPanel").then((m) => m.IntegrationHealthPanel),
  { ssr: false, loading: () => <TableSkeleton rows={4} /> },
);

export default function MobileHealthPage() {
  return (
    <MobileSectionPage title="System health" subtitle="Integrations and site status" backHref="/app/more">
      <MobileSummaryLoader>
        {({ data, slugs }) => (
          <>
            {slugs.map((slug) => {
              const site = data.sites.find((s) => s.slug === slug);
              return (
                <section key={slug} className="mobile-hub-group">
                  <h2>{site?.name ?? slug}</h2>
                  <div className="mobile-embed-view">
                    <IntegrationHealthPanel siteSlug={slug} />
                  </div>
                  <Link href={`/sites/${slug}/diagnostics`} className="mobile-drill-link">
                    Full diagnostics →
                  </Link>
                </section>
              );
            })}
          </>
        )}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
