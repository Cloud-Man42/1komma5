"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  addPlatformTenantMember,
  createPlatformTenant,
  deletePlatformTenant,
  fetchPlatformTenantMembers,
  fetchPlatformTenants,
  removePlatformTenantMember,
  updatePlatformTenant,
  type TenantMember,
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
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [members, setMembers] = useState<TenantMember[]>([]);
  const [memberEmail, setMemberEmail] = useState("");
  const [membersLoading, setMembersLoading] = useState(false);

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

  async function loadMembers(tenantId: number) {
    setMembersLoading(true);
    setError(null);
    try {
      setMembers(await fetchPlatformTenantMembers(tenantId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load members");
      setMembers([]);
    } finally {
      setMembersLoading(false);
    }
  }

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

  async function handleExpand(tenant: TenantSummary) {
    if (expandedId === tenant.id) {
      setExpandedId(null);
      setMembers([]);
      return;
    }
    setExpandedId(tenant.id);
    setMemberEmail("");
    await loadMembers(tenant.id);
  }

  async function handleAddMember(tenantId: number, event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const member = await addPlatformTenantMember(tenantId, memberEmail.trim());
      setMembers((prev) => [...prev, member]);
      setMemberEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add member");
    }
  }

  async function handleRemoveMember(tenantId: number, userId: number) {
    setError(null);
    try {
      await removePlatformTenantMember(tenantId, userId);
      setMembers((prev) => prev.filter((m) => m.userId !== userId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member");
    }
  }

  async function handleDelete(tenant: TenantSummary) {
    if (tenant.slug === "henrik-home") return;
    if (!window.confirm(`Delete tenant "${tenant.displayName}"? Only empty tenants can be removed.`)) return;
    setError(null);
    try {
      await deletePlatformTenant(tenant.id);
      setTenants((prev) => prev.filter((t) => t.id !== tenant.id));
      if (expandedId === tenant.id) {
        setExpandedId(null);
        setMembers([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete tenant");
    }
  }

  return (
    <main className="container admin-page">
      <header className="admin-page-header">
        <h1>Platform tenants</h1>
        <p className="muted">Create, disable, and manage workspace membership (platform admin only).</p>
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
            <li key={tenant.id} style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
                <div>
                  <strong>{tenant.displayName || tenant.name}</strong>
                  <span className="muted"> ({tenant.slug})</span>
                  <div className="muted">
                    {tenant.status ?? "active"}
                    {tenant.isActive === false ? " · disabled" : ""}
                  </div>
                </div>
                <button type="button" className="admin-btn" onClick={() => void handleExpand(tenant)}>
                  {expandedId === tenant.id ? "Hide members" : "Members"}
                </button>
                <button type="button" className="admin-btn" onClick={() => void toggleActive(tenant)}>
                  {tenant.isActive === false ? "Enable" : "Disable"}
                </button>
                {tenant.slug !== "henrik-home" ? (
                  <button type="button" className="admin-btn" onClick={() => void handleDelete(tenant)}>
                    Delete
                  </button>
                ) : null}
              </div>
              {expandedId === tenant.id ? (
                <div className="admin-card" style={{ marginTop: "0.75rem" }}>
                  <h3>Members</h3>
                  {membersLoading ? <p className="muted">Loading members…</p> : null}
                  <ul className="admin-list">
                    {members.map((member) => (
                      <li key={member.tenantUserId} style={{ display: "flex", gap: "1rem" }}>
                        <span>
                          {member.displayName || member.email} ({member.email})
                        </span>
                        <button
                          type="button"
                          className="admin-btn"
                          onClick={() => void handleRemoveMember(tenant.id, member.userId)}
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                  <form onSubmit={(event) => void handleAddMember(tenant.id, event)} className="admin-form-grid">
                    <label>
                      Add user by email
                      <input
                        type="email"
                        value={memberEmail}
                        onChange={(e) => setMemberEmail(e.target.value)}
                        required
                      />
                    </label>
                    <div>
                      <button type="submit" className="admin-btn admin-btn-primary">
                        Add member
                      </button>
                    </div>
                  </form>
                </div>
              ) : null}
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
