"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChargerCatalogModel,
  ChargerIntegrationMethod,
  ChargerManufacturer,
  fetchChargerModelDetail,
  fetchChargerModels,
  fetchChargerManufacturers,
} from "@/lib/api";

const SUPPORT_LABELS: Record<string, string> = {
  FULL: "Full",
  PARTIAL: "Delvis",
  EXPERIMENTAL: "Experimentell",
  MONITORING_ONLY: "Endast övervakning",
  UNSUPPORTED: "Ej implementerad",
};

const IMPLEMENTATION_LABELS: Record<string, string> = {
  FULL: "Implementerad",
  PARTIAL: "Delvis implementerad",
  EXPERIMENTAL: "Experimentell",
  MONITORING_ONLY: "Endast övervakning",
  UNSUPPORTED: "Ej implementerad",
};

export function isSmartChargingAvailable(method: ChargerIntegrationMethod | null | undefined): boolean {
  return method?.implementation_status === "FULL";
}

export type ChargerCatalogSelection = {
  manufacturerId: string;
  modelId: string;
  integrationMethod: string;
};

type Props = {
  value: ChargerCatalogSelection;
  onChange: (next: ChargerCatalogSelection) => void;
  disabled?: boolean;
  showSupportMeta?: boolean;
  idPrefix?: string;
  onSelectedMethodChange?: (method: ChargerIntegrationMethod | null) => void;
};

export function legacyCatalogSelection(charger: {
  manufacturer?: string;
  model?: string;
  manufacturer_id?: string | null;
  model_id?: string | null;
  integration_method?: string | null;
}): ChargerCatalogSelection {
  const manufacturerNorm = (charger.manufacturer ?? "").trim().toLowerCase();
  const modelNorm = (charger.model ?? "").trim().toLowerCase().replace(/\s+/g, "-");
  return {
    manufacturerId:
      charger.manufacturer_id ??
      (manufacturerNorm.includes("charge") ? "charge-amps" : manufacturerNorm.replace(/\s+/g, "-")),
    modelId: charger.model_id ?? (modelNorm === "halo" ? "halo" : modelNorm || "halo"),
    integrationMethod: charger.integration_method ?? "CHARGE_AMPS_CLOUD",
  };
}

