"use client";

import { FormEvent, useEffect, useState } from "react";

import { getAdminToken, setAdminToken } from "@/lib/adminAuth";

export function AdminTokenPanel() {
  const [token, setToken] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setToken(getAdminToken());
    const onAuthRequired = () => {
      setMessage("Admin-token krävs. Ange token från serverns .env och spara.");
    };
    window.addEventListener("emic:admin-auth-required", onAuthRequired);
    return () => window.removeEventListener("emic:admin-auth-required", onAuthRequired);
  }, []);

  function onSave(event: FormEvent) {
    event.preventDefault();
    setAdminToken(token);
    setMessage(token ? "Admin-token sparat för denna webbläsarsession." : "Admin-token borttaget.");
  }

  return (
    <div className="card config-card" data-testid="admin-token-panel">
      <h3 className="config-section-title">Admin-token</h3>
      <p className="muted config-env-intro">
        Krävs när servern har <code>EMIC_ADMIN_TOKEN</code> satt. Alla API-anrop (dashboard, fordon,
        konfiguration) skickar denna token. Sparas i localStorage i denna webbläsare.
      </p>
      <form className="form-grid" onSubmit={onSave}>
        <label className="form-field">
          <span>Bearer-token</span>
          <input
            type="password"
            value={token}
            aria-label="Admin-token"
            autoComplete="off"
            onChange={(event) => setToken(event.target.value)}
          />
        </label>
        <div className="form-actions">
          <button type="submit" className="btn-secondary">
            Spara admin-token
          </button>
        </div>
      </form>
      {message ? <p className="form-success">{message}</p> : null}
    </div>
  );
}
