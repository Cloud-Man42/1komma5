"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Button,
  Card,
  FormField,
  FormSection,
  Modal,
  PasswordField,
  RoleSelectCards,
  SiteAccessCards,
  StatusBadge,
  StickyFormFooter,
  useToast,
} from "@/components/admin-ui";
import { TextInput } from "@/components/admin-ui/FormField";
import type { RoleItem, SiteOption, UserItem } from "@/lib/adminUsersApi";
import {
  createAdminUser,
  resetAdminUserPassword,
  updateAdminUser,
} from "@/lib/adminUsersApi";
import { passwordPolicyChecks, validatePasswordPolicy } from "@/lib/passwordPolicy";
import { formatDateTime, userDisplayLabel, userStatus } from "@/lib/userAdminUtils";

export interface UserFormState {
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  displayName: string;
  isActive: boolean;
  roleIds: number[];
  siteIds: number[];
  password: string;
  mustChangePassword: boolean;
}

function emptyForm(): UserFormState {
  return {
    username: "",
    email: "",
    firstName: "",
    lastName: "",
    displayName: "",
    isActive: true,
    roleIds: [],
    siteIds: [],
    password: "",
    mustChangePassword: true,
  };
}

function fromUser(user: UserItem): UserFormState {
  return {
    username: user.username,
    email: user.email,
    firstName: user.firstName ?? "",
    lastName: user.lastName ?? "",
    displayName: user.displayName ?? "",
    isActive: user.isActive,
    roleIds: user.roles.map((r) => r.id),
    siteIds: [],
    password: "",
    mustChangePassword: false,
  };
}

