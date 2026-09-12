"use client";

import { usePathname } from "next/navigation";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";

function healthIcon(health: string | undefined): string {
  if (health === "healthy") return "●";
  if (health === "degraded") return "◐";
  if (health === "offline") return "○";
  return "○";
}

export function SiteSelector({ compact = false }: { compact?: boolean }) {
  const pathname = usePathname();
  const { loading, accessibleSites, selectedSlugs, draftSlugs, toggleDraft, selectAll, clearAll, applySelection } =
    useSiteSelection();

  if (loading || accessibleSites.length <= 1) return null;

  const label =
    selectedSlugs.length === accessibleSites.length
      ? "Alla anläggningar"
      : selectedSlugs.length === 1
        ? accessibleSites.find((s) => s.slug === selectedSlugs[0])?.name ?? selectedSlugs[0]
        : `${selectedSlugs.length} anläggningar`;

  return (
    <details className={`ms-site-selector${compact ? " ms-site-selector-compact" : ""}`}>
      <summary className="ms-site-selector-trigger">{label} ▼</summary>
      <div className="ms-site-selector-panel">
        <p className="ms-site-selector-title">Anläggningar</p>
        <ul className="ms-site-selector-list">
          {accessibleSites.map((site) => (
            <li key={site.slug}>
              <label className="ms-site-selector-item">
                <input
                  type="checkbox"
                  checked={draftSlugs.includes(site.slug)}
                  onChange={() => toggleDraft(site.slug)}
                />
                <span className="ms-site-selector-name">{site.name}</span>
                <span className="ms-site-selector-health" aria-hidden="true">
                  {healthIcon("healthy")}
                </span>
              </label>
            </li>
          ))}
        </ul>
        <div className="ms-site-selector-actions">
          <button type="button" className="ms-btn-ghost" onClick={selectAll}>
            Markera alla
          </button>
          <button type="button" className="ms-btn-ghost" onClick={clearAll}>
            Rensa
          </button>
          <button type="button" className="ms-btn-primary" onClick={() => void applySelection({ pathname })}>
            Verkställ
          </button>
        </div>
      </div>
    </details>
  );
}
