"use client";

import { APP_ACRONYM, APP_NAME } from "@/lib/brand";

export function LoginHero() {
  return (
    <aside className="login-hero" aria-hidden="true">
      <div className="login-hero-brand">
        <span className="brand-acronym">{APP_ACRONYM}</span>
        <span className="brand-name">{APP_NAME}</span>
      </div>
      <p className="muted">Energiövervakning och styrning i realtid.</p>
      <div className="login-hero-visual">
        <div className="login-energy-flow">
          <div className="login-energy-node">
            <span className="login-energy-dot solar" />
            <span>Solproduktion</span>
          </div>
          <div className="login-energy-node">
            <span className="login-energy-dot battery" />
            <span>Batterilager</span>
          </div>
          <div className="login-energy-node">
            <span className="login-energy-dot grid" />
            <span>Nätimport/export</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
