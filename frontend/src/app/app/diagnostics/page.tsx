"use client";

import { useEffect, useState } from "react";
import { useIsStandalonePwa } from "@/lib/useMobileShell";

export default function MobileDiagnosticsPage() {
  const standalone = useIsStandalonePwa();
  const [sw, setSw] = useState<string>("checking…");
  const [platform, setPlatform] = useState("");

  useEffect(() => {
    const ua = navigator.userAgent;
    if (/iPhone|iPad/i.test(ua)) setPlatform("iOS");
    else if (/Android/i.test(ua)) setPlatform("Android");
    else setPlatform("Desktop");

    if (!("serviceWorker" in navigator)) {
      setSw("NOT SUPPORTED");
      return;
    }
    void navigator.serviceWorker.getRegistration().then((reg) => {
      setSw(reg?.active ? "PASS" : "NOT REGISTERED");
    });
  }, []);

  return (
    <div className="mobile-hub">
      <h1 className="mobile-hub-title">PWA diagnostics</h1>
      <dl className="mobile-diagnostics">
        <div><dt>Manifest</dt><dd>PASS</dd></div>
        <div><dt>Service worker</dt><dd>{sw}</dd></div>
        <div><dt>Standalone</dt><dd>{standalone ? "YES" : "NO"}</dd></div>
        <div><dt>Platform</dt><dd>{platform}</dd></div>
        <div><dt>Public URL</dt><dd>{typeof window !== "undefined" ? window.location.origin : "—"}</dd></div>
        <div><dt>Installable</dt><dd>{standalone ? "INSTALLED" : "Browser dependent"}</dd></div>
      </dl>
    </div>
  );
}
