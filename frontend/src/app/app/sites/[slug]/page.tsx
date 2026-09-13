"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { MobileSiteDetailCard } from "@/components/mobile/MobileSiteDetailCard";
import { MobileSummaryLoader } from "@/components/mobile/MobileSummaryLoader";

export default function MobileSiteDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;

  return (
    <MobileSectionPage title="Site" subtitle={slug} backHref="/app/sites">
      <MobileSummaryLoader>
        {({ data }) => {
          const site = data.sites.find((s) => s.slug === slug);
          if (!site) {
            return <p className="mobile-error">Site not in current selection.</p>;
          }
          return (
            <>
              <MobileSiteDetailCard site={site} />
              <ul className="mobile-hub-list">
                <li><Link href={`/sites/${slug}`} className="mobile-hub-link">Full dashboard →</Link></li>
                <li><Link href={`/sites/${slug}/energy`} className="mobile-hub-link">Energy →</Link></li>
                <li><Link href={`/sites/${slug}/ev`} className="mobile-hub-link">Charging →</Link></li>
                <li><Link href={`/sites/${slug}/diagnostics`} className="mobile-hub-link">Diagnostics →</Link></li>
              </ul>
            </>
          );
        }}
      </MobileSummaryLoader>
    </MobileSectionPage>
  );
}
