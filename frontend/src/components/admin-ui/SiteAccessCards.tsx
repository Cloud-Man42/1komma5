"use client";

import type { SiteOption } from "@/lib/adminUsersApi";

const SITE_LABELS: Record<string, string> = {
  akarp: "Åkarp",
  "summer-house-denmark": "Bøsserup (Danmark)",
};

export function SiteAccessCards({
  sites,
  selectedIds,
  onChange,
  readOnly = false,
}: {
  sites: SiteOption[];
  selectedIds: Set<number>;
  onChange: (ids: Set<number>) => void;
  readOnly?: boolean;
}) {
  function toggle(id: number) {
    if (readOnly) return;
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  }

  return (
    <div className="admin-site-cards">
      {sites.map((site) => {
        const checked = selectedIds.has(site.id);
        return (
          <article key={site.id} className={`admin-site-card${checked ? " admin-site-card-selected" : ""}`}>
            <header>
              <h4>{SITE_LABELS[site.slug] ?? site.name}</h4>
              <p className="muted">{site.slug}</p>
            </header>
            <label className="admin-site-access-toggle">
              <input type="checkbox" checked={checked} onChange={() => toggle(site.id)} disabled={readOnly} />
              <span>Åtkomst</span>
            </label>
            <p className="admin-site-access-note muted">Rollbehörigheter gäller där användaren har site-åtkomst.</p>
          </article>
        );
      })}
    </div>
  );
}
