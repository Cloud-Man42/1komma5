"use client";

import { AppleDevicesAdminPanel } from "@/components/AppleDevicesAdminPanel";
import { DisplayEnrollPanel } from "@/components/DisplayEnrollPanel";

export default function ConfigDisplaysPage() {
  return (
    <>
      <header className="config-page-header">
        <h2 className="config-page-title">Display &amp; enheter</h2>
        <p className="muted config-page-intro">
          Registrera Pi-väggdisplayer och hantera Apple/widget-enheter.
        </p>
      </header>
      <DisplayEnrollPanel />
      <AppleDevicesAdminPanel />
    </>
  );
}
