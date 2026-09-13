"use client";

import Link from "next/link";
import { MobileSectionPage } from "@/components/mobile/MobileSectionPage";
import { useAuth } from "@/lib/authContext";

export default function MobileAdminHubPage() {
  const { can } = useAuth();

  if (!can("users.read") && !can("roles.read")) {
    return (
      <MobileSectionPage title="Administration" backHref="/app/more">
        <p className="mobile-error">You do not have admin access.</p>
      </MobileSectionPage>
    );
  }

  const links = [
    { href: "/admin/users", label: "Users", show: can("users.read") },
    { href: "/admin/roles", label: "Roles", show: can("roles.read") },
    { href: "/admin/audit", label: "Audit log", show: can("audit.read") },
    { href: "/config", label: "Config & integrations", show: can("sites.read") || can("system.read") },
  ].filter((l) => l.show);

  return (
    <MobileSectionPage title="Administration" subtitle="Users, roles and system" backHref="/app/more">
      <ul className="mobile-hub-list">
        {links.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className="mobile-hub-link">{link.label}</Link>
          </li>
        ))}
      </ul>
    </MobileSectionPage>
  );
}
