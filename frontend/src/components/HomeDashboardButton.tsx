"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { IconHome } from "@/components/pi-dashboard/PiIcons";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";
import { useMobileShell } from "@/lib/useMobileShell";

export function HomeDashboardButton({ className }: { className?: string }) {
  const pathname = usePathname();
  const mobileShell = useMobileShell();
  const { loading, accessibleSites, selectedSlugs, navigateToAllSystemsHome } = useSiteSelection();
  const [busy, setBusy] = useState(false);

  const allSelected =
    accessibleSites.length > 0 &&
    accessibleSites.every((site) => selectedSlugs.includes(site.slug));
  const isHome =
    (pathname === "/app" && allSelected) ||
    (pathname === "/overview" && allSelected && accessibleSites.length > 1) ||
    (accessibleSites.length === 1 &&
      pathname === `/sites/${accessibleSites[0]?.slug}` &&
      allSelected);

  async function onClick() {
    if (busy || loading) return;
    setBusy(true);
    try {
      await navigateToAllSystemsHome({ mobile: mobileShell });
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className={`idash-icon-btn idash-home-btn${isHome ? " idash-home-btn-active" : ""}${className ? ` ${className}` : ""}`}
      aria-label="Hem — alla anläggningar"
      title="Hem — alla anläggningar"
      aria-current={isHome ? "page" : undefined}
      disabled={busy || loading}
      onClick={() => void onClick()}
    >
      <IconHome />
    </button>
  );
}
