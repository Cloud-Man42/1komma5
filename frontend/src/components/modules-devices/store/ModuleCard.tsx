"use client";

import Link from "next/link";
import type { StoreModuleSummary } from "@/lib/api";
import { SafeText } from "@/components/modules-devices/store/SafeMarkdown";
import {
  isActionable,
  originLabel,
  primaryActionLabel,
  securityBadgeClass,
  trustBadgeClass,
} from "@/components/modules-devices/store/storeLabels";

export function ModuleCard({ module: mod }: { module: StoreModuleSummary }) {
  const action = mod.primary_action;
  return (
    <article className="config-panel store-module-card" data-testid={`store-card-${mod.module_id}`}>
      <div className="config-panel-header">
        <div>
          <h3 className="config-panel-title">
            <SafeText text={mod.display_name} />
          </h3>
          <p className="muted">
            {mod.publisher_name} · {mod.category}
          </p>
        </div>
        <div className="store-card-badges">
          <span className={trustBadgeClass(mod.trust_badge)}>{mod.trust_badge}</span>
          <span className={securityBadgeClass(mod.security_badge)}>{mod.security_badge.replace(/_/g, " ")}</span>
        </div>
      </div>
      <p className="store-card-description">
        <SafeText text={mod.description} />
      </p>
      <div className="config-stat-grid store-card-meta">
        <div>
          <span className="config-stat-label">Origin</span>
          <strong>{originLabel(mod.origin)}</strong>
        </div>
        <div>
          <span className="config-stat-label">Version</span>
          <strong>{mod.installed_version ?? mod.latest_version ?? "—"}</strong>
        </div>
        <div>
          <span className="config-stat-label">Status</span>
          <strong>{primaryActionLabel(action)}</strong>
        </div>
      </div>
      {mod.control_capable ? (
        <p className="config-banner" data-testid="control-notice">
          Can control physical equipment. Runtime execution may be blocked by policy.
        </p>
      ) : null}
      <div className="store-card-actions">
        <Link href={`/config/modules-devices/store/${encodeURIComponent(mod.module_id)}`} className="config-button">
          Details
        </Link>
        {isActionable(action) ? (
          <Link
            href={`/config/modules-devices/store/${encodeURIComponent(mod.module_id)}/install`}
            className="config-button primary"
          >
            {primaryActionLabel(action)}
          </Link>
        ) : null}
      </div>
    </article>
  );
}
