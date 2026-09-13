"use client";

import { useState } from "react";
import { FormField, TextInput } from "./FormField";

export function PasswordField({
  label,
  value,
  onChange,
  autoComplete,
  error,
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  error?: string | null;
  required?: boolean;
}) {
  const [visible, setVisible] = useState(false);

  return (
    <FormField label={label} error={error}>
      <div className="admin-password-field">
        <TextInput
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          required={required}
        />
        <button
          type="button"
          className="admin-btn admin-btn-ghost admin-password-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-pressed={visible}
        >
          {visible ? "Dölj" : "Visa"}
        </button>
      </div>
    </FormField>
  );
}
