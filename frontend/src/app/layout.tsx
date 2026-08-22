import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { EnergySceneConfigProvider } from "@/components/EnergySceneConfigProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { APP_DESCRIPTION, APP_TITLE, APP_ACRONYM, APP_NAME } from "@/lib/brand";
import "./globals.css";
import "@/styles/tokens.css";
import "@/styles/primitives.css";

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
          <main className="container">
            <EnergySceneConfigProvider>{children}</EnergySceneConfigProvider>
          </main>
        </ThemeProvider>
      </body>
    </html>
  );
}
