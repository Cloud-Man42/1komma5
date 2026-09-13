"use client";

import { useMemo, useState } from "react";
import type { PermissionItem } from "@/lib/adminUsersApi";
import { SearchField } from "./SearchField";
import { Button } from "./Button";

export function PermissionGroupList({
  permissions,
  selectedIds,
  onChange,
  readOnly = false,
}: {
  permissions: PermissionItem[];
  selectedIds: Set<number>;
  onChange: (ids: Set<number>) => void;
  readOnly?: boolean;
}) {
  const [search, setSearch] = useState("");

  const grouped = useMemo(() => {
    const map = new Map<string, PermissionItem[]>();
    for (const perm of permissions) {
      const q = search.trim().toLowerCase();
      if (q && !perm.key.includes(q) && !perm.name.toLowerCase().includes(q) && !perm.group.toLowerCase().includes(q)) {
        continue;
      }
      const list = map.get(perm.group) ?? [];
      list.push(perm);
      map.set(perm.group, list);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b, "sv"));
  }, [permissions, search]);

  function toggle(id: number) {
    if (readOnly) return;
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  }

  function setGroup(groupPerms: PermissionItem[], checked: boolean) {
    if (readOnly) return;
    const next = new Set(selectedIds);
    for (const p of groupPerms) {
      if (checked) next.add(p.id);
      else next.delete(p.id);
    }
    onChange(next);
  }

  return (
    <div className="admin-permission-groups">
      <SearchField value={search} onChange={setSearch} placeholder="Sök behörigheter…" label="Sök behörigheter" />
      {grouped.map(([group, perms]) => (
        <section key={group} className="admin-permission-group">
          <header className="admin-permission-group-header">
            <h3>{group}</h3>
            {!readOnly ? (
              <div className="admin-permission-group-actions">
                <Button variant="ghost" type="button" onClick={() => setGroup(perms, true)}>
                  Markera alla
                </Button>
                <Button variant="ghost" type="button" onClick={() => setGroup(perms, false)}>
                  Rensa
                </Button>
              </div>
            ) : null}
          </header>
          <ul className="admin-permission-list">
            {perms.map((perm) => (
              <li key={perm.id}>
                <label className="admin-permission-item">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(perm.id)}
                    onChange={() => toggle(perm.id)}
                    disabled={readOnly}
                  />
                  <span>
                    <strong>{perm.name}</strong>
                    <span className="muted admin-permission-key">{perm.key}</span>
                    {perm.description ? <span className="admin-permission-desc muted">{perm.description}</span> : null}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