export function UserEditorForm({
  mode,
  user,
  roles,
  sites,
  siteSlugToId,
  onSaved,
}: {
  mode: "create" | "edit";
  user?: UserItem;
  roles: RoleItem[];
  sites: SiteOption[];
  siteSlugToId: Map<string, number>;
  onSaved: (user: UserItem) => void;
}) {
  const { showToast } = useToast();
  const [form, setForm] = useState<UserFormState>(() => (user ? fromUser(user) : emptyForm()));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetPassword, setResetPassword] = useState("");
  const [resetMustChange, setResetMustChange] = useState(true);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    if (user && sites.length) {
      const ids = user.sites.map((slug) => siteSlugToId.get(slug)).filter((id): id is number => id != null);
      setForm((prev) => ({ ...prev, siteIds: ids }));
    }
  }, [user, sites, siteSlugToId]);

  useEffect(() => {
    if (!dirty) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  function patch(partial: Partial<UserFormState>) {
    setDirty(true);
    setForm((prev) => ({ ...prev, ...partial }));
  }

  const passwordChecks = useMemo(() => passwordPolicyChecks(form.password), [form.password]);
  const resetChecks = useMemo(() => passwordPolicyChecks(resetPassword), [resetPassword]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (mode === "create") {
      const policyError = validatePasswordPolicy(form.password);
      if (policyError) {
        setError(policyError);
        return;
      }
    }
    setSaving(true);
    try {
      if (mode === "create") {
        const created = await createAdminUser({
          username: form.username.trim(),
          email: form.email.trim(),
          password: form.password,
          first_name: form.firstName.trim() || null,
          last_name: form.lastName.trim() || null,
          display_name: form.displayName.trim() || null,
          role_ids: form.roleIds,
          site_ids: form.siteIds,
          must_change_password: form.mustChangePassword,
        });
        showToast("Användare skapad", "success");
        onSaved(created);
      } else if (user) {
        const updated = await updateAdminUser(user.id, {
          username: form.username.trim(),
          email: form.email.trim(),
          first_name: form.firstName.trim() || null,
          last_name: form.lastName.trim() || null,
          display_name: form.displayName.trim() || null,
          is_active: form.isActive,
          role_ids: form.roleIds,
          site_ids: form.siteIds,
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

  async function handleResetPassword() {
    if (!user) return;
    const policyError = validatePasswordPolicy(resetPassword);
    if (policyError) {
      setError(policyError);
      return;
    }
    setResetting(true);
    try {
      await resetAdminUserPassword(user.id, resetPassword, resetMustChange);
      setResetOpen(false);
      setResetPassword("");
      showToast("Lösenord återställt", "success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte återställa lösenord");
    } finally {
      setResetting(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      <FormSection title="Profil" intro="Grundläggande kontoinformation.">
        <div className="admin-form-grid">
          <FormField label="Förnamn">
            <TextInput value={form.firstName} onChange={(e) => patch({ firstName: e.target.value })} />
          </FormField>
          <FormField label="Efternamn">
            <TextInput value={form.lastName} onChange={(e) => patch({ lastName: e.target.value })} />
          </FormField>
          <FormField label="Visningsnamn">
            <TextInput value={form.displayName} onChange={(e) => patch({ displayName: e.target.value })} />
          </FormField>
          <FormField label="E-post" error={null}>
            <TextInput type="email" value={form.email} onChange={(e) => patch({ email: e.target.value })} required />
          </FormField>
          <FormField label="Användarnamn">
            <TextInput value={form.username} onChange={(e) => patch({ username: e.target.value })} required />
          </FormField>
          {mode === "edit" ? (
            <FormField label="Status">
              <label className="admin-permission-item">
                <input
                  type="checkbox"
                  checked={form.isActive}
                  onChange={(e) => patch({ isActive: e.target.checked })}
                />
                <span>Aktiv användare</span>
              </label>
            </FormField>
          ) : null}
        </div>
      </FormSection>

      {mode === "create" ? (
        <FormSection title="Lösenord">
          <PasswordField label="Lösenord" value={form.password} onChange={(v) => patch({ password: v })} required />
          {!passwordChecks.nonEmpty ? <p className="admin-field-hint muted">Ange ett lösenord.</p> : null}
          <label className="admin-permission-item">
            <input
              type="checkbox"
              checked={form.mustChangePassword}
              onChange={(e) => patch({ mustChangePassword: e.target.checked })}
            />
            <span>Kräv lösenordsbyte vid nästa inloggning</span>
          </label>
        </FormSection>
      ) : null}

      <FormSection title="Åtkomst" intro="Roller och site-behörigheter.">
        <RoleSelectCards
          roles={roles}
          selectedIds={new Set(form.roleIds)}
          onChange={(ids) => patch({ roleIds: [...ids] })}
        />
        <SiteAccessCards
          sites={sites}
          selectedIds={new Set(form.siteIds)}
          onChange={(ids) => patch({ siteIds: [...ids] })}
        />
      </FormSection>

      {mode === "edit" && user ? (
        <>
          <FormSection title="Säkerhet" intro="Kontostatus och lösenordshantering.">
            <Card>
              <p>
                Status: <StatusBadge status={userStatus(user)} />
              </p>
              {user.isLocked ? <p className="muted">Kontot är låst efter misslyckade inloggningsförsök.</p> : null}
              {user.mustChangePassword ? <p className="muted">Användaren måste byta lösenord vid nästa inloggning.</p> : null}
              <Button type="button" variant="secondary" onClick={() => setResetOpen(true)}>
                Återställ lösenord
              </Button>
            </Card>
          </FormSection>
          <FormSection title="Aktivitet">
            <p className="muted">
              Senaste inloggningsförsök: {formatDateTime(user.lastLoginAt)}
            </p>
          </FormSection>
        </>
      ) : null}

      {error ? <p className="error-text" role="alert">{error}</p> : null}

      <StickyFormFooter>
        <Link href="/admin/users" className="admin-btn admin-btn-secondary">
          Avbryt
        </Link>
        <Button type="submit" disabled={saving}>
          {saving ? "Sparar…" : mode === "create" ? "Skapa användare" : "Spara ändringar"}
        </Button>
      </StickyFormFooter>

      {mode === "edit" && user ? (
        <Modal
          open={resetOpen}
          title="Återställ lösenord"
          onClose={() => setResetOpen(false)}
          footer={
            <>
              <Button variant="secondary" type="button" onClick={() => setResetOpen(false)}>
                Avbryt
              </Button>
              <Button type="button" disabled={resetting || !resetChecks.nonEmpty} onClick={() => void handleResetPassword()}>
                {resetting ? "Sparar…" : "Återställ"}
              </Button>
            </>
          }
        >
          <p className="muted">Nytt lösenord för {userDisplayLabel(user)}.</p>
          <PasswordField label="Nytt lösenord" value={resetPassword} onChange={setResetPassword} required />
          <label className="admin-permission-item">
            <input type="checkbox" checked={resetMustChange} onChange={(e) => setResetMustChange(e.target.checked)} />
            <span>Kräv lösenordsbyte vid nästa inloggning</span>
          </label>
        </Modal>
      ) : null}
    </form>
  );
}
