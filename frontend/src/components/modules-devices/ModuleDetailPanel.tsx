"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  applyModuleConfiguration,
  fetchModuleConfig,
  fetchSiteModuleDetail,
  testModuleConnection,
  updateModuleConfig,
  type ConnectionTestResult,
  type ModuleConfigResponse,
  type SiteModuleRecord,
} from "@/lib/api";
import { StatusBadge } from "@/components/dashboard";
import { ConfigurationStatusBanner } from "@/components/modules-devices/ConfigurationStatusBanner";
import { EnableDisableControl } from "@/components/modules-devices/EnableDisableControl";
import { SchemaForm } from "@/components/modules-devices/SchemaForm";
import { ConnectionTestPanel } from "@/components/modules-devices/ConnectionTestPanel";
import { useRuntimePoller } from "@/components/modules-devices/useRuntimePoller";
import { healthStatusLabel, healthTone, runtimeStatusLabel, runtimeTone } from "@/components/modules-devices/statusLabels";

type Props = {
  siteSlug: string;
  moduleId: string;
};

export function ModuleDetailPanel({ siteSlug, moduleId }: Props) {
  const [module, setModule] = useState<SiteModuleRecord | null>(null);
  const [config, setConfig] = useState<ModuleConfigResponse | null>(null);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applyBusy, setApplyBusy] = useState(false);
  const [pollRuntime, setPollRuntime] = useState(false);
  const [tab, setTab] = useState<"overview" | "capabilities" | "config" | "diagnostics">("overview");

  const load = useCallback(async () => {
    setError(null);
    try {
      const [detail, configView] = await Promise.all([
        fetchSiteModuleDetail(siteSlug, moduleId),
        fetchModuleConfig(siteSlug, moduleId),
      ]);
      setModule(detail);
      setConfig(configView);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda modul");
    }
  }, [siteSlug, moduleId]);

  useRuntimePoller({
    enabled: pollRuntime,
    fetchState: async () => {
      const detail = await fetchSiteModuleDetail(siteSlug, moduleId);
      setModule(detail);
      return detail;
    },
    onUpdate: (detail) => setModule(detail),
  });

  useEffect(() => {
    void load();
  }, [load]);

  async function saveConfig(values: Record<string, unknown>) {
    const updated = await updateModuleConfig(siteSlug, moduleId, values);
    setConfig(updated);
    setApplyError(null);
  }

  async function runApply() {
    setApplyBusy(true);
    setApplyError(null);
    try {
      const result = await applyModuleConfiguration(siteSlug, moduleId);
      if (!result.success) {
        setApplyError(result.message);
        return;
      }
      setPollRuntime(true);
      const refreshed = await fetchModuleConfig(siteSlug, moduleId);
      setConfig(refreshed);
      await load();
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "Tillämpning misslyckades");
    } finally {
      setApplyBusy(false);
    }
  }

  async function runTest() {
    const result = await testModuleConnection(siteSlug, moduleId);
    setTestResult(result);
    setTab("diagnostics");
  }

  if (!module) {
    return error ? <p className="config-error">{error}</p> : <p className="muted">Laddar modul…</p>;
  }

  return (
    <div className="config-page" data-testid="module-detail-panel">
      <p className="config-banner">Anläggning: {siteSlug}</p>
      <header className="config-page-header">
        <div>
          <Link href={`/config/modules-devices?site=${siteSlug}`}>← Tillbaka</Link>
          <h1 className="config-page-title">{module.name}</h1>
          <p className="config-page-lead">{module.module_id} · v{module.version}</p>
        </div>
        <EnableDisableControl
          siteSlug={siteSlug}
          moduleId={module.module_id}
          enabled={module.enabled}
          canDisable={module.can_disable}
          onChanged={() => {
            setPollRuntime(true);
            void load();
          }}
        />
      </header>

      <div className="config-tabs">
        {(["overview", "capabilities", "config", "diagnostics"] as const).map((item) => (
          <button
            key={item}
            type="button"
            className={tab === item ? "config-tab active" : "config-tab"}
            onClick={() => setTab(item)}
          >
            {item === "overview"
              ? "Översikt"
              : item === "capabilities"
                ? "Kapacitet"
                : item === "config"
                  ? "Konfiguration"
                  : "Diagnostik"}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <section className="config-panel">
          <div className="config-stat-grid">
            <div className="config-stat-card">
              <span className="config-stat-label">Aktiverad</span>
              <strong>{module.enabled ? "Ja" : "Nej"}</strong>
            </div>
            <div className="config-stat-card">
              <span className="config-stat-label">Runtime</span>
              <StatusBadge label={runtimeStatusLabel(module.runtime_status)} tone={runtimeTone(module.runtime_status)} />
            </div>
            <div className="config-stat-card">
              <span className="config-stat-label">Hälsa</span>
              <StatusBadge label={healthStatusLabel(module.health_status)} tone={healthTone(module.health_status)} />
            </div>
            <div className="config-stat-card">
              <span className="config-stat-label">Typ</span>
              <strong>{module.module_type}</strong>
            </div>
          </div>
          {module.missing_required_capabilities.length ? (
            <p className="config-error-inline">
              Saknar: {module.missing_required_capabilities.join(", ")}
            </p>
          ) : null}
          {module.last_error ? <p className="config-error">{module.last_error}</p> : null}
          {module.package_source === "installed" ? (
            <div className="config-stat-grid" data-testid="module-package-metadata">
              <div className="config-stat-card">
                <span className="config-stat-label">Paketkälla</span>
                <strong>{module.package_source}</strong>
              </div>
              <div className="config-stat-card">
                <span className="config-stat-label">Installerad version</span>
                <strong>{module.installed_version ?? module.version}</strong>
              </div>
              {module.publisher ? (
                <div className="config-stat-card">
                  <span className="config-stat-label">Utgivare</span>
                  <strong>{module.publisher}</strong>
                </div>
              ) : null}
              {module.package_state ? (
                <div className="config-stat-card">
                  <span className="config-stat-label">Paketstatus</span>
                  <strong>{module.package_state}</strong>
                </div>
              ) : null}
              {module.rollback_available ? (
                <p className="muted">Rollback till tidigare version är tillgänglig (via API).</p>
              ) : null}
              <Link
                href={`/config/modules-devices/store/${encodeURIComponent(module.module_id)}`}
                className="config-button"
                data-testid="view-package-details"
              >
                Visa paketdetaljer
              </Link>
            </div>
          ) : null}
        </section>
      ) : null}

      {tab === "capabilities" ? (
        <section className="config-panel">
          <h3>Tillhandahåller</h3>
          <ul>{module.capabilities_provided.map((cap) => <li key={cap}>{cap}</li>)}</ul>
          <h3>Kräver</h3>
          <ul>{module.capabilities_required.map((cap) => <li key={cap}>{cap}</li>)}</ul>
          <h3>Valfritt</h3>
          <ul>{module.optional_capabilities.map((cap) => <li key={cap}>{cap}</li>)}</ul>
          {module.dependencies?.length ? (
            <>
              <h3>Modulberoenden</h3>
              <ul>{module.dependencies.map((dep) => <li key={dep}>{dep}</li>)}</ul>
            </>
          ) : null}
        </section>
      ) : null}

      {tab === "config" && config ? (
        <section className="config-panel">
          <ConfigurationStatusBanner
            restartRequired={config.restart_required}
            configurationActive={config.configuration_active}
            configurationStatus={config.configuration_status}
            effectivelyConfigured={config.effectively_configured}
            onApply={() => void runApply()}
            applyBusy={applyBusy}
            applyError={applyError}
          />
          {config.configuration_status === "heartbeat_credentials_missing" ? (
            <p className="config-banner config-banner-warning">
              Heartbeat-kontouppgifter saknas. Konfigurera under System innan onboarding anses klar.
            </p>
          ) : null}
          <SchemaForm
            schema={module.configuration_schema ?? { fields: [] }}
            values={config.config}
            configuredFields={config.configured_fields}
            onSubmit={saveConfig}
          />
          {module.onboardable ? (
            <button type="button" className="config-button-secondary" onClick={() => void runTest()}>
              Testa anslutning
            </button>
          ) : null}
        </section>
      ) : null}

      {tab === "diagnostics" ? (
        <section className="config-panel">
          <button type="button" className="config-button" onClick={() => void runTest()}>
            Kör anslutningstest
          </button>
          {testResult ? <ConnectionTestPanel result={testResult} /> : null}
        </section>
      ) : null}
    </div>
  );
}
