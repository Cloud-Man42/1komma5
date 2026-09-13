"use client";

import type { RoleItem } from "@/lib/adminUsersApi";

const ROLE_HINTS: Record<string, string> = {
  SUPER_ADMIN: "Full åtkomst till hela EMIC",
  ADMIN: "Hantera användare och konfiguration",
  OPERATOR: "Styr energisystem utan användaradministration",
  USER: "Läsbehörighet till operativ data",
  VIEWER: "Endast dashboard och energidata",
};

export function RoleSelectCards({
  roles,
  selectedIds,
  onChange,
  readOnly = false,
}: {
  roles: RoleItem[];
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
    <div className="admin-role-cards">
      {roles.map((role) => {
        const checked = selectedIds.has(role.id);
        return (
          <button
            key={role.id}
            type="button"
            className={`admin-role-card${checked ? " admin-role-card-selected" : ""}`}
            onClick={() => toggle(role.id)}
            disabled={readOnly}
            aria-pressed={checked}
          >
            <span className="admin-role-card-check">{checked ? "✓" : ""}</span>
            <span className="admin-role-card-name">{role.name}</span>
            <span className="admin-role-card-desc muted">
              {role.description || ROLE_HINTS[role.name] || "Anpassad roll"}
            </span>
          </button>
        );
      })}
    </div>
  );
}
