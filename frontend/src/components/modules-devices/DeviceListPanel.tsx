"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { fetchSiteOperations, type OperationsDeviceItem } from "@/lib/api";
import { healthStatusLabel } from "@/components/modules-devices/statusLabels";

export function DeviceListPanel() {
  const searchParams = useSearchParams();
  const siteSlug = searchParams.get("site") || "akarp";
  const [devices, setDevices] = useState<OperationsDeviceItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const ops = await fetchSiteOperations(siteSlug);
      setDevices(ops.devices);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda enheter");
    }
  }, [siteSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="config-panel" data-testid="device-list-panel">
      <h2 className="config-panel-title">Enheter ({siteSlug})</h2>
      {error ? <p className="config-error">{error}</p> : null}
      <div className="config-table-wrap">
        <table className="config-table">
          <thead>
            <tr>
              <th>Namn</th>
              <th>Typ</th>
              <th>Tillverkare</th>
              <th>Integration</th>
              <th>Hälsa</th>
              <th>Senast sedd</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr key={`${device.device_type}-${device.device_id}`}>
                <td>
                  <Link href={`/config/modules-devices/devices/${device.device_type}/${device.device_id}?site=${siteSlug}`}>
                    {device.name}
                  </Link>
                </td>
                <td>{device.device_type}</td>
                <td>{device.manufacturer}</td>
                <td>{device.integration ?? "—"}</td>
                <td>{healthStatusLabel(device.health_status)}</td>
                <td>{device.last_seen ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
