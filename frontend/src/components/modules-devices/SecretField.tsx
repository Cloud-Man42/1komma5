"use client";

import { useState } from "react";

type Props = {
  name: string;
  configured: boolean;
  onChange: (value: string) => void;
};

export function SecretField({ configured, onChange }: Props) {
  const [replacing, setReplacing] = useState(!configured);

  if (configured && !replacing) {
    return (
      <div className="config-secret-field">
        <span className="muted">Konfigurerad (maskerad)</span>
        <button type="button" className="config-button-secondary" onClick={() => setReplacing(true)}>
          Ersätt
        </button>
      </div>
    );
  }

  return (
    <input
      type="password"
      autoComplete="off"
      placeholder={configured ? "Nytt värde" : "Ange hemligt värde"}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
