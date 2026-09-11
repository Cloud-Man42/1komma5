"use client";



import Link from "next/link";

import { useCallback, useEffect, useState } from "react";

import { fetchSiteDevice, type SiteDeviceDetail } from "@/lib/api";



type Props = {

  siteSlug: string;

  deviceType: string;

  deviceId: number;

};



export function DeviceDetailPanel({ siteSlug, deviceType, deviceId }: Props) {

  const [device, setDevice] = useState<SiteDeviceDetail | null>(null);

  const [error, setError] = useState<string | null>(null);



  const load = useCallback(async () => {

    try {

      const detail = await fetchSiteDevice(siteSlug, deviceType, deviceId);

      setDevice(detail);

    } catch (err) {

      setError(err instanceof Error ? err.message : "Kunde inte ladda enhet");

    }

  }, [siteSlug, deviceType, deviceId]);



  useEffect(() => {

    void load();

  }, [load]);



  if (error) return <p className="config-error">{error}</p>;

  if (!device) return <p className="muted">Laddar enhet…</p>;



  return (

    <div className="config-page" data-testid="device-detail-panel">

      <Link href={`/config/modules-devices/devices?site=${siteSlug}`}>← Enheter</Link>

      <h1 className="config-page-title">{device.name}</h1>

      <section className="config-panel">

        <dl className="config-dl">

          <dt>Typ</dt><dd>{device.device_type}</dd>

          <dt>Tillverkare</dt><dd>{device.manufacturer}</dd>

          <dt>Modell</dt><dd>{device.model}</dd>

          <dt>Integration</dt><dd>{device.integration ?? "—"}</dd>

          <dt>Anslutning</dt><dd>{device.connection_status ?? "—"}</dd>

          <dt>Hälsa</dt><dd>{device.health_status}</dd>

          <dt>Senast sedd</dt><dd>{device.last_seen ?? "—"}</dd>

          <dt>Konfiguration</dt><dd>{device.configuration_status}</dd>

          <dt>Aktiv</dt><dd>{device.enabled ? "Ja" : "Nej"}</dd>

        </dl>

        {!device.enabled ? (

          <p className="config-banner">Enheten är inaktiverad (soft-disable).</p>

        ) : null}

      </section>

    </div>

  );

}

