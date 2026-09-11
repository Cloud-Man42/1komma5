"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  discoverModuleDevices,
  fetchModuleConfig,
  fetchOnboardingCatalog,
  fetchSites,
  getApiBaseUrl,
  onboardModuleDevice,
  testModuleConnection,
  updateModuleConfig,
  type ConnectionTestCapability,
  type DiscoveryDevice,
  type OnboardingCatalogResponse,
  type Site,
} from "@/lib/api";
import { SchemaForm } from "@/components/modules-devices/SchemaForm";
import { ConnectionTestPanel } from "@/components/modules-devices/ConnectionTestPanel";
import { ApiRequestError, parseApiError } from "@/lib/apiError";
import { adminAuthHeaders, adminFetch } from "@/lib/adminAuth";

const STEP_LABELS = [
  "Kategori",
  "Integration",
  "Anläggning",
  "Konfiguration",
  "Testa anslutning",
  "Upptäck enheter",
  "Välj enhet",
  "Granska kapacitet",
  "Aktivera",
  "Klart",
];

export function AddDeviceWizard() {
  const [step, setStep] = useState(1);
  const [catalog, setCatalog] = useState<OnboardingCatalogResponse | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [siteSlug, setSiteSlug] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [moduleId, setModuleId] = useState("");
  const [configValues, setConfigValues] = useState<Record<string, unknown>>({});
  const [configuredFields, setConfiguredFields] = useState<Record<string, boolean>>({});
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const [testOk, setTestOk] = useState<boolean | null>(null);
  const [discovered, setDiscovered] = useState<DiscoveryDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<DiscoveryDevice | null>(null);
  const [capabilities, setCapabilities] = useState<ConnectionTestCapability[]>([]);
  const [onboardResult, setOnboardResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([fetchOnboardingCatalog(), fetchSites()])
      .then(([catalogData, siteData]) => {
        setCatalog(catalogData);
        setSites(siteData);
        if (siteData.length) setSiteSlug(siteData[0].slug);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda data"));
  }, []);

  const selectedModule = useMemo(
    () => catalog?.modules_by_category[categoryId]?.find((item) => item.module_id === moduleId),
    [catalog, categoryId, moduleId],
  );

  const loadModuleConfig = useCallback(async () => {
    if (!moduleId || !siteSlug) return;
    const config = await fetchModuleConfig(siteSlug, moduleId);
    setConfigValues(config.config);
    setConfiguredFields(config.configured_fields);
  }, [moduleId, siteSlug]);

  useEffect(() => {
    if (step === 4 && moduleId && siteSlug) {
      void loadModuleConfig().catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda config"));
    }
  }, [step, moduleId, siteSlug, loadModuleConfig]);

  async function saveConfigAndContinue(values: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
      await updateModuleConfig(siteSlug, moduleId, values);
      setConfigValues(values);
      setStep(5);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara konfiguration");
    } finally {
      setBusy(false);
    }
  }

  async function runConnectionTest() {
    setBusy(true);
    setError(null);
    try {
      const result = await testModuleConnection(siteSlug, moduleId);
      setTestOk(result.success);
      setTestMessage(result.message);
      setCapabilities(result.capabilities);
      if (result.devices_found.length) {
        setDiscovered(result.devices_found);
      }
      if (!result.success) {
        setError(result.message);
        return;
      }
      if (selectedModule?.supports_discovery) {
        setStep(6);
      } else if (result.devices_found.length === 1) {
        setSelectedDevice(result.devices_found[0]);
        setStep(8);
      } else {
        setStep(8);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anslutningstest misslyckades");
    } finally {
      setBusy(false);
    }
  }

  async function runDiscovery() {
    setBusy(true);
    setError(null);
    try {
      const result = await discoverModuleDevices(siteSlug, moduleId);
      if (!result.supported) {
        setStep(8);
        return;
      }
      setDiscovered(result.devices);
      if (!result.devices.length) {
        setError(result.message || "Inga enheter hittades");
        return;
      }
      setStep(7);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery misslyckades");
    } finally {
      setBusy(false);
    }
  }

  async function activateDevice() {
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        friendly_name: selectedDevice?.name ?? configValues.name ?? "Enhet",
        external_device_id: selectedDevice?.external_id,
      };
      if (configValues.api_key) payload.api_key = configValues.api_key;
      const result = await onboardModuleDevice(siteSlug, moduleId, payload);
      setOnboardResult(result.message || "Enheten är onboardad");
      setCapabilities(result.capabilities);
      setStep(10);
    } catch (err) {
      if (err instanceof Error && err.message.includes("409")) {
        setError("Enheten finns redan i systemet");
      } else if (err instanceof ApiRequestError && err.detail.code === "DEVICE_ALREADY_EXISTS") {
        setError(err.detail.message);
      } else {
        setError(err instanceof Error ? err.message : "Onboarding misslyckades");
      }
    } finally {
      setBusy(false);
    }
  }

  async function activateNonDeviceModule() {
    setBusy(true);
    setError(null);
    try {
      const res = await adminFetch(`${getApiBaseUrl()}/api/sites/${siteSlug}/modules/${moduleId}`, {
        method: "PUT",
        headers: { ...adminAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: true }),
      });
      if (!res.ok) throw await parseApiError(res);
      setOnboardResult("Modulen är aktiverad");
      setStep(10);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.detail.message : err instanceof Error ? err.message : "Aktivering misslyckades");
    } finally {
      setBusy(false);
    }
  }

  const isDeviceOnboarding = selectedModule?.device_categories?.some((c) => c !== "energy_provider") ?? false;

  return (
    <div className="config-page" data-testid="add-device-wizard">
      <header className="config-page-header">
        <Link href={`/config/modules-devices?site=${siteSlug || "akarp"}`}>← Avbryt</Link>
        <h1 className="config-page-title">Lägg till enhet</h1>
        <p className="config-page-lead">
          Steg {step}: {STEP_LABELS[step - 1] ?? ""}
        </p>
      </header>
      {error ? <p className="config-error" role="alert">{error}</p> : null}

      {step === 1 && catalog ? (
        <section className="config-panel">
          <h2>Välj kategori</h2>
          <div className="config-card-grid">
            {catalog.categories.map((category) => (
              <button
                key={category.id}
                type="button"
                className="config-card-button"
                onClick={() => {
                  setCategoryId(category.id);
                  setStep(2);
                }}
              >
                <strong>{category.label}</strong>
                <span className="muted">{category.description}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {step === 2 && catalog ? (
        <section className="config-panel">
          <h2>Välj integration</h2>
          <div className="config-card-grid">
            {(catalog.modules_by_category[categoryId] ?? []).map((module) => (
              <button
                key={module.module_id}
                type="button"
                className="config-card-button"
                disabled={!module.onboardable}
                onClick={() => {
                  setModuleId(module.module_id);
                  setStep(3);
                }}
              >
                <strong>{module.name}</strong>
                {module.connection_types?.length ? (
                  <span className="muted">{module.connection_types.join(" · ")}</span>
                ) : null}
                {!module.onboardable ? <span className="muted">Kommer senare</span> : null}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {step === 3 ? (
        <section className="config-panel">
          <h2>Välj anläggning</h2>
          <label className="config-field">
            <span>Anläggning</span>
            <select value={siteSlug} onChange={(event) => setSiteSlug(event.target.value)}>
              {sites.map((site) => (
                <option key={site.slug} value={site.slug}>
                  {site.name}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="config-button" disabled={!siteSlug} onClick={() => setStep(4)}>
            Fortsätt
          </button>
        </section>
      ) : null}

      {step === 4 && selectedModule ? (
        <section className="config-panel">
          <h2>Konfigurera {selectedModule.name}</h2>
          {selectedModule.module_id === "integration.heartbeat" &&
          configuredFields.external_system_id &&
          !configuredFields.password &&
          !configuredFields.api_token ? (
            <p className="config-banner config-banner-warning">
              Heartbeat-kontouppgifter saknas. Konfigurera globala credentials under System.
            </p>
          ) : null}
          <SchemaForm
            schema={selectedModule.configuration_schema ?? { fields: [] }}
            values={configValues}
            configuredFields={configuredFields}
            onSubmit={async (values) => {
              await saveConfigAndContinue(values);
            }}
          />
          {busy ? <p className="muted">Sparar…</p> : null}
        </section>
      ) : null}

      {step === 5 ? (
        <section className="config-panel">
          <h2>Testa anslutning</h2>
          <button type="button" className="config-button" disabled={busy} onClick={() => void runConnectionTest()}>
            {busy ? "Testar…" : "Kör anslutningstest"}
          </button>
          {testMessage ? <p className={testOk ? "muted" : "config-error-inline"}>{testMessage}</p> : null}
        </section>
      ) : null}

      {step === 6 ? (
        <section className="config-panel">
          <h2>Upptäck enheter</h2>
          <button type="button" className="config-button" disabled={busy} onClick={() => void runDiscovery()}>
            {busy ? "Söker…" : "Sök enheter"}
          </button>
        </section>
      ) : null}

      {step === 7 ? (
        <section className="config-panel">
          <h2>Välj enhet</h2>
          {discovered.length ? (
            <div className="config-card-grid">
              {discovered.map((device) => (
                <button
                  key={device.external_id}
                  type="button"
                  className="config-card-button"
                  onClick={() => {
                    setSelectedDevice(device);
                    setStep(8);
                  }}
                >
                  <strong>{device.name}</strong>
                  <span className="muted">{device.manufacturer} {device.model}</span>
                  <span className="muted">ID: {device.external_id}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">Inga enheter hittades</p>
          )}
        </section>
      ) : null}

      {step === 8 ? (
        <section className="config-panel">
          <h2>Granska kapacitet</h2>
          {selectedDevice ? (
            <p>
              Vald enhet: <strong>{selectedDevice.name}</strong> ({selectedDevice.external_id})
            </p>
          ) : null}
          <ul className="config-capability-list">
            {capabilities.map((cap) => (
              <li key={cap.name}>
                {cap.available ? "✓" : "○"} {cap.name} ({cap.kind})
              </li>
            ))}
          </ul>
          <button type="button" className="config-button" onClick={() => setStep(9)}>
            Fortsätt
          </button>
        </section>
      ) : null}

      {step === 9 ? (
        <section className="config-panel">
          <h2>Aktivera</h2>
          <button
            type="button"
            className="config-button"
            disabled={busy}
            onClick={() => void (isDeviceOnboarding ? activateDevice() : activateNonDeviceModule())}
          >
            {busy ? "Aktiverar…" : "Aktivera integration"}
          </button>
        </section>
      ) : null}

      {step === 10 ? (
        <section className="config-panel">
          <p className="config-banner config-banner-success">{onboardResult ?? "Klart"}</p>
          {capabilities.length ? <ConnectionTestPanel result={{ success: true, message: onboardResult ?? "", devices_found: [], capabilities }} /> : null}
          <Link href={`/config/modules-devices?site=${siteSlug}`} className="config-button">
            Till Module Manager
          </Link>
        </section>
      ) : null}
    </div>
  );
}
