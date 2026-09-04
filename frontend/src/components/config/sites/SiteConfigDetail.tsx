"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { MercedesAdminPanel } from "@/components/MercedesAdminPanel";
import { SolarSiteConfigPanel } from "@/components/SolarSiteConfigPanel";
import { SpaAdminPanel } from "@/components/SpaAdminPanel";
import { SiteChargingSection } from "./SiteChargingSection";
import { SiteGeneralForm } from "./SiteGeneralForm";
import { SITE_CONFIG_TABS, parseSiteConfigTab, siteConfigHref } from "./siteConfigTabs";
import { useSitesAdmin } from "./useSitesAdmin";

type SiteConfigDetailProps = {
  slug: string;
};

export function SiteConfigDetail({ slug }: SiteConfigDetailProps) {
  const admin = useSitesAdmin();
  const searchParams = useSearchParams();
  const router = useRouter();
  const activeTab = parseSiteConfigTab(searchParams.get("tab"));

  const { sites, loading, error, message } = admin;
  const site = sites.find((entry) => entry.slug === slug);

  if (loading) {
    return <p className="muted">Laddar anläggning…</p>;
  }

  if (!site) {
    return (
      <div>
        <p className="form-error">Anläggningen &quot;{slug}&quot; hittades inte.</p>
        <Link href="/config/sites" className="btn-secondary">
          Tillbaka till listan
        </Link>
      </div>
    );
  }

  const setTab = (tabId: (typeof SITE_CONFIG_TABS)[number]["id"]) => {
    router.replace(siteConfigHref(slug, tabId));
  };

  return (
    <div data-testid="site-config-detail">
      <header className="config-page-header">
        <Link href="/config/sites" className="back-link">
          ← Alla anläggningar
        </Link>
        <h2 className="config-page-title">{site.name}</h2>
        <p className="muted config-page-intro">
          Konfigurera grunddata, laddning, sol, spa och fordon för denna anläggning.
        </p>
      </header>

      <div className="config-site-tabs" role="tablist" aria-label="Anläggningsflikar">
        {SITE_CONFIG_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`config-site-tab${activeTab === tab.id ? " config-site-tab-active" : ""}`}
            onClick={() => setTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "general" ? <SiteGeneralForm site={site} admin={admin} /> : null}
      {activeTab === "charging" ? <SiteChargingSection site={site} admin={admin} /> : null}
      {activeTab === "solar" ? <SolarSiteConfigPanel siteSlug={site.slug} /> : null}
      {activeTab === "spa" ? <SpaAdminPanel siteSlug={site.slug} /> : null}
      {activeTab === "vehicles" ? <MercedesAdminPanel siteSlug={site.slug} /> : null}

      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
