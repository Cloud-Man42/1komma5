"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LoginHero } from "@/components/auth/LoginHero";
import { Button } from "@/components/admin-ui";
import { PasswordField } from "@/components/admin-ui/PasswordField";
import { FormField } from "@/components/admin-ui/FormField";
import { useAuth } from "@/lib/authContext";
import { APP_ACRONYM } from "@/lib/brand";

function safeNextPath(raw: string | null): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return "/";
  if (raw.startsWith("/login")) return "/";
  return raw;
}

export function LoginForm() {
  const { login, isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeNextPath(searchParams.get("next"));
  const usernameRef = useRef<HTMLInputElement>(null);

  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    usernameRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace(nextPath);
    }
  }, [loading, isAuthenticated, router, nextPath]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(usernameOrEmail.trim(), password);
      router.replace(nextPath);
    } catch {
      setError("Felaktigt användarnamn eller lösenord.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!loading && isAuthenticated) return null;

  return (
    <div className="login-page">
      <LoginHero />
      <div className="login-panel">
        <div className="login-card">
          <h1 className="login-card-title">Logga in</h1>
          <p className="muted">Säker åtkomst till {APP_ACRONYM}</p>
          <form onSubmit={onSubmit} className="login-form">
            <FormField label="E-post / användarnamn">
              <input
                ref={usernameRef}
                className="admin-input"
                type="text"
                autoComplete="username"
                value={usernameOrEmail}
                onChange={(e) => setUsernameOrEmail(e.target.value)}
                required
              />
            </FormField>
            <PasswordField
              label="Lösenord"
              value={password}
              onChange={setPassword}
              autoComplete="current-password"
              required
            />
            {error ? <p className="error-text" role="alert">{error}</p> : null}
            <Button type="submit" disabled={submitting} className="admin-btn-block">
              {submitting ? "Loggar in…" : "Logga in"}
            </Button>
          </form>
          <p className="muted login-footer-note">Säker åtkomst till EMIC</p>
        </div>
      </div>
    </div>
  );
}
