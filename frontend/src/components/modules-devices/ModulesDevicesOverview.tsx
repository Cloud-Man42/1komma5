"use client";



import Link from "next/link";

import { useCallback, useEffect, useMemo, useState } from "react";

import {

  fetchSiteOperations,

  fetchSites,

  type SiteOperationsResponse,

} from "@/lib/api";

import { ClimateStatusPanel } from "@/components/climate-dashboard/ClimateStatusPanel";
import { ModuleTable } from "@/components/modules-devices/ModuleTable";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { runtimeStatusLabel } from "@/components/modules-devices/statusLabels";



export function ModulesDevicesOverview() {

  const [siteSlug, setSiteSlug] = useState("akarp");

  const [sitesLoaded, setSitesLoaded] = useState(false);

  const [siteOptions, setSiteOptions] = useState<Array<{ slug: string; label: string }>>([]);

  const [operations, setOperations] = useState<SiteOperationsResponse | null>(null);

  const [error, setError] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);



  useEffect(() => {

    if (typeof window === "undefined") return;

    const params = new URLSearchParams(window.location.search);

    const fromQuery = params.get("site");

    if (fromQuery) setSiteSlug(fromQuery);

  }, []);



  useEffect(() => {

    fetchSites()

      .then((sites) => {

        setSiteOptions(sites.map((site) => ({ slug: site.slug, label: site.name })));

        setSitesLoaded(true);

      })

      .catch(() => setSitesLoaded(true));

  }, []);



  const load = useCallback(async () => {

    setLoading(true);

    setError(null);

    try {

      const data = await fetchSiteOperations(siteSlug);

      setOperations(data);

    } catch (err) {

      setError(err instanceof Error ? err.message : "Kunde inte ladda driftstatus");

    } finally {

      setLoading(false);

    }

  }, [siteSlug]);



  useEffect(() => {

    if (sitesLoaded) void load();

  }, [load, sitesLoaded]);



  const moduleNames = useMemo(

    () => Object.fromEntries((operations?.modules ?? []).map((m) => [m.module_id, m.name])),

    [operations],

  );



  const summary = useMemo(() => {

    if (!operations) return null;

    const enabled = operations.modules.filter((m) => m.enabled).length;

    const running = operations.modules.filter((m) => m.runtime_status === "running").length;

    return { enabled, running, devices: operations.devices.length };

  }, [operations]);



  function changeSite(nextSlug: string) {

    setSiteSlug(nextSlug);

    const next = new URLSearchParams(window.location.search);

    next.set("site", nextSlug);

    window.history.replaceState(null, "", `?${next.toString()}`);

  }



  return (

    <div className="config-page" data-testid="modules-devices-overview">

      <ModulesDevicesNav />

      <header className="config-page-header">

        <div>

          <h1 className="config-page-title">Moduler &amp; enheter</h1>

          <p className="config-page-lead">

            Hantera moduler, enheter och onboarding för {siteSlug}.

          </p>

        </div>

        <div className="config-toolbar">

          <label className="config-field-inline">

            <span>Anläggning</span>

            <select value={siteSlug} onChange={(event) => changeSite(event.target.value)}>

              {siteOptions.map((site) => (

                <option key={site.slug} value={site.slug}>

                  {site.label}

                </option>

              ))}

            </select>

          </label>

          <Link href={`/config/modules-devices/add?site=${siteSlug}`} className="config-button">

            Lägg till enhet

          </Link>

        </div>

      </header>



      {error ? <p className="config-error" role="alert">{error}</p> : null}

      {loading ? <p className="muted">Laddar…</p> : null}



      {summary ? (

        <div className="config-stat-grid">

          <div className="config-stat-card">

            <span className="config-stat-label">Aktiva moduler</span>

            <strong>{summary.enabled}</strong>

          </div>

          <div className="config-stat-card">

            <span className="config-stat-label">Körs</span>

            <strong>{summary.running}</strong>

          </div>

          <div className="config-stat-card">

            <span className="config-stat-label">Enheter</span>

            <strong>{summary.devices}</strong>

          </div>

          <div className="config-stat-card">

            <span className="config-stat-label">Hälsa</span>

            <strong>{operations?.overall_health_status ?? "—"}</strong>

          </div>

        </div>

      ) : null}



      {operations ? (

        <>

          <ModuleTable

            siteSlug={siteSlug}

            modules={operations.modules}

            moduleNames={moduleNames}

            onChanged={load}

          />

          <section className="config-panel">

            <div className="config-panel-header">

              <h2 className="config-panel-title">Enheter</h2>

              <Link href={`/config/modules-devices/devices?site=${siteSlug}`}>Visa alla</Link>

            </div>

            <div className="config-table-wrap">

              <table className="config-table">

                <thead>

                  <tr>

                    <th>Namn</th>

                    <th>Typ</th>

                    <th>Integration</th>

                    <th>Hälsa</th>

                  </tr>

                </thead>

                <tbody>

                  {operations.devices.slice(0, 8).map((device) => (

                    <tr key={`${device.device_type}-${device.device_id}`}>

                      <td>

                        <Link href={`/config/modules-devices/devices/${device.device_type}/${device.device_id}?site=${siteSlug}`}>

                          {device.name}

                        </Link>

                      </td>

                      <td>{device.device_type}</td>

                      <td>{device.integration ?? "—"}</td>

                      <td>{device.health_status}</td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          </section>

        </>

      ) : null}



      {operations ? (

        <p className="muted">

          Runtime: {operations.modules.slice(0, 3).map((m) => `${m.name}: ${runtimeStatusLabel(m.runtime_status)}`).join(" · ")}

        </p>

      ) : null}

      {siteSlug ? (

        <section className="config-panel">

          <h2 className="config-panel-title">Climate (read-only)</h2>

          <ClimateStatusPanel siteSlug={siteSlug} />

        </section>

      ) : null}

    </div>

  );

}

