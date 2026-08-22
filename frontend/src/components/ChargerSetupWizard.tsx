"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChargerConnectionTestResult,
  ChargerIntegrationMethod,
  createEvCharger,
  fetchChargerModelDetail,
  testEvChargerConnectionDraft,
} from "@/lib/api";
import { ChargerCatalogFields, ChargerCatalogSelection, isSmartChargingAvailable } from "@/components/ChargerCatalogFields";

type Props = {
  siteSlug: string;
  onClose: () => void;
  onSaved: () => void;
};

export function ChargerSetupWizard({ siteSlug, onClose, onSaved }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [selection, setSelection] = useState<ChargerCatalogSelection>({
    manufacturerId: "",
    modelId: "",
    integrationMethod: "",
  });
  const [methods, setMethods] = useState<ChargerIntegrationMethod[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [connection, setConnection] = useState<Record<string, string>>({});
  const [testResult, setTestResult] = useState<ChargerConnectionTestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    panelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, []);

  useEffect(() => {
    if (!selection.manufacturerId || !selection.modelId) {
      setMethods([]);
      return;
    }
    fetchChargerModelDetail(selection.manufacturerId, selection.modelId)
      .then((detail) => {
        setMethods(detail.integration_methods);
        if (!displayName) {
          setDisplayName(detail.model.name);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda integrationsmetoder"));
  }, [selection.manufacturerId, selection.modelId, displayName]);

  const selectedMethod = useMemo(
    () => methods.find((method) => method.id === selection.integrationMethod) ?? null,
    [methods, selection.integrationMethod],
  );

  const buildPayload = () => {
    const chargerId = credentials.charger_id || connection.charger_id || credentials.external_charger_id;
    return {
      manufacturer_id: selection.manufacturerId,
      model_id: selection.modelId,
      integration_method: selection.integrationMethod,
      chargeamp_charger_id: selection.integrationMethod === "CHARGE_AMPS_CLOUD" ? chargerId ?? null : null,
      external_charger_id: chargerId ?? null,
      chargeamps_api_key: credentials.api_key ?? null,
      connection_settings: { ...connection, ...credentials },
    };
  };

  const smartChargingAvailable = isSmartChargingAvailable(selectedMethod);

  const handleTest = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await testEvChargerConnectionDraft(siteSlug, buildPayload());
      setTestResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Anslutningstest misslyckades");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = buildPayload();
      await createEvCharger(siteSlug, {
        name: displayName.trim() || "Laddbox",
        manufacturer_id: selection.manufacturerId,
        model_id: selection.modelId,
        integration_method: selection.integrationMethod,
        chargeamp_charger_id: payload.chargeamp_charger_id,
        external_charger_id: payload.external_charger_id,
        chargeamps_api_key: payload.chargeamps_api_key,
        connection_settings: payload.connection_settings,
        bridge_enabled: false,
      });
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte spara laddbox");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div ref={panelRef} className="charger-wizard" role="dialog" aria-labelledby="charger-wizard-title">
      <div className="charger-wizard-header">
        <h3 id="charger-wizard-title">Lägg till laddbox</h3>
        <p className="muted">Välj tillverkare, modell och integrationsmetod. Testa anslutningen innan du sparar.</p>
      </div>
      {error ? <p className="form-error">{error}</p> : null}

      <ChargerCatalogFields value={selection} onChange={setSelection} idPrefix="wizard" />

      {selectedMethod?.cloud_dependent ? (
        <p className="wizard-note">Molnberoende integration — kräver internetanslutning.</p>
      ) : null}
      {selectedMethod?.connection_type === "OCPP" ? (
        <p className="wizard-warning">
          Att ansluta laddboxen direkt till EMIC OCPP kan ersätta tillverkarens nuvarande OCPP-backend.
        </p>
      ) : null}

      {selectedMethod && !smartChargingAvailable ? (
        <p className="wizard-warning">
          Du kan testa och spara konfigurationen, men smartladdning aktiveras inte förrän integrationen
          är implementerad.
        </p>
      ) : null}

      <div className="form-grid">
        <label className="form-field">
          <span>Visningsnamn</span>
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </label>
      </div>

      {selectedMethod?.credential_fields.map((field) => {
        const key = String(field.key);
        const label = String(field.label);
        const fieldType = String(field.field_type ?? "text");
        return (
          <label key={key} className="form-field">
            <span>{label}</span>
            <input
              type={fieldType === "password" ? "password" : "text"}
              value={credentials[key] ?? ""}
              onChange={(e) => {
                setCredentials((current) => ({ ...current, [key]: e.target.value }));
                setTestResult(null);
              }}
            />
          </label>
        );
      })}

      {selectedMethod?.connection_fields.map((field) => {
        const key = String(field.key);
        const label = String(field.label);
        return (
          <label key={key} className="form-field">
            <span>{label}</span>
            <input
              value={connection[key] ?? ""}
              onChange={(e) => {
                setConnection((current) => ({ ...current, [key]: e.target.value }));
                setTestResult(null);
              }}
            />
          </label>
        );
      })}

      {testResult ? (
        <div className={testResult.success ? "wizard-success" : "wizard-error"}>
          <p>{testResult.message}</p>
          {testResult.detected_device?.serial_number ? (
            <p>Serial: {testResult.detected_device.serial_number}</p>
          ) : null}
          {testResult.model_mismatch ? (
            <p className="wizard-warning">Vald modell matchar inte upptäckt laddbox.</p>
          ) : null}
        </div>
      ) : null}

      <div className="wizard-actions">
        <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
          Avbryt
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={handleTest}
          disabled={loading || !selection.integrationMethod}
        >
          Testa anslutning
        </button>
        <button
          type="button"
          className="btn-primary"
          onClick={handleSave}
          disabled={loading || !selection.integrationMethod || !displayName.trim()}
        >
          Spara
        </button>
      </div>
    </div>
  );
}
