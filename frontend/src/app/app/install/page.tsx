"use client";



import { useEffect, useRef, useState } from "react";

import { APP_NAME } from "@/lib/brand";

import { useIsStandalonePwa } from "@/lib/useMobileShell";



export default function MobileInstallPage() {

  const standalone = useIsStandalonePwa();

  const [origin, setOrigin] = useState("");

  const [installReady, setInstallReady] = useState(false);

  const installPromptRef = useRef<(() => Promise<void>) | null>(null);



  useEffect(() => {

    setOrigin(window.location.origin);

    const onInstall = (event: Event) => {

      const detail = (event as CustomEvent<{ prompt: () => Promise<void> }>).detail;

      installPromptRef.current = detail.prompt;

      setInstallReady(true);

    };

    window.addEventListener("emic:pwa-install-available", onInstall);

    return () => window.removeEventListener("emic:pwa-install-available", onInstall);

  }, []);



  const installUrl = `${origin}/app`;

  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(installUrl)}`;



  return (

    <div className="mobile-hub mobile-install">

      <h1 className="mobile-hub-title">Install EMIC</h1>

      <p className="muted">{APP_NAME}</p>

      {standalone ? (

        <p className="mobile-install-ok">EMIC is running as an installed app.</p>

      ) : (

        <>

          {installReady ? (

            <button type="button" className="mobile-install-btn" onClick={() => void installPromptRef.current?.()}>

              Install EMIC now

            </button>

          ) : null}

          <p>Scan to open the app URL on your phone, then use Add to Home Screen.</p>

          <img src={qrUrl} alt="QR code for EMIC install URL" className="mobile-install-qr" width={220} height={220} />

          <p className="mobile-install-url">{installUrl}</p>

          <section className="mobile-install-ios">

            <h2>iOS (Safari)</h2>

            <ol>

              <li>
                On home WiFi, open{" "}
                <a href="http://emic.inacloud.se/emic-ca.html">http://emic.inacloud.se/emic-ca.html</a> once and
                install the HTTPS trust profile.
              </li>

              <li>Open {installUrl} in Safari and log in</li>

              <li>Tap Share → Add to Home Screen</li>

            </ol>

          </section>

          <section className="mobile-install-android">

            <h2>Android (Chrome)</h2>

            <ol>

              <li>Open {installUrl}</li>

              <li>Tap menu → Install app / Add to Home screen</li>

            </ol>

          </section>

        </>

      )}

    </div>

  );

}


