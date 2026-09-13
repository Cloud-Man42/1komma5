"use client";

import { HomeDashboardButton } from "@/components/HomeDashboardButton";
import { UserMenu } from "@/components/UserMenu";
import { useAuth } from "@/lib/authContext";
import { ConfigSidebar } from "./ConfigSidebar";

export function ConfigShell({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const userAuthEnabled = process.env.NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED === "true";

  return (
    <div className="config-hub" data-testid="config-shell">
      <header className="config-hub-header">
        <div className="config-hub-header-top">
          <div className="config-hub-home-row">
            <HomeDashboardButton />
            <span className="back-link">Dashboard</span>
          </div>
          {userAuthEnabled && !authLoading && user ? <UserMenu compact /> : null}
        </div>
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
