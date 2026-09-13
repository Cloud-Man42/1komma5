"use client";

import Link from "next/link";
import { TableSkeleton } from "@/components/admin-ui";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";

export default function MobileSitesHubPage() {
  const { loading, accessibleSites, selectedSlugs } = useSiteSelection();
  const sites = accessibleSites.filter((s) => selectedSlugs.includes(s.slug));

  if (loading) return <TableSkeleton rows={4} />;

  return (
    <div className="mobile-hub">
      <h1 className="mobile-hub-title">Sites</h1>
      <ul className="mobile-hub-list">
        {sites.map((site) => (
          <li key={site.slug}>
            <Link href={`/app/sites/${site.slug}`} className="mobile-hub-link">
              <strong>{site.name}</strong>
              <span>Open summary →</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
