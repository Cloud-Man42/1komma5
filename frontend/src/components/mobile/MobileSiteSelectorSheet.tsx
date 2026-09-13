"use client";

import { useState } from "react";
import { useSiteSelection } from "@/lib/SiteSelectionProvider";

export function MobileSiteSelectorTrigger() {
  const { accessibleSites, selectedSlugs, draftSlugs, toggleDraft, selectAll, clearAll, applySelection, loading } =
    useSiteSelection();
  const [open, setOpen] = useState(false);

  const label =
    selectedSlugs.length === accessibleSites.length
      ? "Alla anläggningar"
      : selectedSlugs.map((slug) => accessibleSites.find((s) => s.slug === slug)?.name ?? slug).join(" + ");

  return (
    <>
      <button
        type="button"
        className="mobile-site-trigger"
        onClick={() => setOpen(true)}
        disabled={loading}
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <span className="mobile-site-trigger-label">{label}</span>
        <span aria-hidden="true">▼</span>
      </button>
      {open ? (
        <div className="mobile-sheet-backdrop" role="presentation" onClick={() => setOpen(false)}>
          <div
            className="mobile-sheet"
            role="dialog"
            aria-label="Välj anläggningar"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mobile-sheet-title">Select sites</h2>
            <ul className="mobile-sheet-list">
              {accessibleSites.map((site) => (
                <li key={site.slug}>
                  <label className="mobile-sheet-item">
                    <input
                      type="checkbox"
                      checked={draftSlugs.includes(site.slug)}
                      onChange={() => toggleDraft(site.slug)}
                    />
                    <span>{site.name}</span>
                  </label>
                </li>
              ))}
            </ul>
            <div className="mobile-sheet-actions">
              <button type="button" className="ms-btn-ghost" onClick={selectAll}>
                Select all
              </button>
              <button type="button" className="ms-btn-ghost" onClick={clearAll}>
                Clear
              </button>
              <button
                type="button"
                className="ms-btn-primary"
                onClick={() => {
                  void applySelection({ pathname: window.location.pathname }).then(() => setOpen(false));
                }}
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
