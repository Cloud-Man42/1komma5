"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { AdminAuthPrompt } from "@/components/AdminAuthPrompt";
import { ThemeToggle } from "@/components/ThemeToggle";
import { APP_ACRONYM, APP_NAME } from "@/lib/brand";
import { getAdminToken } from "@/lib/adminAuth";

async function probeAdminAuthRequired(): Promise<boolean> {
  if (getAdminToken()) return false;
  try {
    const res = await fetch("/api/sites", { cache: "no-store" });
    return res.status === 401;
  } catch {
    return false;
  }
}

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isSiteDashboard = pathname.startsWith("/sites/");
  const isPiDisplay = pathname.startsWith("/display/");
  const isConfigHub = pathname.startsWith("/config");
  const [authRequired, setAuthRequired] = useState(false);

  useEffect(() => {
    if (isPiDisplay) return;

    const onAuthRequired = () => setAuthRequired(true);
    window.addEventListener("emic:admin-auth-required", onAuthRequired);

    let active = true;
    probeAdminAuthRequired().then((required) => {
      if (active && required) setAuthRequired(true);
    });

    return () => {
      active = false;
      window.removeEventListener("emic:admin-auth-required", onAuthRequired);
    };
  }, [isPiDisplay, pathname]);

  // The kiosk display owns the whole viewport and must not inherit app chrome.
  if (isPiDisplay) {
    return <>{children}</>;
  }

  const authOverlay = authRequired && !getAdminToken() ? <AdminAuthPrompt /> : null;

  if (isSiteDashboard || isConfigHub) {
    return (
      <div className="emic-app emic-app-dashboard">
        {authOverlay}
        {children}
      </div>
    );
  }

  return (
    <div className="emic-app">
      {authOverlay}
      <header className="header">
        <div className="header-inner">
          <h1 className="brand">
            <span className="brand-acronym">{APP_ACRONYM}</span>
            <span className="brand-full">{APP_NAME}</span>
          </h1>
          <nav className="header-nav">
            <a href="/">Dashboard</a>
            <a href="/config">Konfiguration</a>
            <a href="/calibrate">Kalibrera</a>
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="container">{children}</main>
    </div>
  );
}
