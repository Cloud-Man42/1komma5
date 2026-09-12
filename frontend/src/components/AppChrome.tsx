"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { AdminAuthPrompt } from "@/components/AdminAuthPrompt";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserMenu } from "@/components/UserMenu";
import { useAuth } from "@/lib/authContext";
import { APP_ACRONYM, APP_NAME } from "@/lib/brand";
import { adminAuthHeaders, applySetupTokenFromUrl } from "@/lib/adminAuth";

type AdminAuthIssue = "required" | "invalid";

async function probeAdminAuthIssue(): Promise<AdminAuthIssue | null> {
  try {
    const res = await fetch("/api/sites", {
      cache: "no-store",
      headers: adminAuthHeaders(),
    });
    if (res.status === 401) return "required";
    if (res.status === 403) return "invalid";
    return null;
  } catch {
    return null;
  }
}

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isSiteDashboard = pathname.startsWith("/sites/");
  const isPiDisplay = pathname.startsWith("/display/");
  const isConfigHub = pathname.startsWith("/config");
  const isLogin = pathname.startsWith("/login");
  const isAdminHub = pathname.startsWith("/admin/users") || pathname.startsWith("/admin/roles") || pathname.startsWith("/admin/audit");
  const isOverview = pathname.startsWith("/overview");
  const [authIssue, setAuthIssue] = useState<AdminAuthIssue | null>(null);
  const { user, loading: authLoading } = useAuth();
  const userAuthEnabled = process.env.NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED === "true";

  useEffect(() => {
    if (isPiDisplay) return;
    if (userAuthEnabled) return;

    if (applySetupTokenFromUrl()) {
      window.location.reload();
      return;
    }

    const onAuthRequired = () => setAuthIssue("required");
    const onAuthInvalid = () => setAuthIssue("invalid");
    window.addEventListener("emic:admin-auth-required", onAuthRequired);
    window.addEventListener("emic:admin-auth-invalid", onAuthInvalid);

    let active = true;
    probeAdminAuthIssue().then((issue) => {
      if (active && issue) setAuthIssue(issue);
    });

    return () => {
      active = false;
      window.removeEventListener("emic:admin-auth-required", onAuthRequired);
      window.removeEventListener("emic:admin-auth-invalid", onAuthInvalid);
    };
  }, [isPiDisplay, pathname, userAuthEnabled]);

  useEffect(() => {
    if (!userAuthEnabled) return;
    const onRequired = () => {
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    };
    window.addEventListener("emic:auth-required", onRequired);
    return () => window.removeEventListener("emic:auth-required", onRequired);
  }, [userAuthEnabled]);

  // The kiosk display owns the whole viewport and must not inherit app chrome.
  if (isPiDisplay) {
    return <>{children}</>;
  }

  const authOverlay = authIssue ? <AdminAuthPrompt issue={authIssue} /> : null;

  if (isLogin) {
    return <>{children}</>;
  }

  if (isSiteDashboard || isConfigHub || isAdminHub || isOverview) {
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
            {(!userAuthEnabled || !user || user.roles.includes("SUPER_ADMIN") || user.permissions.includes("*") || user.permissions.some((p) => p.startsWith("sites.") || p.startsWith("integration.") || p.startsWith("system."))) ? (
              <a href="/config">Konfiguration</a>
            ) : null}
            <a href="/calibrate">Kalibrera</a>
            <ThemeToggle />
            {!authLoading && user ? <UserMenu /> : null}
          </nav>
        </div>
      </header>
      <main className="container">{children}</main>
    </div>
  );
}
