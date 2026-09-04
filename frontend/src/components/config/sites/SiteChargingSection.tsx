"use client";

import { ChargerSetupWizard } from "@/components/ChargerSetupWizard";
import {
  ChargerCatalogFields,
  isSmartChargingAvailable,
  legacyCatalogSelection,
} from "@/components/ChargerCatalogFields";
import { DeadlineInput } from "@/components/DeadlineInput";
import { HeartbeatVirtualBridgePanel } from "@/components/HeartbeatVirtualBridgePanel";
import type { EvCharger, Site } from "@/lib/api";
import type { SitesAdminState } from "./useSitesAdmin";

type SiteChargingSectionProps = {
  site: Site;
  admin: SitesAdminState;
};

export function SiteChargingSection({ site, admin }: SiteChargingSectionProps) {
  const {
    chargersBySite,
    wizardSiteSlug,
    setWizardSiteSlug,
    integrationMethodsByCharger,
    setIntegrationMethodsByCharger,
    load,
    handleSyncChargers,
    handleAddCharger,
    handleUpdateCharger,
    handleDeleteCharger,
    updateCharger,
  } = admin;

  const chargers = chargersBySite[site.slug] ?? [];

  return (
    <div data-testid={`site-charging-${site.slug}`}>
      <div className="site-actions">
        <button type="button" className="btn-secondary" onClick={() => handleSyncChargers(site.slug)}>
          Synka laddboxar från HeartBeat
        </button>
        <button type="button" className="btn-secondary" onClick={() => handleAddCharger(site.slug)}>
          Lägg till laddbox
        </button>
      </div>

      {wizardSiteSlug === site.slug ? (
        <ChargerSetupWizard
          siteSlug={site.slug}
          onClose={() => setWizardSiteSlug(null)}
          onSaved={async () => {
            await load();
          }}
        />
      ) : null}

      <HeartbeatVirtualBridgePanel siteSlug={site.slug} />

      <h4 className="charger-section-title">EV-laddboxar</h4>
      {chargers.length === 0 && wizardSiteSlug !== site.slug ? (
        <p className="muted">
          Inga laddboxar konfigurerade. Klicka <strong>Lägg till laddbox</strong> för att välja
          tillverkare och modell.
        </p>
      ) : null}

      {chargers.map((charger) => (
        <ChargerEditor
          key={charger.id}
          charger={charger}
          selectedIntegration={integrationMethodsByCharger[charger.id] ?? null}
          onIntegrationChange={(method) =>
            setIntegrationMethodsByCharger((current) => ({
              ...current,
              [charger.id]: method,
            }))
          }
          onChange={(patch) => updateCharger(site.slug, charger.id, patch)}
          onSave={() => handleUpdateCharger(site.slug, charger)}
          onDelete={() => handleDeleteCharger(site.slug, charger)}
        />
      ))}
    </div>
  );
}

type ChargerEditorProps = {
  charger: EvCharger;
  selectedIntegration: import("@/lib/api").ChargerIntegrationMethod | null;
  onIntegrationChange: (method: import("@/lib/api").ChargerIntegrationMethod | null) => void;
  onChange: (patch: Partial<EvCharger>) => void;
  onSave: () => void;
  onDelete: () => void;
};

