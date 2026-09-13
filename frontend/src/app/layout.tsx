import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { AppChrome } from "@/components/AppChrome";
import { ToastProvider } from "@/components/admin-ui";
import { AuthProvider } from "@/lib/authContext";
import { MobileShellProvider } from "@/lib/MobileShellProvider";
import { SiteSelectionProvider } from "@/lib/SiteSelectionProvider";
import { TenantSelectionProvider } from "@/lib/TenantSelectionProvider";
import { GlobalMobileShell } from "@/components/mobile/GlobalMobileShell";
import { EnergySceneConfigProvider } from "@/components/EnergySceneConfigProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import { APP_DESCRIPTION, APP_TITLE } from "@/lib/brand";
import "./globals.css";
import "@/styles/tokens.css";
import "@/styles/primitives.css";
import "@/styles/intelligence-dashboard.css";
import "@/styles/spa-dashboard.css";
import "@/styles/vehicle-dashboard.css";
import "@/styles/economy-dashboard.css";
import "@/styles/energy-dashboard.css";
import "@/styles/ev-dashboard.css";
import "@/styles/solar-dashboard.css";
import "@/styles/config-hub.css";
import "@/styles/admin-auth.css";
import "@/styles/multisite-overview.css";
import "@/styles/mobile-app.css";
import { PwaRegistration } from "@/components/pwa/PwaRegistration";

export const metadata: Metadata = {
  title: APP_TITLE,
  description: APP_DESCRIPTION,
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "EMIC",
  },
  icons: {
    icon: [
      { url: "/icons/favicon.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/emic-icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/emic-icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/icons/emic-icon-192.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

const themeInitScript = `(function(){try{var t=localStorage.getItem('emic-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`;

const adminSetupScript = `(function(){try{var params=new URLSearchParams(window.location.search);var setup=params.get('emic_setup_token');if(!setup){return;}localStorage.setItem('emic_admin_token',setup.trim());params.delete('emic_setup_token');var q=params.toString();var next=window.location.pathname+(q?'?'+q:'')+window.location.hash;window.history.replaceState({},'',next);}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="sv" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#070c16" />
        <Script id="emic-theme-init" strategy="beforeInteractive">
          {themeInitScript}
        </Script>
        <Script id="emic-admin-setup" strategy="beforeInteractive">
          {adminSetupScript}
        </Script>
      </head>
      <body>
        <ThemeProvider>
          <AuthProvider>
            <ToastProvider>
              <TenantSelectionProvider>
              <SiteSelectionProvider>
                <MobileShellProvider>
                  <PwaRegistration />
                  <AppChrome>
                    <GlobalMobileShell>
                      <EnergySceneConfigProvider>{children}</EnergySceneConfigProvider>
                    </GlobalMobileShell>
                  </AppChrome>
                </MobileShellProvider>
              </SiteSelectionProvider>
              </TenantSelectionProvider>
            </ToastProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
