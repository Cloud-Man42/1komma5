"use client";

import { MercedesAdminPanel } from "@/components/MercedesAdminPanel";
import { SolarSiteConfigPanel } from "@/components/SolarSiteConfigPanel";
import { SpaAdminPanel } from "@/components/SpaAdminPanel";
import { SiteChargingSection } from "@/components/config/sites/SiteChargingSection";
import { SiteGeneralForm } from "@/components/config/sites/SiteGeneralForm";
import { useSitesAdmin } from "@/components/config/sites/useSitesAdmin";

/** @deprecated Use SiteListPanel + SiteConfigDetail under /config/sites instead. */
export function SitesManager() {
  const admin = useSitesAdmin();
  const { sites, newSite, setNewSite, message, error, handleCreateSiteClick } = admin;

  return (
    <div className="card config-card">
      <h3 className="config-section-title">Anläggningar</h3>
      <p className="muted config-env-intro">
        Lägg till, konfigurera eller ta bort anläggningar. Under varje anläggning finns{" "}
        <strong>Solprognos — plats &amp; anläggning</strong> där du anger koordinater (lat/long),
        kWp och aktiverar PV-prognos. ChargeAmp Halo styrs via Charge Amps API med energidata från
        Heartbeat — synka laddboxar när system-ID och token är konfigurerade.
      </p>

      <div className="site-create-form">
        <div className="form-grid">
          <label className="form-field">
            <span>Slug (URL-id)</span>
            <input
              required
              value={newSite.slug}
              placeholder="min-anlaggning"
              onChange={(e) => setNewSite({ ...newSite, slug: e.target.value.toLowerCase() })}
            />
          </label>
          <label className="form-field">
            <span>Namn</span>
            <input
              required
              value={newSite.name}
              onChange={(e) => setNewSite({ ...newSite, name: e.target.value })}
            />
          </label>
          <label className="form-field">
            <span>Tidszon</span>
            <input
              required
              value={newSite.timezone}
              onChange={(e) => setNewSite({ ...newSite, timezone: e.target.value })}
            />
          </label>
        </div>
        <button type="button" className="btn-secondary" onClick={() => void handleCreateSiteClick()}>
          Lägg till anläggning
        </button>
      </div>

      {sites.map((site) => (
        <div key={site.slug} className="site-block">
          <SiteGeneralForm site={site} admin={admin} />
          <SiteChargingSection site={site} admin={admin} />
          <SolarSiteConfigPanel siteSlug={site.slug} />
          <SpaAdminPanel siteSlug={site.slug} />
          <MercedesAdminPanel siteSlug={site.slug} />
        </div>
      ))}

      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
