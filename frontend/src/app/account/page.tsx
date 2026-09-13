"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Button,
  Card,
  FormSection,
  Modal,
  PasswordField,
  UserAvatar,
  useToast,
} from "@/components/admin-ui";
import { changePassword } from "@/lib/auth";
import { useAuth } from "@/lib/authContext";
import { passwordPolicyChecks, validatePasswordPolicy } from "@/lib/passwordPolicy";

export default function AccountPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const { showToast } = useToast();
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checks = passwordPolicyChecks(newPassword, confirmPassword);

  if (loading) return <p className="muted">Laddar konto…</p>;
  if (!user) return <p className="muted">Inte inloggad</p>;

  async function onChangePassword(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const policyError = validatePasswordPolicy(newPassword);
    if (policyError) {
      setError(policyError);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Lösenorden matchar inte.");
      return;
    }
    setSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      setPasswordOpen(false);
      showToast("Lösenord uppdaterat — logga in igen.", "success");
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte byta lösenord");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="account-page">
      {user.mustChangePassword ? (
        <div className="admin-card" role="alert">
          <p className="error-text">Du måste byta lösenord innan du fortsätter.</p>
          <Button type="button" onClick={() => setPasswordOpen(true)}>
            Byt lösenord
          </Button>
        </div>
      ) : null}

      <header className="account-hero">
        <UserAvatar name={user.displayName} size="lg" />
        <div>
          <h1 className="account-hero-name">{user.displayName}</h1>
          <p className="muted">{user.email || user.username}</p>
        </div>
      </header>

      <div className="account-sections">
        <Card title="Profil">
          <dl>
            <dt>Namn</dt>
            <dd>{user.displayName}</dd>
            <dt>E-post</dt>
            <dd>{user.email || "—"}</dd>
            <dt>Användarnamn</dt>
            <dd>{user.username}</dd>
          </dl>
        </Card>

        <Card title="Säkerhet">
          {user.authMethod === "break_glass" ? (
            <p className="muted">Break-glass-token — lösenordsbyte via användarlogin.</p>
          ) : (
            <Button type="button" variant="secondary" onClick={() => setPasswordOpen(true)}>
              Byt lösenord
            </Button>
          )}
        </Card>

        <Card title="Åtkomst">
          <FormSection title="Roller">
            <div className="admin-chip-row">
              {user.roles.map((role) => (
                <span key={role} className="admin-chip">
                  {role}
                </span>
              ))}
            </div>
          </FormSection>
          <FormSection title="Sites">
            <div className="admin-chip-row">
              {user.sites.length ? (
                user.sites.map((site) => (
                  <span key={site} className="admin-chip">
                    {site}
                  </span>
                ))
              ) : (
                <span className="muted">Inga sites</span>
              )}
            </div>
          </FormSection>
        </Card>
      </div>

      <Modal
        open={passwordOpen}
        title="Byt lösenord"
        onClose={() => setPasswordOpen(false)}
        footer={
          <>
            <Button variant="secondary" type="button" onClick={() => setPasswordOpen(false)}>
              Avbryt
            </Button>
            <Button
              type="submit"
              form="change-password-form"
              disabled={submitting || !checks.nonEmpty || !checks.match}
            >
              {submitting ? "Sparar…" : "Spara"}
            </Button>
          </>
        }
      >
        <form id="change-password-form" onSubmit={onChangePassword}>
          <PasswordField
            label="Nuvarande lösenord"
            value={currentPassword}
            onChange={setCurrentPassword}
            autoComplete="current-password"
            required
          />
          <PasswordField
            label="Nytt lösenord"
            value={newPassword}
            onChange={setNewPassword}
            autoComplete="new-password"
            required
          />
          <PasswordField
            label="Bekräfta nytt lösenord"
            value={confirmPassword}
            onChange={setConfirmPassword}
            autoComplete="new-password"
            required
          />
          <ul className="admin-field-hint muted">
            <li>{checks.match ? "✓" : "○"} Lösenorden matchar</li>
          </ul>
          {error ? <p className="error-text" role="alert">{error}</p> : null}
        </form>
      </Modal>
    </div>
  );
}
