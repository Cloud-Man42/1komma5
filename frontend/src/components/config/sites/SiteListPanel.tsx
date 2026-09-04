"use client";

import Link from "next/link";
import { siteConfigHref } from "./siteConfigTabs";
import { useSitesAdmin } from "./useSitesAdmin";

export function SiteListPanel() {
  const admin = useSitesAdmin();
  const { sites, chargersBySite, newSite, setNewSite, loading, error, message, handleCreateSiteClick } =
    admin;

  if (loading) {
    return <p className="muted">Laddar anläggningar…</p>;
  }

  if (error && sites.length === 0) {
    return <p className="form-error">{error}</p>;
  }

  return (
    <div data-testid="site-list-panel">
      <div className="card config-card">
        <h3 className="config-section-title">Lägg till anläggning</h3>
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
      </div>

      {sites.length === 0 ? (
        <p className="muted">Inga anläggningar ännu. Skapa en ovan.</p>
      ) : (
        <div className="config-site-list">
          {sites.map((site) => {
            const chargerCount = chargersBySite[site.slug]?.length ?? 0;
            return (
              <div key={site.slug} className="config-site-row" data-testid={`site-row-${site.slug}`}>
                <div>
                  <h3 className="config-site-row-title">{site.name}</h3>
                  <p className="config-site-row-meta">
                    {site.slug} · {chargerCount} laddbox{chargerCount === 1 ? "" : "ar"}
                    {site.external_system_id ? " · Heartbeat kopplad" : " · Heartbeat saknas"}
                  </p>
                </div>
                <Link href={siteConfigHref(site.slug)} className="btn-secondary">
                  Konfigurera →
                </Link>
              </div>
            );
          })}
        </div>
      )}

      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
