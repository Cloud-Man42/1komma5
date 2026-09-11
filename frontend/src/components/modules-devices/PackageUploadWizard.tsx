"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  analyzePackageImpact,
  fetchPackageStoreDetail,
  installModulePackage,
  updateModulePackage,
  validateModulePackage,
  type PackageImpactResult,
  type PackageValidationResult,
} from "@/lib/api";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { PackageReviewPanel } from "@/components/modules-devices/PackageReviewPanel";

type Step = "select" | "validated" | "installing" | "installed" | "failed";

export function PackageUploadWizard() {
  const searchParams = useSearchParams();
  const updateModuleId = searchParams.get("update");
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<Step>("select");
  const [validation, setValidation] = useState<PackageValidationResult | null>(null);
  const [impact, setImpact] = useState<PackageImpactResult | null>(null);
  const [installedVersion, setInstalledVersion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const isUpdateMode = Boolean(updateModuleId);

  useEffect(() => {
    if (!updateModuleId) return;
    void fetchPackageStoreDetail(updateModuleId)
      .then((detail) => setInstalledVersion(detail.installed_version))
      .catch(() => setInstalledVersion(null));
  }, [updateModuleId]);

  async function runValidation(selected: File) {
    setFile(selected);
    setStep("select");
    setError(null);
    setMessage(null);
    try {
      const result = await validateModulePackage(selected);
      setValidation(result);
      const moduleId = updateModuleId ?? result.manifest?.module_id;
      if (moduleId) {
        const impactResult = await analyzePackageImpact(moduleId, selected);
        setImpact(impactResult);
      }
      setStep("validated");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validering misslyckades");
      setStep("failed");
    }
  }

  async function confirmInstall() {
    if (!file || !validation?.install_allowed) return;
    setStep("installing");
    setError(null);
    try {
      const result = isUpdateMode && updateModuleId
        ? await updateModulePackage(updateModuleId, file)
        : await installModulePackage(file);
      setMessage(result.message);
      setStep("installed");
    } catch (err) {
      setError(err instanceof Error ? err.message : isUpdateMode ? "Uppdatering misslyckades" : "Installation misslyckades");
      setStep("failed");
    }
  }

  return (
    <div className="config-page" data-testid="package-upload-wizard">
      <ModulesDevicesNav />
      <header className="config-page-header">
        <div>
          <Link href="/config/modules-devices/store">← Module Store</Link>
          <h1 className="config-page-title">{isUpdateMode ? "Uppdatera modulpaket" : "Ladda upp modulpaket"}</h1>
          <p className="config-page-lead">Validera först, granska trust/impact, {isUpdateMode ? "uppdatera" : "installera"} sedan via backend.</p>
        </div>
      </header>

      <section className="config-panel">
        <label className="config-field">
          <span>Välj .emicpkg</span>
          <input
            type="file"
            accept=".emicpkg,application/zip"
            onChange={(event) => {
              const selected = event.target.files?.[0];
              if (selected) void runValidation(selected);
            }}
          />
        </label>
        {step === "installing" ? <p className="muted">{isUpdateMode ? "Uppdaterar…" : "Installerar…"}</p> : null}
        {error ? <p className="config-error" role="alert">{error}</p> : null}
        {message ? <p className="config-banner">{message}</p> : null}
      </section>

      {validation ? (
        <>
          <PackageReviewPanel
            validation={validation}
            impact={impact}
            installedVersion={installedVersion}
            mode={isUpdateMode ? "update" : "install"}
          />
          <section className="config-panel">
            <button
              type="button"
              className="config-button"
              disabled={!validation.install_allowed || step === "installing"}
              onClick={() => void confirmInstall()}
            >
              {isUpdateMode ? "Uppdatera paket" : "Installera paket"}
            </button>
            {step === "installed" ? (
              <p className="config-banner">
                Modul {isUpdateMode ? "uppdaterad" : "installerad"}. Application restart required before the module becomes available.
              </p>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}
