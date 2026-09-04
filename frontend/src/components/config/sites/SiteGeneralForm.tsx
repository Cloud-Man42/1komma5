"use client";

import type { Site } from "@/lib/api";
import type { SitesAdminState } from "./useSitesAdmin";

type SiteGeneralFormProps = {
  site: Site;
  admin: SitesAdminState;
  showActions?: boolean;
};

export function SiteGeneralForm({ site, admin, showActions = true }: SiteGeneralFormProps) {
  const { updateSiteField, handleUpdateSite, handleDeleteSite } = admin;

  return (
    <div className="site-block" data-testid={`site-general-${site.slug}`}>
      <div className="form-grid">
        <label className="form-field">
          <span>Namn</span>
          <input
            value={site.name}
            onChange={(e) => updateSiteField(site.slug, { name: e.target.value })}
          />
        </label>
        <label className="form-field">
          <span>Slug</span>
          <input value={site.slug} disabled />
        </label>
        <label className="form-field">
          <span>Tidszon</span>
          <input
            value={site.timezone}
            onChange={(e) => updateSiteField(site.slug, { timezone: e.target.value })}
          />
        </label>
        <label className="form-field form-field-wide">
          <span>HeartBeat system-ID (UUID)</span>
          <input
            value={site.external_system_id ?? ""}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            onChange={(e) =>
              updateSiteField(site.slug, { external_system_id: e.target.value || null })
            }
          />
        </label>
        <label className="form-field">
          <span>Reservpris inköp (kr/kWh)</span>
          <input
            type="number"
            min={0}
            max={20}
            step="0.01"
            value={site.fallback_purchase_price_sek_kwh}
            onChange={(e) =>
              updateSiteField(site.slug, {
                fallback_purchase_price_sek_kwh: Number(e.target.value),
              })
            }
          />
        </label>
        <label className="form-field">
          <span>Total ersättning såld el (kr/kWh)</span>
          <input
            type="number"
            min={0}
            max={20}
            step="0.01"
            value={site.export_compensation_sek_kwh}
            onChange={(e) =>
              updateSiteField(site.slug, {
                export_compensation_sek_kwh: Number(e.target.value),
              })
            }
          />
        </label>
        <label className="form-field">
          <span>Huvudsäkring (A)</span>
          <input
            type="number"
            min={1}
            max={200}
            step="1"
            value={site.main_fuse_a ?? ""}
            placeholder="t.ex. 25"
            onChange={(e) =>
              updateSiteField(site.slug, {
                main_fuse_a: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </label>
        <label className="form-field">
          <span>Säkerhetsmarginal (A)</span>
          <input
            type="number"
            min={0}
            max={50}
            step="0.5"
            value={site.safety_margin_a ?? 2}
            onChange={(e) =>
              updateSiteField(site.slug, { safety_margin_a: Number(e.target.value) })
            }
          />
        </label>
      </div>

      {showActions ? (
        <div className="site-actions">
          <button type="button" className="btn-secondary" onClick={() => handleUpdateSite(site)}>
            Spara anläggning
          </button>
          <button
            type="button"
            className="btn-danger"
            onClick={() => handleDeleteSite(site.slug, site.name)}
          >
            Ta bort
          </button>
        </div>
      ) : null}
    </div>
  );
}
