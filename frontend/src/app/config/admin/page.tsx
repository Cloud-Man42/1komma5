"use client";

import { AdminAuditPanel } from "@/components/AdminAuditPanel";
import { AdminTokenPanel } from "@/components/AdminTokenPanel";

export default function ConfigAdminPage() {
  return (
    <>
      <header className="config-page-header">
        <h2 className="config-page-title">Admin &amp; säkerhet</h2>
        <p className="muted config-page-intro">
          Admin-token för skyddade API:er och granskning av admin-händelser.
        </p>
      </header>
      <AdminTokenPanel />
      <AdminAuditPanel />
    </>
  );
}
