"use client";

import { FormEvent, useEffect, useState } from "react";

import { getAdminToken, setAdminToken } from "@/lib/adminAuth";

type AdminAuthPromptProps = {
  issue?: "required" | "invalid";
  onDismiss?: () => void;
};

export function AdminAuthPrompt({ issue = "required", onDismiss }: AdminAuthPromptProps) {
  const [token, setToken] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setToken(getAdminToken());
  }, []);

  function onSave(event: FormEvent) {
    event.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) {
      setMessage("Ange admin-token från serverns .env (EMIC_ADMIN_TOKEN).");
      return;
    }
    setAdminToken(trimmed);
    window.location.reload();
  }

  return (
    <div className="admin-auth-overlay" role="dialog" aria-labelledby="admin-auth-title">
      <div className="admin-auth-dialog card">
        <h2 id="admin-auth-title" className="config-section-title">
          {issue === "invalid" ? "Admin-token ogiltig" : "Admin-token krävs"}
        </h2>
        <p className="muted config-env-intro">
          {issue === "invalid" ? (
            <>
              Sparad token matchar inte serverns <code>EMIC_ADMIN_TOKEN</code>. Hämta aktuellt värde
              från <code>~/energy-monitoring/.env</code> och spara igen.
            </>
          ) : (
            <>
              Dashboard och API kräver Bearer-token när <code>EMIC_ADMIN_TOKEN</code> är satt på servern.
              Hämta värdet från <code>~/energy-monitoring/.env</code> på servern.
            </>
          )}
        </p>
        <form className="form-grid" onSubmit={onSave}>
          <label className="form-field">
            <span>Bearer-token</span>
            <input
              type="password"
              value={token}
              aria-label="Admin-token"
              autoComplete="off"
              autoFocus
              onChange={(event) => setToken(event.target.value)}
            />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn-primary">
              Spara och ladda om
            </button>
            {onDismiss ? (
              <button type="button" className="btn-secondary" onClick={onDismiss}>
                Stäng
              </button>
            ) : null}
          </div>
        </form>
        {message ? <p className="form-error">{message}</p> : null}
        <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.875rem" }}>
          Du kan också spara token under <a href="/config">Konfiguration</a>.
        </p>
      </div>
    </div>
  );
}
