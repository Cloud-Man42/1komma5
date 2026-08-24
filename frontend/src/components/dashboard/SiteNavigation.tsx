"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Site, fetchSites } from "@/lib/api";

export function SiteSwitcher({ currentSlug }: { currentSlug: string }) {
  const [sites, setSites] = useState<Site[]>([]);

  useEffect(() => {
    fetchSites()
      .then(setSites)
      .catch(() => setSites([]));
  }, []);

  if (sites.length <= 1) return null;

  if (sites.length <= 3) {
    return (
      <div className="site-switcher" role="navigation" aria-label="Byt anläggning">
        {sites.map((site) => (
          <Link
            key={site.slug}
            href={`/sites/${site.slug}`}
            className={`site-switcher-segment ${site.slug === currentSlug ? "site-switcher-segment-active" : ""}`.trim()}
          >
            {site.name}
          </Link>
        ))}
      </div>
    );
  }

  return (
    <label className="site-switcher">
      <span className="muted">Anläggning</span>
      <select
        value={currentSlug}
        onChange={(event) => {
          window.location.href = `/sites/${event.target.value}`;
        }}
      >
        {sites.map((site) => (
          <option key={site.slug} value={site.slug}>
            {site.name}
          </option>
        ))}
      </select>
    </label>
  );
}

export function SiteTabs({
  slug,
  spaEnabled,
  vehicleEnabled,
}: {
  slug: string;
  spaEnabled?: boolean;
  vehicleEnabled?: boolean;
}) {
  const pathname = usePathname();
  const base = `/sites/${slug}`;
  const tabs = [
    { href: base, label: "Översikt", exact: true },
    { href: `${base}/energy`, label: "Energi" },
    { href: `${base}/solar`, label: "Sol" },
    { href: `${base}/ev`, label: "Laddbox" },
    { href: `${base}/costs`, label: "Ekonomi" },
    { href: `${base}/diagnostics`, label: "Diagnostik" },
  ];
  if (spaEnabled) {
    tabs.push({ href: `${base}/spa`, label: "Spa" });
  }
  if (vehicleEnabled) {
    tabs.push({ href: `${base}/vehicle`, label: "Fordon" });
  }

  return (
    <nav className="site-tabs" aria-label="Sitedetaljer">
      {tabs.map((tab) => {
        const active = tab.exact ? pathname === tab.href : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`site-tab ${active ? "site-tab-active" : ""}`.trim()}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