export function ChargerCatalogFields({
  value,
  onChange,
  disabled = false,
  showSupportMeta = true,
  idPrefix = "charger",
  onSelectedMethodChange,
}: Props) {
  const [manufacturers, setManufacturers] = useState<ChargerManufacturer[]>([]);
  const [models, setModels] = useState<ChargerCatalogModel[]>([]);
  const [methods, setMethods] = useState<ChargerIntegrationMethod[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetchChargerManufacturers()
      .then(setManufacturers)
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Kunde inte ladda tillverkare"));
  }, []);

  useEffect(() => {
    if (!value.manufacturerId) {
      setModels([]);
      return;
    }
    fetchChargerModels(value.manufacturerId)
      .then(setModels)
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Kunde inte ladda modeller"));
  }, [value.manufacturerId]);

  useEffect(() => {
    if (!value.manufacturerId || !value.modelId) {
      setMethods([]);
      return;
    }
    fetchChargerModelDetail(value.manufacturerId, value.modelId)
      .then((detail) => {
        setMethods(detail.integration_methods);
        if (!value.integrationMethod && detail.integration_methods.length > 0) {
          const recommended = detail.integration_methods.find((m) => m.recommended);
          onChange({
            ...value,
            integrationMethod: recommended?.id ?? detail.integration_methods[0]?.id ?? "",
          });
        }
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Kunde inte ladda integrationsmetoder"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value.manufacturerId, value.modelId]);

  const selectedModel = useMemo(
    () => models.find((model) => model.id === value.modelId) ?? null,
    [models, value.modelId],
  );

  const selectedMethod = useMemo(
    () => methods.find((method) => method.id === value.integrationMethod) ?? null,
    [methods, value.integrationMethod],
  );

  const onSelectedMethodChangeRef = useRef(onSelectedMethodChange);
  onSelectedMethodChangeRef.current = onSelectedMethodChange;

  useEffect(() => {
    onSelectedMethodChangeRef.current?.(selectedMethod);
  }, [selectedMethod]);

  return (
    <div className="charger-catalog-fields form-grid">
      {loadError ? <p className="form-error form-field-wide">{loadError}</p> : null}

      <label className="form-field" htmlFor={`${idPrefix}-manufacturer`}>
        <span>Tillverkare</span>
        <select
          id={`${idPrefix}-manufacturer`}
          value={value.manufacturerId}
          disabled={disabled || manufacturers.length === 0}
          onChange={(e) =>
            onChange({
              manufacturerId: e.target.value,
              modelId: "",
              integrationMethod: "",
            })
          }
        >
          <option value="">Välj tillverkare…</option>
          {manufacturers.map((manufacturer) => (
            <option key={manufacturer.id} value={manufacturer.id}>
              {manufacturer.name}
            </option>
          ))}
        </select>
      </label>

      <label className="form-field" htmlFor={`${idPrefix}-model`}>
        <span>Modell</span>
        <select
          id={`${idPrefix}-model`}
          value={value.modelId}
          disabled={disabled || !value.manufacturerId}
          onChange={(e) =>
            onChange({
              ...value,
              modelId: e.target.value,
              integrationMethod: "",
            })
          }
        >
          <option value="">Välj modell…</option>
          {models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name} ({SUPPORT_LABELS[model.status] ?? model.status})
            </option>
          ))}
        </select>
      </label>

      <label className="form-field" htmlFor={`${idPrefix}-integration`}>
        <span>Integrationsmetod</span>
        <select
          id={`${idPrefix}-integration`}
          value={value.integrationMethod}
          disabled={disabled || !value.modelId}
          onChange={(e) => onChange({ ...value, integrationMethod: e.target.value })}
        >
          <option value="">Välj metod…</option>
          {methods.map((method) => (
            <option key={method.id} value={method.id}>
              {method.label} ({method.connection_type}) —{" "}
              {IMPLEMENTATION_LABELS[method.implementation_status] ?? method.implementation_status}
            </option>
          ))}
        </select>
      </label>

      {showSupportMeta && (selectedModel || selectedMethod) ? (
        <div className="wizard-meta form-field-wide">
          {selectedModel ? (
            <p>
              Modellstöd: <strong>{SUPPORT_LABELS[selectedModel.status] ?? selectedModel.status}</strong>
              {selectedMethod ? (
                <>
                  {" "}
                  · Integration:{" "}
                  <strong>
                    {IMPLEMENTATION_LABELS[selectedMethod.implementation_status] ??
                      selectedMethod.implementation_status}
                  </strong>
                </>
              ) : null}
            </p>
          ) : selectedMethod ? (
            <p>
              Integration:{" "}
              <strong>
                {IMPLEMENTATION_LABELS[selectedMethod.implementation_status] ??
                  selectedMethod.implementation_status}
              </strong>
            </p>
          ) : null}
          {selectedMethod && isSmartChargingAvailable(selectedMethod) ? (
            <p className="wizard-success">
              Smartladdning och styrning är tillgängliga med {selectedMethod.label}.
            </p>
          ) : selectedMethod ? (
            <p className="wizard-warning">
              Integrationen {selectedMethod.label} är ännu inte implementerad i EMIC. Smartladdning
              och styrning är inte tillgängliga förrän adapter finns.
            </p>
          ) : selectedModel?.status === "UNSUPPORTED" ? (
            <p className="wizard-warning">
              Denna modell saknar implementerad integration i EMIC. Välj Charge Amps Halo med Charge
              Amps Cloud API för smartladdning idag.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
