"use client";

import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { APP_ACRONYM, APP_NAME } from "@/lib/brand";

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isSiteDashboard = pathname.startsWith("/sites/");
  const isPiDisplay = pathname.startsWith("/display/");

  // The kiosk display owns the whole viewport and must not inherit app chrome.
  if (isPiDisplay) {
    return <>{children}</>;
  }

  if (isSiteDashboard) {
    return <div className="emic-app emic-app-dashboard">{children}</div>;
  }

  return (
    <div className="emic-app">
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
