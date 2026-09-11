"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  discoverModuleDevices,
  fetchExternalModuleConfig,
  fetchStoreModuleDetail,
  fetchStorePreflight,
  installStoreModule,
  testModuleConnection,
  upsertExternalModuleConfig,
  type DiscoveryDevice,
  type StoreModuleDetailResponse,
  type StorePreflightResponse,
} from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { ModuleStoreShell } from "@/components/modules-devices/store/ModuleStoreShell";
import { primaryActionLabel } from "@/components/modules-devices/store/storeLabels";

const DEFAULT_STEPS = ["Trust", "Security", "Permissions", "Compatibility", "Site", "Configuration", "Review"] as const;
const SENSIBO_STEPS = [
  "Trust",
  "Security",
  "Permissions",
  "Compatibility",
  "Site",
  "Credential",
  "Connectivity",
  "Discovery",
  "Devices",
  "Review",
] as const;

function isExternalOnboardModule(moduleId: string): boolean {
  return moduleId === "integration.sensibo";
}

export function InstallWizard({ moduleId }: { moduleId: string }) {
  const [detail, setDetail] = useState<StoreModuleDetailResponse | null>(null);
  const [preflight, setPreflight] = useState<StorePreflightResponse | null>(null);
  const [step, setStep] = useState(0);
  const [siteSlug, setSiteSlug] = useState("");
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [apiKey, setApiKey] = useState("");
  const [credentialConfigured, setCredentialConfigured] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState<string | null>(null);
  const [connectionOk, setConnectionOk] = useState<boolean | null>(null);
  const [discovered, setDiscovered] = useState<DiscoveryDevice[]>([]);
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  const externalOnboard = isExternalOnboardModule(moduleId);
  const steps = useMemo(
    () => (externalOnboard ? [...SENSIBO_STEPS] : [...DEFAULT_STEPS]),
    [externalOnboard],
  );
  const currentStep = steps[step] ?? steps[0];
  const version = detail?.summary.latest_version ?? "1.0.0";

  const load = useCallback(async () => {
    if (!getAdminToken()) {
      setError("Admin token required.");
      return;
    }
    try {
      const d = await fetchStoreModuleDetail(moduleId);
      setDetail(d);
      const pf = await fetchStorePreflight(moduleId, d.summary.latest_version ?? "1.0.0");
      setPreflight(pf);
      if (pf.sites.length > 0) setSiteSlug(pf.sites[0].site_slug);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, [moduleId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!externalOnboard || !siteSlug) return;
    void fetchExternalModuleConfig(siteSlug, moduleId)
      .then((cfg) => {
        setCredentialConfigured(cfg.credential_configured);
        setSelectedDevices(cfg.selected_device_ids);
      })
      .catch(() => undefined);
  }, [externalOnboard, moduleId, siteSlug]);

  async function refreshPreflight() {
    if (!detail) return;
    const pf = await fetchStorePreflight(moduleId, version, { site_slug: siteSlug || undefined, config });
    setPreflight(pf);
  }

  async function saveCredential() {
    if (!siteSlug) {
      setError("Select a site first.");
      return false;
    }
    if (!apiKey.trim() && !credentialConfigured) {
      setError("Sensibo API key is required.");
      return false;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await upsertExternalModuleConfig(siteSlug, moduleId, {
        api_key: apiKey.trim() || undefined,
        poll_interval_seconds: 300,
        selected_device_ids: selectedDevices,
      });
      setCredentialConfigured(result.credential_configured);
      setApiKey("");
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save credential");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function runConnectivityTest() {
    if (!siteSlug) return;
    setBusy(true);
    setError(null);
    try {
      const result = await testModuleConnection(siteSlug, moduleId);
      setConnectionOk(result.success);
      setConnectionMessage(result.message);
    } catch (err) {
      setConnectionOk(false);
      setConnectionMessage(err instanceof Error ? err.message : "Connection test failed");
    } finally {
      setBusy(false);
    }
  }

  async function runDiscovery() {
    if (!siteSlug) return;
    setBusy(true);
    setError(null);
    try {
      const result = await discoverModuleDevices(siteSlug, moduleId);
      setDiscovered(result.devices);
      if (result.devices.length && selectedDevices.length === 0) {
        setSelectedDevices(result.devices.map((d) => d.external_id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveDeviceSelection() {
    if (!siteSlug) return false;
    setBusy(true);
    setError(null);
    try {
      await upsertExternalModuleConfig(siteSlug, moduleId, {
        poll_interval_seconds: 300,
        selected_device_ids: selectedDevices,
      });
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save device selection");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function runInstall() {
    setBusy(true);
    setError(null);
    try {
      const result = await installStoreModule(moduleId, version, { site_slug: siteSlug || undefined, config });
      setDone(result.message);
      if (preflight?.runtime_blocked) {
        setDone(`${result.message}. ${preflight.runtime_message}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Install failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleNext() {
    if (currentStep === "Site" || currentStep === "Configuration") {
      await refreshPreflight();
    }
    if (currentStep === "Credential") {
      const ok = await saveCredential();
      if (!ok) return;
    }
    if (currentStep === "Connectivity") {
      await runConnectivityTest();
    }
    if (currentStep === "Discovery") {
      await runDiscovery();
    }
    if (currentStep === "Devices") {
      const ok = await saveDeviceSelection();
      if (!ok) return;
    }
    setStep((s) => s + 1);
  }

  return (
    <>
      <ModulesDevicesNav />
      <ModuleStoreShell>
        <h2 className="config-panel-title">Install {detail?.summary.display_name ?? moduleId}</h2>
        {error ? <p className="config-error">{error}</p> : null}
        {done ? (
          <p className="config-banner success">{done}</p>
        ) : (
          <>
            <ol className="store-wizard-steps">
              {steps.map((label, i) => (
                <li key={label} className={i === step ? "active" : i < step ? "done" : ""}>
                  {label}
                </li>
              ))}
            </ol>
            {currentStep === "Trust" && preflight ? (
              <section className="config-panel">
                <p>Publisher: {preflight.display_name}</p>
                <p>Trust tier: {preflight.trust_tier}</p>
                <p>Publisher status: {preflight.publisher_status}</p>
              </section>
            ) : null}
            {currentStep === "Security" && preflight ? (
              <section className="config-panel">
                <p>{preflight.policy.explanation}</p>
                <p>Decision: {preflight.policy.decision}</p>
              </section>
            ) : null}
            {currentStep === "Permissions" && preflight ? (
              <section className="config-panel">
                {preflight.permissions.map((p) => (
                  <p key={p.permission}>
                    {p.label} ({p.risk_level})
                  </p>
                ))}
              </section>
            ) : null}
            {currentStep === "Compatibility" && preflight ? (
              <section className="config-panel">
                <p>{preflight.compatibility.compatible ? "Compatible" : "Incompatible"}</p>
                {preflight.compatibility.reasons.map((r) => (
                  <p key={r}>{r}</p>
                ))}
              </section>
            ) : null}
            {currentStep === "Site" && preflight ? (
              <section className="config-panel">
                <label>
                  Site
                  <select
                    className="config-input"
                    value={siteSlug}
                    onChange={(e) => setSiteSlug(e.target.value)}
                    data-testid="install-site-select"
                  >
                    {preflight.sites.map((s) => (
                      <option key={s.site_slug} value={s.site_slug}>
                        {s.site_name}
                      </option>
                    ))}
                  </select>
                </label>
              </section>
            ) : null}
            {currentStep === "Configuration" && preflight && Object.keys(preflight.configuration_schema).length > 0 ? (
              <section className="config-panel">
                <p className="muted">Configure module settings. Secret values show as configured/not configured only.</p>
                {Object.entries(preflight.configuration_schema).map(([key, def]) => {
                  const field = def as { title?: string; type?: string };
                  const isSecret = field.type === "secret" || key.toLowerCase().includes("secret");
                  return (
                    <label key={key} className="config-field">
                      {field.title ?? key}
                      {isSecret ? (
                        <span className="muted"> (use secret reference — not shown)</span>
                      ) : (
                        <input
                          className="config-input"
                          type={field.type === "number" ? "number" : "text"}
                          value={String(config[key] ?? "")}
                          onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                        />
                      )}
                    </label>
                  );
                })}
              </section>
            ) : currentStep === "Configuration" ? (
              <p className="muted">No configuration required.</p>
            ) : null}
            {currentStep === "Credential" ? (
              <section className="config-panel" data-testid="install-credential-step">
                <p className="muted">Enter your Sensibo API key. It is stored encrypted and never shown again.</p>
                <p>{credentialConfigured ? "Status: Configured" : "Status: Not configured"}</p>
                <label>
                  API key
                  <input
                    className="config-input"
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    data-testid="install-api-key"
                    placeholder={credentialConfigured ? "Leave blank to keep existing key" : "Required"}
                  />
                </label>
              </section>
            ) : null}
            {currentStep === "Connectivity" ? (
              <section className="config-panel" data-testid="install-connectivity-step">
                <p className="muted">Broker-backed connectivity test (no backend Sensibo shortcut).</p>
                {connectionMessage ? (
                  <p className={connectionOk ? "config-banner success" : "config-banner"}>{connectionMessage}</p>
                ) : (
                  <p className="muted">Press Next to run the connectivity test.</p>
                )}
              </section>
            ) : null}
            {currentStep === "Discovery" ? (
              <section className="config-panel" data-testid="install-discovery-step">
                <p className="muted">Discover Sensibo devices via the network broker.</p>
                {discovered.length ? (
                  <ul>
                    {discovered.map((d) => (
                      <li key={d.external_id}>
                        {d.name} ({d.external_id})
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">Press Next to discover devices.</p>
                )}
              </section>
            ) : null}
            {currentStep === "Devices" ? (
              <section className="config-panel" data-testid="install-devices-step">
                <p className="muted">Select devices to monitor (read-only).</p>
                {discovered.length ? (
                  discovered.map((device) => (
                    <label key={device.external_id} className="config-field">
                      <input
                        type="checkbox"
                        checked={selectedDevices.includes(device.external_id)}
                        onChange={(e) => {
                          setSelectedDevices((prev) =>
                            e.target.checked
                              ? [...prev, device.external_id]
                              : prev.filter((id) => id !== device.external_id),
                          );
                        }}
                      />
                      {device.name} ({device.external_id})
                    </label>
                  ))
                ) : (
                  <p className="muted">No devices discovered yet.</p>
                )}
              </section>
            ) : null}
            {currentStep === "Review" && preflight ? (
              <section className="config-panel">
                <p>Module: {preflight.display_name} v{version}</p>
                <p>Site: {siteSlug}</p>
                <p>Policy: {preflight.policy.decision}</p>
                <p>{preflight.policy.explanation}</p>
                {externalOnboard ? (
                  <>
                    <p>Credential: {credentialConfigured ? "Configured" : "Missing"}</p>
                    <p>Selected devices: {selectedDevices.length}</p>
                  </>
                ) : null}
                {preflight.runtime_blocked ? <p className="config-banner">{preflight.runtime_message}</p> : null}
              </section>
            ) : null}
            <div className="store-card-actions">
              {step > 0 ? (
                <button type="button" className="config-button" onClick={() => setStep((s) => s - 1)}>
                  Back
                </button>
              ) : (
                <Link href={`/config/modules-devices/store/${encodeURIComponent(moduleId)}`} className="config-button">
                  Cancel
                </Link>
              )}
              {step < steps.length - 1 ? (
                <button type="button" className="config-button primary" disabled={busy} onClick={() => void handleNext()}>
                  {busy ? "Working…" : "Next"}
                </button>
              ) : (
                <button
                  type="button"
                  className="config-button primary"
                  disabled={busy || !preflight?.install_allowed}
                  onClick={() => void runInstall()}
                  data-testid="install-confirm"
                >
                  {busy ? "Installing…" : primaryActionLabel(preflight?.primary_action ?? "INSTALL")}
                </button>
              )}
            </div>
          </>
        )}
      </ModuleStoreShell>
    </>
  );
}
