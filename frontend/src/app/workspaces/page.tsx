"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTenantSelection } from "@/lib/TenantSelectionProvider";

export default function WorkspacesPage() {
  const router = useRouter();
  const { tenants, loading, switchTenant } = useTenantSelection();

  useEffect(() => {
    if (!loading && tenants.length === 1) {
      void switchTenant(tenants[0].id).then(() => router.replace("/"));
    }
  }, [loading, tenants, switchTenant, router]);

  if (loading) {
    return <main className="login-shell"><p className="muted">Laddar workspaces…</p></main>;
  }

  return (
    <main className="login-shell">
      <div className="login-card" style={{ width: "min(480px, 100%)" }}>
        <h1>Välj workspace</h1>
        <p className="muted">Välj vilken tenant du vill arbeta i.</p>
        <ul className="workspace-list">
          {tenants.map((tenant) => (
            <li key={tenant.id}>
              <button
                type="button"
                className="admin-btn admin-btn-block"
                onClick={() => void switchTenant(tenant.id).then(() => router.replace("/"))}
              >
                {tenant.displayName || tenant.name}
              </button>
            </li>
          ))}
        </ul>
        <p className="muted login-footer-note">
          <Link href="/">Tillbaka</Link>
        </p>
      </div>
    </main>
  );
}
