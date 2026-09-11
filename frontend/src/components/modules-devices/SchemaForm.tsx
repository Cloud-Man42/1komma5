"use client";

import { useState } from "react";
import type { ConfigSchemaField } from "@/lib/api";
import { SecretField } from "@/components/modules-devices/SecretField";

type FieldDef = {
  name: string;
  label: string;
  type: string;
  required?: boolean;
  secret?: boolean;
  help?: string;
  default?: unknown;
  options?: string[];
};

type Props = {
  schema: { fields?: FieldDef[] };
  values: Record<string, unknown>;
  configuredFields: Record<string, boolean>;
  onSubmit: (values: Record<string, unknown>) => Promise<void>;
};

export function SchemaForm({ schema, values, configuredFields, onSubmit }: Props) {
  const [draft, setDraft] = useState<Record<string, unknown>>({ ...values });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fields = schema.fields ?? [];

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(draft);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="config-form" onSubmit={(event) => void handleSubmit(event)} data-testid="schema-form">
      {fields.map((field: ConfigSchemaField | FieldDef) => (
        <label key={field.name} className="config-field">
          <span>{field.label}{field.required ? " *" : ""}</span>
          {field.secret ? (
            <SecretField
              name={field.name}
              configured={configuredFields[field.name] ?? false}
              onChange={(value) => setDraft((current) => ({ ...current, [field.name]: value }))}
            />
          ) : field.type === "boolean" ? (
            <input
              type="checkbox"
              checked={Boolean(draft[field.name])}
              onChange={(event) => setDraft((current) => ({ ...current, [field.name]: event.target.checked }))}
            />
          ) : field.options?.length ? (
            <select
              value={String(draft[field.name] ?? "")}
              onChange={(event) => setDraft((current) => ({ ...current, [field.name]: event.target.value }))}
            >
              <option value="">Välj…</option>
              {field.options.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          ) : (
            <input
              type={field.type === "integer" ? "number" : "text"}
              value={String(draft[field.name] ?? "")}
              onChange={(event) => setDraft((current) => ({ ...current, [field.name]: event.target.value }))}
            />
          )}
          {field.help ? <small className="muted">{field.help}</small> : null}
        </label>
      ))}
      {error ? <p className="config-error">{error}</p> : null}
      <button type="submit" className="config-button" disabled={busy}>
        Spara konfiguration
      </button>
    </form>
  );
}
