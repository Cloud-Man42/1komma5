"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  createPlatformTenant,
  fetchPlatformTenants,
  updatePlatformTenant,
  type TenantSummary,
} from "@/lib/tenantApi";

export default function PlatformTenantsPage() {
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [slug, setSlug] = useState("");

  async function loadTenants() {
    setLoading(true);
    setError(null);
    try {
      setTenants(await fetchPlatformTenants());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTenants();
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const tenant = await createPlatformTenant({
        name: name.trim(),
        displayName: displayName.trim() || name.trim(),
        slug: slug.trim().toLowerCase(),
      });
      setTenants((prev) => [...prev, tenant].sort((a, b) => a.displayName.localeCompare(b.displayName)));
      setName("");
      setDisplayName("");
      setSlug("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create tenant");
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(tenant: TenantSummary) {
    setError(null);
    try {
      const updated = await updatePlatformTenant(tenant.id, { isActive: !tenant.isActive });
      setTenants((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update tenant");
    }
  }

  return (
    <main className="container admin-page">
      <header className="admin-page-header">
        <h1>Platform tenants</h1>
        <p className="muted">Create and manage workspaces (platform admin only).</p>
      </header>

      {error ? <p className="error-text">{error}</p> : null}

      <section className="admin-card" style={{ marginBottom: "1.5rem" }}>
        <h2>Create tenant</h2>
        <form onSubmit={handleCreate} className="admin-form-grid">
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Display name
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </label>
          <label>
            Slug
            <input
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              pattern="[a-z0-9]+(-[a-z0-9]+)*"
              required
            />
          </label>
          <div>
            <button type="submit" className="admin-btn admin-btn-primary" disabled={creating}>
              {creating ? "Creating…" : "Create tenant"}
            </button>
          </div>
        </form>
      </section>

      <section>
        <h2>All tenants</h2>
        {loading ? <p className="muted">Loading…</p> : null}
        <ul className="admin-list">
          {tenants.map((tenant) => (
            <li key={tenant.id} style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
              <div>
                <strong>{tenant.displayName || tenant.name}</strong>
                <span className="muted"> ({tenant.slug})</span>
                <div className="muted">
                  {tenant.status ?? "active"}
                  {tenant.isActive === false ? " · disabled" : ""}
                </div>
              </div>
              <button
                type="button"
                className="admin-btn"
                onClick={() => void toggleActive(tenant)}
              >
                {tenant.isActive === false ? "Enable" : "Disable"}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <p className="muted">
        <Link href="/">Back to home</Link>
      </p>
    </main>
  );
}
