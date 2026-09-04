"use client";

import Link from "next/link";
import { ConfigSidebar } from "./ConfigSidebar";

export function ConfigShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="config-hub" data-testid="config-shell">
      <header className="config-hub-header">
        <Link href="/" className="back-link">
          ← Dashboard
        </Link>
        <h1 className="config-hub-title">Konfiguration</h1>
        <p className="muted config-hub-intro">
          Strukturerad administration av system, anläggningar, display och integrationer.
        </p>
      </header>
      <div className="config-hub-body">
        <ConfigSidebar />
        <div className="config-hub-main">{children}</div>
      </div>
    </div>
  );
}
