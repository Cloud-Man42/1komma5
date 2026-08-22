"use client";

import { useCallback, useEffect, useState } from "react";
import {
  EvCharger,
  Site,
  createSite,
  deleteEvCharger,
  deleteSite,
  fetchEvChargers,
  fetchSites,
  syncEvChargers,
  updateEvCharger,
  updateSite,
} from "@/lib/api";
import { SolarSiteConfigPanel } from "@/components/SolarSiteConfigPanel";
import { DeadlineInput } from "@/components/DeadlineInput";
import { ChargerSetupWizard } from "@/components/ChargerSetupWizard";
import {
  ChargerCatalogFields,
  legacyCatalogSelection,
  isSmartChargingAvailable,
} from "@/components/ChargerCatalogFields";
import type { ChargerIntegrationMethod } from "@/lib/api";

type NewSiteForm = { slug: string; name: string; timezone: string };

const EMPTY_SITE: NewSiteForm = { slug: "", name: "", timezone: "Europe/Stockholm" };

export function SitesManager() {
  const [sites, setSites] = useState<Site[]>([]);
  const [chargersBySite, setChargersBySite] = useState<Record<string, EvCharger[]>>({});
  const [newSite, setNewSite] = useState<NewSiteForm>(EMPTY_SITE);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wizardSiteSlug, setWizardSiteSlug] = useState<string | null>(null);
  const [integrationMethodsByCharger, setIntegrationMethodsByCharger] = useState<
    Record<number, ChargerIntegrationMethod | null>
  >({});

  const load = useCallback(async () => {
    const siteList = await fetchSites();
    setSites(siteList);
    const chargerMap: Record<string, EvCharger[]> = {};
    await Promise.all(
      siteList.map(async (site) => {
        chargerMap[site.slug] = await fetchEvChargers(site.slug);
      }),
    );
    setChargersBySite(chargerMap);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda anläggningar"));
  }, [load]);

  const handleCreateSiteClick = async () => {
    if (!newSite.slug.trim() || !newSite.name.trim() || !newSite.timezone.trim()) return;
    setError(null);
    setMessage(null);
    try {
      await createSite(newSite);
      setNewSite(EMPTY_SITE);
      await load();
      setMessage("Anläggning tillagd.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte skapa anläggning");
    }
  };

  const handleUpdateSite = async (site: Site) => {
    setError(null);
    try {
      await updateSite(site.slug, {
        name: site.name,
        timezone: site.timezone,
        external_system_id: site.external_system_id,
        fallback_purchase_price_sek_kwh: site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh: site.export_compensation_sek_kwh,
        main_fuse_a: site.main_fuse_a,
        safety_margin_a: site.safety_margin_a,
      });
      await load();
      setMessage(`Anläggning "${site.name}" uppdaterad.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte uppdatera anläggning");
    }
  };

  const handleDeleteSite = async (slug: string, name: string) => {
    if (!confirm(`Ta bort anläggningen "${name}" och all tillhörande data?`)) return;
    setError(null);
    try {
      await deleteSite(slug);
      await load();
      setMessage(`Anläggning "${name}" borttagen.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte ta bort anläggning");
    }
  };

  const handleAddCharger = (slug: string) => {
    setError(null);
    setWizardSiteSlug(slug);
  };

  const handleUpdateCharger = async (slug: string, charger: EvCharger) => {
    setError(null);
    try {
      await updateEvCharger(slug, charger.id, {
        name: charger.name,
        manufacturer: charger.manufacturer,
        model: charger.model,
        heartbeat_ev_id: charger.heartbeat_ev_id,
        heartbeat_charger_id: charger.heartbeat_charger_id,
        chargeamp_charger_id: charger.chargeamp_charger_id,
        bridge_enabled: charger.bridge_enabled,
        virtual_evse_enabled: charger.virtual_evse_enabled,
        max_current_a: charger.max_current_a,
        min_current_a: charger.min_current_a,
        phases: charger.phases,
        nominal_voltage_v: charger.nominal_voltage_v,
        max_power_w: charger.max_power_w,
        max_grid_import_w: charger.max_grid_import_w,
        update_interval_seconds: charger.update_interval_seconds,
        min_change_interval_seconds: charger.min_change_interval_seconds,
        current_hysteresis_a: charger.current_hysteresis_a,
        stale_timeout_seconds: charger.stale_timeout_seconds,
        required_energy_kwh: charger.required_energy_kwh,
        deadline_at: charger.deadline_at,
        clear_deadline_at: !charger.deadline_at,
        solar_start_threshold_w: charger.solar_start_threshold_w,
        solar_stop_threshold_w: charger.solar_stop_threshold_w,
        solar_start_delay_seconds: charger.solar_start_delay_seconds,
        solar_stop_delay_seconds: charger.solar_stop_delay_seconds,
        start_delay_seconds: charger.start_delay_seconds,
        stop_delay_seconds: charger.stop_delay_seconds,
        minimum_run_time_seconds: charger.minimum_run_time_seconds,
        minimum_off_time_seconds: charger.minimum_off_time_seconds,
        temporary_grid_import_allowance_w: charger.temporary_grid_import_allowance_w,
        temporary_grid_import_seconds: charger.temporary_grid_import_seconds,
        grid_deadband_w: charger.grid_deadband_w,
        minimum_current_change_interval_seconds: charger.minimum_current_change_interval_seconds,
        max_current_increase_per_step_a: charger.max_current_increase_per_step_a,
        max_current_decrease_per_step_a: charger.max_current_decrease_per_step_a,
        max_automatic_starts_per_hour: charger.max_automatic_starts_per_hour,
        manufacturer_id: charger.manufacturer_id,
        model_id: charger.model_id,
        integration_method: charger.integration_method,
        external_charger_id: charger.external_charger_id ?? charger.chargeamp_charger_id,
      });
      await load();
      setMessage(`Laddbox "${charger.name}" uppdaterad.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte uppdatera laddbox");
    }
  };

  const handleDeleteCharger = async (slug: string, charger: EvCharger) => {
    if (!confirm(`Ta bort laddboxen "${charger.name}"?`)) return;
    setError(null);
    try {
      await deleteEvCharger(slug, charger.id);
      await load();
      setMessage("Laddbox borttagen.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte ta bort laddbox");
    }
  };

  const handleSyncChargers = async (slug: string) => {
    setError(null);
    try {
      await syncEvChargers(slug);
      await load();
      setMessage("Laddboxar synkade från HeartBeat.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Synkning misslyckades");
    }
  };

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
          <div className="form-grid">
            <label className="form-field">
              <span>Namn</span>
              <input
                value={site.name}
                onChange={(e) =>
                  setSites((current) =>
                    current.map((s) => (s.slug === site.slug ? { ...s, name: e.target.value } : s)),
                  )
                }
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
                onChange={(e) =>
                  setSites((current) =>
                    current.map((s) =>
                      s.slug === site.slug ? { ...s, timezone: e.target.value } : s,
                    ),
                  )
                }
              />
            </label>
            <label className="form-field form-field-wide">
              <span>HeartBeat system-ID (UUID)</span>
              <input
                value={site.external_system_id ?? ""}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                onChange={(e) =>
                  setSites((current) =>
                    current.map((s) =>
                      s.slug === site.slug
                        ? { ...s, external_system_id: e.target.value || null }
                        : s,
                    ),
                  )
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
                  setSites((current) =>
                    current.map((s) =>
                      s.slug === site.slug
                        ? { ...s, fallback_purchase_price_sek_kwh: Number(e.target.value) }
                        : s,
                    ),
                  )
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
                  setSites((current) =>
                    current.map((s) =>
                      s.slug === site.slug
                        ? { ...s, export_compensation_sek_kwh: Number(e.target.value) }
                        : s,
                    ),
                  )
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
                  setSites((current) =>
                    current.map((s) =>
                      s.slug === site.slug
                        ? {
                            ...s,
                            main_fuse_a: e.target.value ? Number(e.target.value) : null,
                          }
                        : s,
                    ),
                  )
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
                  setSites((current) =>
                    current.map((s) =>
                      s.slug === site.slug
                        ? { ...s, safety_margin_a: Number(e.target.value) }
                        : s,
                    ),
                  )
                }
              />
            </label>
          </div>

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
                setMessage("Laddbox tillagd.");
              }}
            />
          ) : null}

          <SolarSiteConfigPanel siteSlug={site.slug} />

          <h4 className="charger-section-title">EV-laddboxar</h4>
          {(chargersBySite[site.slug] ?? []).length === 0 && wizardSiteSlug !== site.slug ? (
            <p className="muted">
              Inga laddboxar konfigurerade. Klicka <strong>Lägg till laddbox</strong> för att välja
              tillverkare och modell.
            </p>
          ) : null}

          {(chargersBySite[site.slug] ?? []).map((charger) => {
            const selectedIntegration = integrationMethodsByCharger[charger.id] ?? null;
            const smartChargingAvailable = isSmartChargingAvailable(selectedIntegration);

            return (
            <div key={charger.id} className="charger-block">
              <div className="form-grid">
                <label className="form-field">
                  <span>Laddboxnamn</span>
                  <input
                    value={charger.name}
                    onChange={(e) =>
                      setChargersBySite((current) => ({
                        ...current,
                        [site.slug]: current[site.slug].map((c) =>
                          c.id === charger.id ? { ...c, name: e.target.value } : c,
                        ),
                      }))
                    }
                  />
                </label>
              </div>

              <ChargerCatalogFields
                idPrefix={`charger-${charger.id}`}
                value={legacyCatalogSelection(charger)}
                onChange={(next) =>
                  setChargersBySite((current) => ({
                    ...current,
                    [site.slug]: current[site.slug].map((c) =>
                      c.id === charger.id
                        ? {
                            ...c,
                            manufacturer_id: next.manufacturerId,
                            model_id: next.modelId,
                            integration_method: next.integrationMethod,
                          }
                        : c,
                    ),
                  }))
                }
                onSelectedMethodChange={(method) =>
                  setIntegrationMethodsByCharger((current) => ({
                    ...current,
                    [charger.id]: method,
                  }))
                }
              />

              <div className="form-grid">
                <label className="form-field">
                  <span>Laddbox-ID</span>
                  <input
                    value={charger.external_charger_id ?? charger.chargeamp_charger_id ?? ""}
                    onChange={(e) =>
                      setChargersBySite((current) => ({
                        ...current,
                        [site.slug]: current[site.slug].map((c) =>
                          c.id === charger.id
                            ? {
                                ...c,
                                chargeamp_charger_id: e.target.value || null,
                                external_charger_id: e.target.value || null,
                              }
                            : c,
                        ),
                      }))
                    }
                  />
                </label>
                <label className="form-field">
                  <span>HeartBeat EV-ID</span>
                  <input
                    value={charger.heartbeat_ev_id ?? ""}
                    onChange={(e) =>
                      setChargersBySite((current) => ({
                        ...current,
                        [site.slug]: current[site.slug].map((c) =>
                          c.id === charger.id ? { ...c, heartbeat_ev_id: e.target.value || null } : c,
                        ),
                      }))
                    }
                  />
                </label>
                <label className="form-field">
                  <span>HeartBeat laddbox-ID</span>
                  <input
                    value={charger.heartbeat_charger_id ?? ""}
                    onChange={(e) =>
                      setChargersBySite((current) => ({
                        ...current,
                        [site.slug]: current[site.slug].map((c) =>
                          c.id === charger.id
                            ? { ...c, heartbeat_charger_id: e.target.value || null }
                            : c,
                        ),
                      }))
                    }
                  />
                </label>
              </div>

              <details className="bridge-settings">
                <summary>Smartladdning (Charge Amps + Heartbeat)</summary>
                <p className="muted">
                  EMIC styr Halo via Charge Amps API med energidata från Heartbeat.
                  Kräver Charge Amps laddbox-ID och aktiv bridge.
                </p>
                {!smartChargingAvailable ? (
                  <p className="wizard-warning">
                    Smartladdning kräver en implementerad integration (t.ex. Charge Amps Cloud API
                    med Halo).
                  </p>
                ) : null}
                <div className="form-grid">
                  <label className="form-field">
                    <span>Bridge aktiv</span>
                    <select
                      value={charger.bridge_enabled ? "true" : "false"}
                      disabled={!smartChargingAvailable}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, bridge_enabled: e.target.value === "true" }
                              : c,
                          ),
                        }))
                      }
                    >
                      <option value="false">Nej</option>
                      <option value="true">Ja</option>
                    </select>
                  </label>
                  <label className="form-field">
                    <span>Virtual EVSE aktiv</span>
                    <select
                      value={charger.virtual_evse_enabled ? "true" : "false"}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, virtual_evse_enabled: e.target.value === "true" }
                              : c,
                          ),
                        }))
                      }
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
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, max_current_a: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Min ström (A)</span>
                    <input
                      type="number"
                      min={0}
                      max={32}
                      value={charger.min_current_a}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, min_current_a: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Faser</span>
                    <select
                      value={charger.phases}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id ? { ...c, phases: Number(e.target.value) } : c,
                          ),
                        }))
                      }
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
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, nominal_voltage_v: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Hysteresis (A)</span>
                    <input
                      type="number"
                      step="0.1"
                      value={charger.current_hysteresis_a}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, current_hysteresis_a: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Stale timeout (s)</span>
                    <input
                      type="number"
                      value={charger.stale_timeout_seconds}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, stale_timeout_seconds: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Sol start (W)</span>
                    <input
                      type="number"
                      value={charger.solar_start_threshold_w ?? 1500}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, solar_start_threshold_w: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Sol stopp (W)</span>
                    <input
                      type="number"
                      value={charger.solar_stop_threshold_w ?? 800}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, solar_stop_threshold_w: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Energibehov (kWh)</span>
                    <input
                      type="number"
                      step="0.1"
                      value={charger.required_energy_kwh ?? ""}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? {
                                  ...c,
                                  required_energy_kwh: e.target.value ? Number(e.target.value) : null,
                                }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field form-field-wide">
                    <span>Klar senast</span>
                    <DeadlineInput
                      value={charger.deadline_at}
                      idPrefix={`config-deadline-${charger.id}`}
                      onChange={(iso) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id ? { ...c, deadline_at: iso } : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Startfördröjning (s)</span>
                    <input
                      type="number"
                      value={charger.start_delay_seconds ?? 120}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, start_delay_seconds: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Stoppfördröjning (s)</span>
                    <input
                      type="number"
                      value={charger.stop_delay_seconds ?? 300}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, stop_delay_seconds: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Min körning (s)</span>
                    <input
                      type="number"
                      value={charger.minimum_run_time_seconds ?? 300}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, minimum_run_time_seconds: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Min paus (s)</span>
                    <input
                      type="number"
                      value={charger.minimum_off_time_seconds ?? 300}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, minimum_off_time_seconds: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Nät deadband (W)</span>
                    <input
                      type="number"
                      value={charger.grid_deadband_w ?? 300}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, grid_deadband_w: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Tillfällig import (W)</span>
                    <input
                      type="number"
                      value={charger.temporary_grid_import_allowance_w ?? 800}
                      onChange={(e) =>
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? {
                                  ...c,
                                  temporary_grid_import_allowance_w: Number(e.target.value),
                                }
                              : c,
                          ),
                        }))
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
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, max_current_increase_per_step_a: Number(e.target.value) }
                              : c,
                          ),
                        }))
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
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, max_current_decrease_per_step_a: Number(e.target.value) }
                              : c,
                          ),
                        }))
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
                        setChargersBySite((current) => ({
                          ...current,
                          [site.slug]: current[site.slug].map((c) =>
                            c.id === charger.id
                              ? { ...c, max_automatic_starts_per_hour: Number(e.target.value) }
                              : c,
                          ),
                        }))
                      }
                    />
                  </label>
                </div>
                <p className="muted">
                  Säkrings- och fasdata från Heartbeat visas som diagnostik. Halo-lastbalanseraren
                  har sista ordet om faktisk laddström — EMIC styr önskad maxström.
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
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => handleUpdateCharger(site.slug, charger)}
                >
                  Spara laddbox
                </button>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => handleDeleteCharger(site.slug, charger)}
                >
                  Ta bort laddbox
                </button>
              </div>
            </div>
            );
          })}

        </div>
      ))}

      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
