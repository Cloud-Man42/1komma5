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
import type { ChargerIntegrationMethod } from "@/lib/api";

type NewSiteForm = { slug: string; name: string; timezone: string };

const EMPTY_SITE: NewSiteForm = { slug: "", name: "", timezone: "Europe/Stockholm" };

export function useSitesAdmin() {
  const [sites, setSites] = useState<Site[]>([]);
  const [chargersBySite, setChargersBySite] = useState<Record<string, EvCharger[]>>({});
  const [newSite, setNewSite] = useState<NewSiteForm>(EMPTY_SITE);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wizardSiteSlug, setWizardSiteSlug] = useState<string | null>(null);
  const [integrationMethodsByCharger, setIntegrationMethodsByCharger] = useState<
    Record<number, ChargerIntegrationMethod | null>
  >({});
  const [loading, setLoading] = useState(true);

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
    setLoading(true);
    load()
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda anläggningar"))
      .finally(() => setLoading(false));
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

  const updateSiteField = (slug: string, patch: Partial<Site>) => {
    setSites((current) =>
      current.map((site) => (site.slug === slug ? { ...site, ...patch } : site)),
    );
  };

  const updateCharger = (siteSlug: string, chargerId: number, patch: Partial<EvCharger>) => {
    setChargersBySite((current) => ({
      ...current,
      [siteSlug]: current[siteSlug].map((charger) =>
        charger.id === chargerId ? { ...charger, ...patch } : charger,
      ),
    }));
  };

  return {
    sites,
    chargersBySite,
    newSite,
    setNewSite,
    message,
    error,
    loading,
    wizardSiteSlug,
    setWizardSiteSlug,
    integrationMethodsByCharger,
    setIntegrationMethodsByCharger,
    load,
    handleCreateSiteClick,
    handleUpdateSite,
    handleDeleteSite,
    handleAddCharger,
    handleUpdateCharger,
    handleDeleteCharger,
    handleSyncChargers,
    updateSiteField,
    updateCharger,
  };
}

export type SitesAdminState = ReturnType<typeof useSitesAdmin>;
