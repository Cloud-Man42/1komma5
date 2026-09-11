"use client";

import Link from "next/link";
import { StatusBadge } from "@/components/dashboard";
import type { OperationsModuleItem } from "@/lib/api";
import { EnableDisableControl } from "@/components/modules-devices/EnableDisableControl";
import { healthStatusLabel, healthTone, runtimeStatusLabel, runtimeTone } from "@/components/modules-devices/statusLabels";

type Props = {
  siteSlug: string;
  modules: OperationsModuleItem[];
  moduleNames?: Record<string, string>;
  onChanged: () => void;
};

export function ModuleTable({ siteSlug, modules, moduleNames, onChanged }: Props) {
  return (
    <section className="config-panel" data-testid="module-table">
      <div className="config-panel-header">
        <h2 className="config-panel-title">Moduler</h2>
        <Link href={`/config/modules-devices/modules?site=${siteSlug}`}>Visa alla</Link>
      </div>
      <div className="config-table-wrap">
        <table className="config-table">
          <thead>
            <tr>
              <th>Modul</th>
              <th>Aktiverad</th>
              <th>Runtime</th>
              <th>Hälsa</th>
              <th>Enheter</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {modules.map((module) => (
              <tr key={module.module_id} data-testid={`module-row-${module.module_id}`}>
                <td>
                  <Link href={`/config/modules-devices/modules/${encodeURIComponent(module.module_id)}?site=${siteSlug}`}>
                    <strong>{module.name}</strong>
                  </Link>
                  <div className="muted">{module.module_id}</div>
                  {module.last_error ? <div className="config-error-inline">{module.last_error}</div> : null}
                </td>
                <td>{module.enabled ? "Ja" : "Nej"}</td>
                <td>
                  <StatusBadge label={runtimeStatusLabel(module.runtime_status)} tone={runtimeTone(module.runtime_status)} />
                </td>
                <td>
                  <StatusBadge label={healthStatusLabel(module.health_status)} tone={healthTone(module.health_status)} />
                </td>
                <td>{module.device_count}</td>
                <td>
                  <EnableDisableControl
                    siteSlug={siteSlug}
                    moduleId={module.module_id}
                    enabled={module.enabled}
                    canDisable={module.can_disable}
                    moduleNames={moduleNames}
                    onChanged={onChanged}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
