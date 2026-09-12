"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  Button,
  Card,
  FormField,
  FormSection,
  PermissionGroupList,
  StickyFormFooter,
  useToast,
} from "@/components/admin-ui";
import { TextInput } from "@/components/admin-ui/FormField";
import type { PermissionItem, RoleItem } from "@/lib/adminUsersApi";
import { createAdminRole, updateAdminRole } from "@/lib/adminUsersApi";

export function RoleEditorForm({
  mode,
  role,
  permissions,
  readOnly = false,
  onSaved,
}: {
  mode: "create" | "edit";
  role?: RoleItem;
  permissions: PermissionItem[];
  readOnly?: boolean;
  onSaved: (role: RoleItem) => void;
}) {
  const { showToast } = useToast();
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(
    () => new Set(role?.permissions.map((p) => p.id) ?? []),
  );
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!dirty) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (readOnly) return;
    setError(null);
    setSaving(true);
    try {
      const permissionIds = [...selectedIds];
      if (mode === "create") {
        const created = await createAdminRole({
          name: name.trim(),
          description: description.trim() || null,
          permission_ids: permissionIds,
        });
        showToast("Roll skapad", "success");
        onSaved(created);
      } else if (role) {
        const updated = await updateAdminRole(role.id, {
          description: description.trim() || null,
          permission_ids: permissionIds,
        });
        setDirty(false);
        showToast("Ändringar sparade", "success");
        onSaved(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara");
    } finally {
      setSaving(false);
    }
  }

  function patchSelected(ids: Set<number>) {
    setDirty(true);
    setSelectedIds(ids);
  }

  return (
    <form onSubmit={onSubmit}>
      <div className="admin-form-grid">
        <FormSection title="Roll" intro={readOnly ? "Systemroll — skrivskyddad." : "Namn och beskrivning."}>
          <FormField label="Namn">
            <TextInput
              value={name}
              onChange={(e) => {
                setDirty(true);
                setName(e.target.value);
              }}
              required
              disabled={mode === "edit" || readOnly}
            />
          </FormField>
          <FormField label="Beskrivning">
            <TextInput
              value={description}
              onChange={(e) => {
                setDirty(true);
                setDescription(e.target.value);
              }}
              disabled={readOnly}
            />
          </FormField>
        </FormSection>
        <Card title="Sammanfattning">
          <p>
            <strong>{selectedIds.size}</strong> behörigheter valda
          </p>
          <p className="muted">Site-åtkomst ärvs från användaren, inte rollen.</p>
        </Card>
      </div>

      <FormSection title="Behörigheter" intro="Grupperade enligt EMIC-moduler.">
        <PermissionGroupList
          permissions={permissions}
          selectedIds={selectedIds}
          onChange={patchSelected}
          readOnly={readOnly}
        />
      </FormSection>

      {error ? <p className="error-text" role="alert">{error}</p> : null}

      {!readOnly ? (
        <StickyFormFooter>
          <Link href="/admin/roles" className="admin-btn admin-btn-secondary">
            Avbryt
          </Link>
          <Button type="submit" disabled={saving}>
            {saving ? "Sparar…" : mode === "create" ? "Skapa roll" : "Spara ändringar"}
          </Button>
        </StickyFormFooter>
      ) : null}
    </form>
  );
}
