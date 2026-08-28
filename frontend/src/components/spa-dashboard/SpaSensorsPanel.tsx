"use client";

import type { SpaHealth, SpaStatus } from "@/lib/api";
import { buildSensorRows } from "./spaDashboardHelpers";

const GROUP_LABELS = {
  bad: "Bad & styrning",
  effekt: "Effekt & komponenter",
  system: "System & mätning",
} as const;

export function SpaSensorsPanel({ status, health }: { status: SpaStatus; health: SpaHealth | null }) {
  const rows = buildSensorRows(status, health);
  const groups = (["bad", "effekt", "system"] as const).map((group) => ({
    group,
    label: GROUP_LABELS[group],
    rows: rows.filter((row) => row.group === group),
  }));

  return (
    <div className="sdash-sensors-panel" data-testid="spa-sensors-panel">
      {groups.map(({ group, label, rows: groupRows }) =>
        groupRows.length === 0 ? null : (
          <section key={group} className="sdash-sensors-group">
            <h3>{label}</h3>
            <dl className="sdash-sensors-grid">
              {groupRows.map((row) => (
                <div key={`${group}-${row.label}`} className="sdash-sensor-row">
                  <dt>{row.label}</dt>
                  <dd>{row.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        ),
      )}
      <p className="sdash-muted sdash-sensors-note">
        Vattenkvalitet och ozonator rapporteras inte av Eco Pak. UV visas som På under filter-/saneringscykler
        när cirkulation mäts.
      </p>
    </div>
  );
}
