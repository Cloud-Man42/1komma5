"use client";

import type { CSSProperties } from "react";
import type { MultiSiteSiteEntry } from "@/lib/multiSiteApi";
import { buildSiteColorMap } from "@/lib/multiSiteSiteColors";

function healthDot(health: string): string {
  if (health === "healthy") return "●";
  if (health === "degraded") return "◐";
  return "○";
}

export function OverviewSiteVisibilityBar({
  sites,
  visibleSlugs,
  onToggle,
  onShowAll,
  onIsolate,
}: {
  sites: MultiSiteSiteEntry[];
  visibleSlugs: string[];
  onToggle: (slug: string) => void;
  onShowAll: () => void;
  onIsolate: (slug: string) => void;
}) {
  const colors = buildSiteColorMap(sites.map((s) => s.slug));
  const allVisible = visibleSlugs.length === sites.length;

  return (
    <section className="ms-site-visibility" aria-label="Synliga anläggningar">
      <div className="ms-site-visibility-head">
        <h2 className="ms-site-visibility-title">Anläggningar i vyn</h2>
        <div className="ms-site-visibility-actions">
          <button type="button" className="ms-btn-ghost" onClick={onShowAll} disabled={allVisible}>
            Visa alla
          </button>
        </div>
      </div>
      <ul className="ms-site-visibility-list">
        {sites.map((site) => {
          const visible = visibleSlugs.includes(site.slug);
          const color = colors[site.slug];
          return (
            <li key={site.slug}>
              <button
                type="button"
                className={`ms-site-visibility-chip${visible ? " ms-site-visibility-chip-on" : ""}`}
                style={{ "--ms-site-color": color } as CSSProperties}
                aria-pressed={visible}
                onClick={() => onToggle(site.slug)}
                onDoubleClick={() => onIsolate(site.slug)}
                title={`${visible ? "Dölj" : "Visa"} ${site.name}. Dubbelklicka för att isolera.`}
              >
                <span className="ms-site-visibility-swatch" aria-hidden="true" />
                <span className="ms-site-visibility-name">{site.name}</span>
                <span className="ms-site-visibility-health" aria-hidden="true">
                  {healthDot(site.health)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="muted ms-site-visibility-hint">
        Klicka för att visa/dölja i diagrammen. Dubbelklicka en anläggning för att isolera den.
      </p>
    </section>
  );
}
