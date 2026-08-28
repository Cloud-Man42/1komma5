import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { AppChrome } from "@/components/AppChrome";
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

export const metadata: Metadata = {
  title: APP_TITLE,
  description: APP_DESCRIPTION,
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

const themeInitScript = `(function(){try{var t=localStorage.getItem('emic-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="sv" suppressHydrationWarning>
      <head>
        <Script id="emic-theme-init" strategy="beforeInteractive">
          {themeInitScript}
        </Script>
      </head>
      <body>
        <ThemeProvider>
          <AppChrome>
            <EnergySceneConfigProvider>{children}</EnergySceneConfigProvider>
          </AppChrome>
        </ThemeProvider>
      </body>
    </html>
  );
}
