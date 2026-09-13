"use client";

import Link from "next/link";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { useAuth } from "@/lib/authContext";

export default function MobileAccountPage() {
  const { user } = useAuth();

  if (!user) {
    return (
      <MobileSectionPage title="My account" backHref="/app/more">
        <p className="mobile-error">Not signed in.</p>
        <Link href="/login" className="mobile-hub-link">Sign in →</Link>
      </MobileSectionPage>
    );
  }

  return (
    <MobileSectionPage title="My account" backHref="/app/more">
      <section className="mobile-card-section">
        <div className="mobile-stat-grid">
          <div><span>Name</span><strong>{user.displayName || user.username}</strong></div>
          <div><span>Email</span><strong>{user.email || "—"}</strong></div>
          <div><span>Roles</span><strong>{user.roles.join(", ") || "—"}</strong></div>
          <div><span>Sites</span><strong>{user.sites.length ? user.sites.join(", ") : "All"}</strong></div>
        </div>
      </section>
      <ul className="mobile-hub-list">
        <li><Link href="/account" className="mobile-hub-link">Change password & full account →</Link></li>
        <li><Link href="/app/install" className="mobile-hub-link">Install PWA →</Link></li>
      </ul>
    </MobileSectionPage>
  );
}