function ChargerEditor({
  charger,
  selectedIntegration,
  onIntegrationChange,
  onChange,
  onSave,
  onDelete,
}: Omit<ChargerEditorProps, "site">) {
  const smartChargingAvailable = isSmartChargingAvailable(selectedIntegration);

  return (
    <div className="charger-block">
      <div className="form-grid">
        <label className="form-field">
          <span>Laddboxnamn</span>
          <input value={charger.name} onChange={(e) => onChange({ name: e.target.value })} />
        </label>
      </div>

      <ChargerCatalogFields
        idPrefix={`charger-${charger.id}`}
        value={legacyCatalogSelection(charger)}
        onChange={(next) =>
          onChange({
            manufacturer_id: next.manufacturerId,
            model_id: next.modelId,
            integration_method: next.integrationMethod,
          })
        }
        onSelectedMethodChange={onIntegrationChange}
      />

      <div className="form-grid">
        <label className="form-field">
          <span>Laddbox-ID</span>
          <input
            value={charger.external_charger_id ?? charger.chargeamp_charger_id ?? ""}
            onChange={(e) =>
              onChange({
                chargeamp_charger_id: e.target.value || null,
                external_charger_id: e.target.value || null,
              })
            }
          />
        </label>
        <label className="form-field">
          <span>HeartBeat EV-ID</span>
          <input
            value={charger.heartbeat_ev_id ?? ""}
            onChange={(e) => onChange({ heartbeat_ev_id: e.target.value || null })}
          />
        </label>
        <label className="form-field">
          <span>HeartBeat laddbox-ID</span>
          <input
            value={charger.heartbeat_charger_id ?? ""}
            onChange={(e) => onChange({ heartbeat_charger_id: e.target.value || null })}
          />
        </label>
      </div>

      <details className="bridge-settings">
        <summary>Smartladdning (Charge Amps + Heartbeat)</summary>
        <p className="muted">
          EMIC styr Halo via Charge Amps API med energidata från Heartbeat. Kräver Charge Amps
          laddbox-ID och aktiv bridge.
        </p>
        {!smartChargingAvailable ? (
          <p className="wizard-warning">
            Smartladdning kräver en implementerad integration (t.ex. Charge Amps Cloud API med
            Halo).
          </p>
        ) : null}
        <div className="form-grid">
          <label className="form-field">
            <span>Bridge aktiv</span>
            <select
              value={charger.bridge_enabled ? "true" : "false"}
              disabled={!smartChargingAvailable}
              onChange={(e) => onChange({ bridge_enabled: e.target.value === "true" })}
            >
              <option value="false">Nej</option>
              <option value="true">Ja</option>
            </select>
          </label>
          <label className="form-field">
            <span>Virtual EVSE aktiv</span>
            <select
              value={charger.virtual_evse_enabled ? "true" : "false"}
              onChange={(e) => onChange({ virtual_evse_enabled: e.target.value === "true" })}
            >
              <option value="false">Nej</option>
              <option value="true">Ja</option>
            </select>
          </label>
          <label className="form-field">
            <span>Max ström (A)</span>
            <input
              type="number"
              min={6}
              max={32}
              value={charger.max_current_a}
              onChange={(e) => onChange({ max_current_a: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Min ström (A)</span>
            <input
              type="number"
              min={0}
              max={32}
              value={charger.min_current_a}
              onChange={(e) => onChange({ min_current_a: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Faser</span>
            <select
              value={charger.phases}
              onChange={(e) => onChange({ phases: Number(e.target.value) })}
            >
              <option value={1}>1-fas</option>
              <option value={3}>3-fas</option>
            </select>
          </label>
          <label className="form-field">
            <span>Nominell spänning (V)</span>
            <input
              type="number"
              value={charger.nominal_voltage_v}
              onChange={(e) => onChange({ nominal_voltage_v: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Hysteresis (A)</span>
            <input
              type="number"
              step="0.1"
              value={charger.current_hysteresis_a}
              onChange={(e) => onChange({ current_hysteresis_a: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Stale timeout (s)</span>
            <input
              type="number"
              value={charger.stale_timeout_seconds}
              onChange={(e) => onChange({ stale_timeout_seconds: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Sol start (W)</span>
            <input
              type="number"
              value={charger.solar_start_threshold_w ?? 1500}
              onChange={(e) => onChange({ solar_start_threshold_w: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Sol stopp (W)</span>
            <input
              type="number"
              value={charger.solar_stop_threshold_w ?? 800}
              onChange={(e) => onChange({ solar_stop_threshold_w: Number(e.target.value) })}
            />
          </label>
          <label className="form-field form-field-wide">
            <span>Klar senast</span>
            <DeadlineInput
              value={charger.deadline_at}
              idPrefix={`config-deadline-${charger.id}`}
              onChange={(iso) => onChange({ deadline_at: iso })}
            />
          </label>
          <label className="form-field">
            <span>Startfördröjning (s)</span>
            <input
              type="number"
              value={charger.start_delay_seconds ?? 120}
              onChange={(e) => onChange({ start_delay_seconds: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Stoppfördröjning (s)</span>
            <input
              type="number"
              value={charger.stop_delay_seconds ?? 300}
              onChange={(e) => onChange({ stop_delay_seconds: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Min körning (s)</span>
            <input
              type="number"
              value={charger.minimum_run_time_seconds ?? 300}
              onChange={(e) => onChange({ minimum_run_time_seconds: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Min paus (s)</span>
            <input
              type="number"
              value={charger.minimum_off_time_seconds ?? 300}
              onChange={(e) => onChange({ minimum_off_time_seconds: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Nät deadband (W)</span>
            <input
              type="number"
              value={charger.grid_deadband_w ?? 300}
              onChange={(e) => onChange({ grid_deadband_w: Number(e.target.value) })}
            />
          </label>
          <label className="form-field">
            <span>Tillfällig import (W)</span>
            <input
              type="number"
              value={charger.temporary_grid_import_allowance_w ?? 800}
              onChange={(e) =>
                onChange({ temporary_grid_import_allowance_w: Number(e.target.value) })
              }
            />
          </label>
          <label className="form-field">
            <span>Ramp upp (A/steg)</span>
            <input
              type="number"
              step="0.1"
              value={charger.max_current_increase_per_step_a ?? 1}
              onChange={(e) =>
                onChange({ max_current_increase_per_step_a: Number(e.target.value) })
              }
            />
          </label>
          <label className="form-field">
            <span>Ramp ned (A/steg)</span>
            <input
              type="number"
              step="0.1"
              value={charger.max_current_decrease_per_step_a ?? 2}
              onChange={(e) =>
                onChange({ max_current_decrease_per_step_a: Number(e.target.value) })
              }
            />
          </label>
          <label className="form-field">
            <span>Max starter/timme</span>
            <input
              type="number"
              min={1}
              max={20}
              value={charger.max_automatic_starts_per_hour ?? 4}
              onChange={(e) =>
                onChange({ max_automatic_starts_per_hour: Number(e.target.value) })
              }
            />
          </label>
        </div>
        <p className="muted">
          Säkrings- och fasdata från Heartbeat visas som diagnostik. Halo-lastbalanseraren har sista
          ordet om faktisk laddström — EMIC styr önskad maxström.
        </p>
        {(charger.last_applied_current_a != null || charger.last_bridge_run_at) && (
          <p className="muted">
            Senast applicerad ström: {charger.last_applied_current_a ?? "—"} A
            {charger.last_bridge_run_at && (
              <> · Bridge körd {new Date(charger.last_bridge_run_at).toLocaleString()}</>
            )}
          </p>
        )}
      </details>

      <div className="site-actions">
        <button type="button" className="btn-secondary" onClick={onSave}>
          Spara laddbox
        </button>
        <button type="button" className="btn-danger" onClick={onDelete}>
          Ta bort laddbox
        </button>
      </div>
    </div>
  );
}
