"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchSiteModules, type SiteModuleRecord, updateSiteModule } from "@/lib/api";

type Props = {
  siteSlug: string;
};

export function SiteModulesPanel({ siteSlug }: Props) {
  const [modules, setModules] = useState<SiteModuleRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchSiteModules(siteSlug);
      setModules(response.modules);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda moduler");
    } finally {
      setLoading(false);
    }
  }, [siteSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleModule(module: SiteModuleRecord) {
    try {
      const updated = await updateSiteModule(siteSlug, module.module_id, !module.enabled);
      setModules((current) =>
        current.map((item) => (item.module_id === updated.module_id ? updated : item)),
      );
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte uppdatera modul");
    }
  }

  if (loading) {
    return <p className="muted">Laddar moduler…</p>;
  }

  return (
    <section className="config-panel" data-testid="site-modules-panel">
      <h3 className="config-panel-title">Moduler ({siteSlug})</h3>
      {error ? <p className="config-error" role="alert">{error}</p> : null}
      <div className="config-table-wrap">
        <table className="config-table">
          <thead>
            <tr>
              <th>Modul</th>
              <th>Typ</th>
              <th>Aktiv</th>
              <th>Runtime</th>
              <th>Hälsa</th>
              <th>Saknas</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {modules.map((module) => (
              <tr key={module.module_id} data-testid={`module-row-${module.module_id}`}>
                <td>
                  <strong>{module.name}</strong>
                  <div className="muted">{module.module_id}</div>
                </td>
                <td>{module.module_type}</td>
                <td>{module.enabled ? "Ja" : "Nej"}</td>
                <td>{module.runtime_status}</td>
                <td>{module.health_status}</td>
                <td>{module.missing_required_capabilities.join(", ") || "—"}</td>
                <td>
                  <button
                    type="button"
                    className="config-button-secondary"
                    onClick={() => void toggleModule(module)}
                  >
                    {module.enabled ? "Inaktivera" : "Aktivera"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
